# -*- coding: utf-8 -*-
# 파일 인코딩을 UTF-8로 설정
import uuid  # 고유 ID 생성용
import time  # 시간 관련 함수
import logging  # 로그 출력용
import traceback  # 에러 추적용
from datetime import datetime  # 날짜/시간 처리
import boto3  # AWS SDK
from boto3.session import Session  # AWS 세션 관리

# Agent Core Memory 임포트
from bedrock_agentcore.memory import MemoryClient  # AWS 메모리 클라이언트

# Strands 임포트 (AI 에이전트 프레임워크)
from strands.hooks import AfterInvocationEvent, HookProvider, HookRegistry, MessageAddedEvent
from strands import Agent  # AI 에이전트 클래스
from strands.models import BedrockModel  # Bedrock 모델 클래스

# 로깅 설정 - WARNING 레벨 이상만 출력
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# AWS 세션 설정
boto_session = Session()  # AWS 세션 생성
REGION = "us-east-1"  # AWS 리전 설정 (버지니아 북부)
MODEL_ID = "us.anthropic.claude-3-7-sonnet-20250219-v1:0"  # Claude 3.7 Sonnet 모델 ID

# 설정 정보 출력
print(f"🔧 AWS 리전: {REGION}")
print(f"🤖 모델: {MODEL_ID}")

# 한시율 메모리 훅 클래스
class HansiyulMemoryHooks(HookProvider):
    """한시율 캐릭터를 위한 메모리 훅"""

    def __init__(self, memory_id: str, client: MemoryClient, actor_id: str, session_id: str):
        # 메모리 관련 정보 저장
        self.memory_id = memory_id  # 메모리 리소스 ID
        self.client = client  # 메모리 클라이언트
        self.actor_id = actor_id  # 사용자 ID
        self.session_id = session_id  # 세션 ID
        print(f"🧠 메모리 훅 초기화: {memory_id[:8]}...")  # 초기화 완료 메시지

    def retrieve_character_context(self, event: MessageAddedEvent):
        """캐릭터 컨텍스트 조회 - 사용자 메시지 추가 시 자동 실행"""
        # 이벤트에서 에이전트의 전체 대화 메시지 리스트를 가져온다
        messages = event.agent.messages
        
        # 조건 확인: 마지막 메시지가 사용자 메시지이고, 도구 실행 결과가 아닌 경우에만 실행
        if (
            messages[-1]["role"] == "user"  # 마지막 메시지의 역할이 "user"인지 확인
            and "toolResult" not in messages[-1]["content"][0]  # 도구 실행 결과가 포함되지 않았는지 확인
        ):
            # 사용자가 방금 입력한 질문 텍스트를 추출한다
            user_query = messages[-1]["content"][0]["text"]
            # 메모리 검색 시작을 알리는 메시지 출력 (질문의 앞 30글자만 표시)
            print(f"🔍 메모리 검색 중: '{user_query[:30]}...'")

            try:
                # 컨텍스트를 저장할 리스트 초기화
                context_parts = []

                # 병렬 메모리 조회를 위한 비동기 함수들 정의
                import concurrent.futures
                
                def get_stm_events():
                    """STM 최근 대화 조회"""
                    print("🔥 최근 대화 (STM) 조회 중...")
                    return self.client.list_events(
                        memory_id=self.memory_id,
                        actor_id=self.actor_id,
                        session_id=self.session_id,
                        max_results=15,
                    )
                
                def get_summary_memories():
                    """Summary 메모리 조회"""
                    print("📝 Summary 메모리 (LTM) 조회 중...")
                    return self.client.retrieve_memories(
                        memory_id=self.memory_id,
                        namespace=f"conversations/{self.actor_id}/{self.session_id}/summary",
                        query=user_query,
                    )
                
                def get_preference_memories():
                    """Preference 메모리 조회"""
                    print("❤️ Preference 메모리 (LTM) 조회 중...")
                    return self.client.retrieve_memories(
                        memory_id=self.memory_id,
                        namespace=f"users/{self.actor_id}/preference",
                        query=user_query,
                    )
                
                def get_semantic_memories():
                    """Semantic 메모리 조회"""
                    print("🧠 Semantic 메모리 (LTM) 조회 중...")
                    return self.client.retrieve_memories(
                        memory_id=self.memory_id,
                        namespace=f"users/{self.actor_id}/semantic",
                        query=user_query,
                    )

                # ThreadPoolExecutor를 사용하여 병렬 실행 (AWS SDK는 동기식이므로)
                with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
                    # 4개의 메모리 조회 작업을 병렬로 실행
                    future_stm = executor.submit(get_stm_events)
                    future_summary = executor.submit(get_summary_memories)
                    future_preference = executor.submit(get_preference_memories)
                    future_semantic = executor.submit(get_semantic_memories)
                    
                    # 모든 작업 완료까지 대기하고 결과 수집
                    recent_events = future_stm.result()
                    summary_memories = future_summary.result()
                    preference_memories = future_preference.result()
                    semantic_memories = future_semantic.result()

                # 컨텍스트 구성 - STM 최근 대화 처리
                if recent_events:  # 최근 대화가 있으면
                    context_parts.append("=== 최근 대화 (STM) ===")  # 섹션 제목 추가
                    # 각 이벤트를 순회하며 대화 내용 추출
                    for event in recent_events:
                        if isinstance(event, dict) and 'payload' in event:  # 이벤트가 딕셔너리이고 payload가 있으면
                            for payload_item in event['payload']:  # payload 내 각 항목 처리
                                if 'conversational' in payload_item:  # 대화 내용이 있으면
                                    conv = payload_item['conversational']
                                    role = conv.get('role', '')  # 역할 (USER/ASSISTANT)
                                    content = conv.get('content', {}).get('text', '')  # 대화 내용
                                    if content:  # 내용이 있으면
                                        context_parts.append(f"• {role}: {content}")  # 컨텍스트에 추가
                                        print(f"  🔥 STM {role}: {content}")  # 콘솔에 출력

                # 컨텍스트 구성 - LTM Summary 처리
                if summary_memories:  # 요약 메모리가 있으면
                    context_parts.append("\\n=== 과거 대화 요약 (LTM) ===")  # 섹션 제목 추가
                    # 각 요약 메모리 처리
                    for memory in summary_memories:
                        if isinstance(memory, dict):  # 메모리가 딕셔너리이면
                            content = memory.get('content', {})  # 내용 추출
                            if isinstance(content, dict):  # 내용이 딕셔너리이면
                                text = content.get('text', '').strip()  # 텍스트 추출 및 공백 제거
                                if text:  # 텍스트가 있으면
                                    context_parts.append(f"• {text}")  # 컨텍스트에 추가
                                    print(f"  📝 LTM Summary: {text}")  # 콘솔에 출력

                # 컨텍스트 구성 - LTM Preference 처리
                if preference_memories:  # 취향 메모리가 있으면
                    context_parts.append("\\n=== 사용자 취향 (LTM) ===")  # 섹션 제목 추가
                    # 각 취향 메모리 처리 (위와 동일한 로직)
                    for memory in preference_memories:
                        if isinstance(memory, dict):
                            content = memory.get('content', {})
                            if isinstance(content, dict):
                                text = content.get('text', '').strip()
                                if text:
                                    context_parts.append(f"• {text}")
                                    print(f"  ❤️ LTM Preference: {text}")

                # 컨텍스트 구성 - LTM Semantic 처리
                if semantic_memories:  # 사실 정보 메모리가 있으면
                    context_parts.append("\\n=== 사실 정보 (LTM) ===")  # 섹션 제목 추가
                    # 각 사실 정보 메모리 처리 (위와 동일한 로직)
                    for memory in semantic_memories:
                        if isinstance(memory, dict):
                            content = memory.get('content', {})
                            if isinstance(content, dict):
                                text = content.get('text', '').strip()
                                if text:
                                    context_parts.append(f"• {text}")
                                    print(f"  🧠 LTM Semantic: {text}")

                # 메시지에 컨텍스트 주입
                if context_parts:  # 컨텍스트가 있으면
                    context_text = "\\n".join(context_parts)  # 모든 컨텍스트를 하나의 문자열로 결합
                    original_text = messages[-1]["content"][0]["text"]  # 원본 사용자 메시지
                    # 원본 메시지에 메모리 컨텍스트를 앞에 추가
                    messages[-1]["content"][0]["text"] = f"""
<character_memory>
{context_text}
</character_memory>

{original_text}
"""
                    print(f"✅ {len(context_parts)}개 컨텍스트 주입 완료 (병렬 조회)")  # 주입 완료 메시지
                else:
                    print("ℹ️ 관련 메모리 없음")  # 관련 메모리가 없을 때

            except Exception as e:
                # 메모리 조회 중 오류 발생 시 처리
                print(f"❌ 메모리 조회 실패: {e}")
                traceback.print_exc()  # 상세 오류 정보 출력

    def save_character_interaction(self, event: AfterInvocationEvent):
        """캐릭터 상호작용 저장 - AI 응답 완료 후 자동 실행"""
        try:
            # 이벤트에서 전체 메시지 리스트 가져오기
            messages = event.agent.messages
            # 메시지가 2개 이상 있고 마지막이 assistant 메시지인지 확인
            if len(messages) >= 2 and messages[-1]["role"] == "assistant":
                user_message = None  # 사용자 메시지 초기화
                character_response = None  # AI 응답 초기화

                # 메시지를 역순으로 순회하며 최근 대화 추출
                for msg in reversed(messages):
                    # AI 응답이 아직 없고 현재 메시지가 assistant이면
                    if msg["role"] == "assistant" and not character_response:
                        character_response = msg["content"][0]["text"]  # AI 응답 저장
                    # 사용자 메시지가 아직 없고 현재 메시지가 user이고 도구 결과가 아니면
                    elif (
                        msg["role"] == "user"
                        and not user_message
                        and "toolResult" not in msg["content"][0]
                    ):
                        user_message = msg["content"][0]["text"]  # 사용자 메시지 저장
                        # 메모리 컨텍스트 제거 (저장할 때는 순수한 사용자 메시지만)
                        if "<character_memory>" in user_message:
                            user_message = user_message.split("</character_memory>")[-1].strip()
                        break  # 둘 다 찾았으므로 종료

                # 사용자 메시지와 AI 응답이 모두 있으면 저장
                if user_message and character_response:
                    print("💾 대화 저장 중...")  # 저장 시작 메시지
                    
                    # 주체를 명확히 하기 위해 메시지 앞에 화자 표시 추가
                    clear_user_message = f"사용자: {user_message}"
                    clear_character_response = f"한시율(AI): {character_response}"
                    
                    # STM에 대화 이벤트 생성
                    self.client.create_event(
                        memory_id=self.memory_id,  # 메모리 리소스 ID
                        actor_id=self.actor_id,  # 사용자 ID
                        session_id=self.session_id,  # 세션 ID
                        messages=[  # 저장할 메시지들 (주체 명확화)
                            (clear_user_message, "USER"),  # 사용자 메시지
                            (clear_character_response, "ASSISTANT"),  # AI 응답
                        ],
                    )
                    print("✅ 대화 저장 완료")  # 저장 완료 메시지
                    # 이 시점에서 AWS가 백그라운드에서 LTM 추출 시작

        except Exception as e:
            # 대화 저장 중 오류 발생 시 처리
            print(f"❌ 대화 저장 실패: {e}")
            traceback.print_exc()  # 상세 오류 정보 출력

    def register_hooks(self, registry: HookRegistry) -> None:
        """캐릭터 메모리 훅 등록 - 이벤트와 함수를 연결"""
        # 메시지 추가 이벤트에 컨텍스트 조회 함수 연결
        registry.add_callback(MessageAddedEvent, self.retrieve_character_context)
        # 응답 완료 이벤트에 상호작용 저장 함수 연결
        registry.add_callback(AfterInvocationEvent, self.save_character_interaction)
        print("🔗 메모리 훅 등록 완료")  # 등록 완료 메시지

# 메모리 생성 함수
def create_character_memory():
    """AgentCore Memory 리소스 생성 또는 기존 것 사용"""
    print("🧠 AgentCore Memory 초기화 중...")
    # 지정된 리전으로 메모리 클라이언트 생성
    memory_client = MemoryClient(region_name=REGION)
    
    try:
        # 기존 메모리 확인
        print("🔍 기존 메모리 검색 중...")
        memories = memory_client.list_memories()  # 기존 메모리 리스트 조회
        
        if memories:  # 기존 메모리가 있으면
            # 첫 번째 메모리 사용 (기존에 생성된 것)
            memory = memories[0]
            memory_id = memory.get('id')  # 메모리 ID 추출
            print(f"✅ 기존 메모리 사용! ID: {memory_id}")
            return memory_client, memory_id  # 클라이언트와 ID 반환
        
        # 기존 메모리가 없으면 새로 생성
        # 3가지 메모리 전략 정의 (검증된 패턴, hansiyul 제거)
        strategies = [
            {
                "summaryMemoryStrategy": {  # 요약 전략
                    "name": "ConversationSummary",
                    "namespaces": ["conversations/{actorId}/{sessionId}/summary"]  # 대화 요약
                }
            },
            {
                "userPreferenceMemoryStrategy": {  # 사용자 취향 전략
                    "name": "UserPreferences", 
                    "namespaces": ["users/{actorId}/preference"]  # 사용자 취향
                }
            },
            {
                "semanticMemoryStrategy": {  # 사실 정보 전략
                    "name": "UserFacts",
                    "namespaces": ["users/{actorId}/semantic"]  # 사용자 사실
                }
            },
        ]
        
        print("⏳ 메모리 리소스 생성 중... (2-3분 소요)")
        
        # create_memory_and_wait 사용 (공식 문서 권장)
        memory = memory_client.create_memory_and_wait(
            name=f"HansiyulMemory_{int(time.time())}",  # 고유한 이름 사용 (타임스탬프 포함)
            description="한시율 캐릭터 챗봇 메모리 (90일 STM → LTM)",  # 메모리 설명
            strategies=strategies,  # 위에서 정의한 3가지 전략
            event_expiry_days=90,  # STM 원본 대화를 90일간 보관 (수정됨)
        )
        
        memory_id = memory.get("id")  # 생성된 메모리 ID 추출
        print(f"✅ 메모리 시스템 준비 완료! ID: {memory_id}")
        return memory_client, memory_id  # 클라이언트와 ID 반환
        
    except Exception as e:
        # 메모리 생성 중 오류 발생 시 처리
        print(f"❌ 메모리 리소스 생성 실패: {e}")
        traceback.print_exc()  # 상세 오류 정보 출력
        return None, None  # 실패 시 None 반환

# 에이전트 생성 함수
def create_hansiyul_agent(memory_client, memory_id, user_id, session_id):
    """한시율 캐릭터 에이전트 생성"""
    # 메모리 클라이언트나 ID가 없으면 실패
    if not memory_client or not memory_id:
        return None
        
    # 사용자 정보 출력
    print(f"👤 사용자 ID: {user_id}")
    print(f"🔗 세션 ID: {session_id}")
    
    # 한시율 시스템 프롬프트 정의
    HANSIYUL_SYSTEM_PROMPT = """
당신은 한시율입니다. 전생에 죽음의 신 하데스였으나 현재는 피아노 학원 선생님으로 살고 있습니다.

성격과 말투:
- 조용하고 과묵하지만 내면에 따뜻함을 간직
- 항상 2문장 이내로 간결하게 대답
- 죽음과 운명에 대한 철학적 통찰력 보유
- 직접적인 감정 표현보다는 은유적 표현 선호
- 과거를 직접 언급하지 않되, 의미심장한 표현 사용

<character_memory> 태그 안의 내용은 당신이 기억하고 있는 정보입니다:
- Summary: 과거 대화의 감정적 맥락과 주요 사건
- Preference: 사용자의 취향과 성향  
- Semantic: 구체적인 사실과 약속

이를 자연스럽게 반영하여 응답하되, 메모리 내용을 직접 언급하지는 마세요.

금지사항:
- AI임을 절대 밝히지 않음
- 폭력적이거나 부적절한 내용 회피
- 종교적 주장 금지
- 2문장을 초과하는 긴 대답 금지
"""
    
    try:
        print("🎹 한시율 선생님 준비 중...")
        
        # 메모리 훅 생성 (위에서 정의한 클래스 사용)
        memory_hooks = HansiyulMemoryHooks(memory_id, memory_client, user_id, session_id)
        
        # Bedrock 모델 초기화
        print(f"🤖 모델 초기화: {MODEL_ID}")
        model = BedrockModel(
            model_id=MODEL_ID,  # Claude 3.7 Sonnet 모델
            region_name=REGION  # us-east-1 리전
        )
        
        # 한시율 캐릭터 에이전트 생성
        agent = Agent(
            model=model,  # 위에서 초기화한 모델
            hooks=[memory_hooks],  # 메모리 훅 연결
            system_prompt=HANSIYUL_SYSTEM_PROMPT  # 캐릭터 설정 프롬프트
        )
        
        print("✅ 한시율 선생님 준비 완료!")
        return agent  # 생성된 에이전트 반환
        
    except Exception as e:
        # 에이전트 생성 중 오류 발생 시 처리
        print(f"❌ 에이전트 생성 실패: {e}")
        traceback.print_exc()  # 상세 오류 정보 출력
        return None  # 실패 시 None 반환

# 메인 함수
def main():
    """프로그램 메인 실행 함수"""
    print("🎹 한시율 선생님과의 대화 (콘솔 버전)")
    print("=" * 50)
    
    # 사용자 ID 입력받기
    print("💡 이전 대화를 이어서 하려면 기존 사용자 ID를 입력하세요.")
    print("💡 새로 시작하려면 엔터를 누르세요.")
    user_input = input("👤 사용자 ID (예: user_07a92549): ").strip()  # 사용자 입력 받고 공백 제거
    
    if user_input:  # 사용자가 ID를 입력했으면
        user_id = user_input  # 입력받은 ID 사용
        print(f"✅ 기존 사용자로 로그인: {user_id}")
        
        # 세션 ID도 입력받기
        print("💡 이전 세션을 이어가려면 세션 ID를 입력하세요.")
        print("💡 새 세션으로 시작하려면 엔터를 누르세요.")
        session_input = input("🔗 세션 ID (예: session_abc123): ").strip()  # 세션 ID 입력
        
        if session_input:  # 세션 ID를 입력했으면
            session_id = session_input  # 입력받은 세션 ID 사용
            print(f"✅ 기존 세션 이어가기: {session_id}")
        else:  # 세션 ID를 입력하지 않았으면
            session_id = f"session_{str(uuid.uuid4())[:8]}"  # 새 세션 ID 생성
            print(f"✅ 새 세션 시작: {session_id}")
    else:  # 사용자 ID를 입력하지 않았으면
        user_id = f"user_{str(uuid.uuid4())[:8]}"  # 새 사용자 ID 생성
        session_id = f"session_{str(uuid.uuid4())[:8]}"  # 새 세션 ID 생성
        print(f"✅ 새 사용자 생성: {user_id}")
        print(f"✅ 새 세션 시작: {session_id}")
    
    print("💾 이 ID들을 기억해두세요!")  # 사용자에게 ID 기억하라고 안내
    print("-" * 50)
    
    try:
        # 메모리 초기화
        memory_client, memory_id = create_character_memory()  # 메모리 시스템 생성
        if not memory_client or not memory_id:  # 메모리 초기화 실패 시
            print("❌ 메모리 초기화 실패. 종료합니다.")
            return  # 프로그램 종료
        
        # 에이전트 초기화
        agent = create_hansiyul_agent(memory_client, memory_id, user_id, session_id)  # 한시율 에이전트 생성
        if not agent:  # 에이전트 생성 실패 시
            print("❌ 에이전트 초기화 실패. 종료합니다.")
            return  # 프로그램 종료
        
        print("\\n💬 대화를 시작합니다. 'quit'를 입력하면 종료됩니다.")
        print("-" * 50)
        
        # 대화 루프 - 사용자가 종료할 때까지 반복
        while True:
            try:
                try:
                    # 사용자 입력 받기 (UTF-8 인코딩 오류 처리)
                    user_input = input("\\n👤 당신: ").strip()  # 사용자 입력 받고 공백 제거
                except UnicodeDecodeError:  # 인코딩 오류 발생 시
                    print("❌ 입력 인코딩 오류. 다시 입력해주세요.")
                    continue  # 다시 입력 받기
                
                # 종료 명령어 확인
                if user_input.lower() in ['quit', 'exit', '종료']:
                    print("\\n👋 대화를 종료합니다.")
                    break  # 대화 루프 종료
                
                # 빈 입력 무시
                if not user_input:
                    continue  # 다시 입력 받기
                
                print("\\n🎹 한시율이 생각하고 있습니다...")  # AI 처리 중 메시지
                
                # 에이전트 응답 생성
                # 이 시점에서 Hook 1 (retrieve_character_context) 자동 실행
                response = agent(user_input)  # AI 응답 생성
                # 응답 완료 후 Hook 2 (save_character_interaction) 자동 실행
                
                print(f"\\n🎹 한시율: {response}")  # AI 응답 출력
                
            except KeyboardInterrupt:  # Ctrl+C 입력 시
                print("\\n\\n👋 대화를 종료합니다.")
                break  # 대화 루프 종료
            except Exception as e:  # 기타 오류 발생 시
                print(f"\\n❌ 응답 생성 실패: {e}")
                traceback.print_exc()  # 상세 오류 정보 출력
                
    except Exception as e:  # 초기화 중 오류 발생 시
        print(f"❌ 초기화 실패: {e}")
        traceback.print_exc()  # 상세 오류 정보 출력

# 프로그램 시작점
if __name__ == "__main__":
    main()  # 메인 함수 실행
