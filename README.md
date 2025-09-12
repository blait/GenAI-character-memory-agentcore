# 한시율 캐릭터 챗봇

AWS Agent Core Memory를 활용한 캐릭터 챗봇

## 설치 방법

### 1. 패키지 설치
```bash
pip install -r requirements.txt
```

### 2. AWS 설정
```bash
# AWS CLI 설치 및 설정
aws configure

# 또는 .env 파일 생성
cp .env.example .env
# .env 파일에 AWS 자격 증명 입력
```

### 3. AWS 권한 설정
다음 권한이 필요합니다:
- `bedrock:InvokeModel`
- `bedrock-agentcore:*`
- `iam:PassRole` (메모리 실행 역할용)

## 실행 방법

```bash
streamlit run streamlit_app.py
```

## 필수 AWS 서비스
- Amazon Bedrock (Claude 3.5 Sonnet 모델 액세스)
- Amazon Bedrock Agent Core Memory
- IAM (권한 관리)

## 트러블슈팅

### 메모리 생성 실패
- AWS 권한 확인
- 리전 설정 확인 (us-east-1 권장)

### 모델 호출 실패
- Bedrock 모델 액세스 권한 확인
- Claude 3.5 Sonnet 모델 활성화 확인

### 패키지 설치 실패
```bash
pip install --upgrade pip
pip install -r requirements.txt --force-reinstall
```

## 파일 구조
```
GameCharAI/
├── streamlit_app.py      # 메인 애플리케이션
├── requirements.txt      # 패키지 의존성
├── config.py            # 설정 파일
├── .env.example         # 환경 변수 예시
├── requirements.md      # 개발 요구사항
└── README.md           # 이 파일
```
