import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# AWS 설정
AWS_REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
AWS_PROFILE = os.getenv("AWS_PROFILE", "default")

# Bedrock 모델 설정 - Claude 3.7 Sonnet
MODEL_ID = "anthropic.claude-3-7-sonnet-20250219-v1:0"

# 메모리 설정
MEMORY_EXPIRY_DAYS = 90

# 캐릭터 설정
CHARACTER_NAME = "한시율"
CHARACTER_DESCRIPTION = "피아노 학원 선생님 (전생: 하데스)"
