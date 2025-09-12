# AWS 설정 가이드

## 1. IAM 권한 설정

### 필수 권한 정책
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "bedrock:InvokeModel",
                "bedrock:InvokeModelWithResponseStream"
            ],
            "Resource": [
                "arn:aws:bedrock:*::foundation-model/*",
                "arn:aws:bedrock:*:*:inference-profile/*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "bedrock-agentcore:*"
            ],
            "Resource": "*"
        }
    ]
}
```

### 메모리 실행 역할 (선택사항)
커스텀 메모리 전략 사용 시 필요:

**신뢰 정책:**
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": "bedrock-agentcore.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
        }
    ]
}
```

## 2. Bedrock 모델 액세스

1. AWS 콘솔 → Bedrock → Model access
2. **Claude 3.7 Sonnet** 모델 활성화
3. 리전: us-east-1 권장

## 3. AWS CLI 설정

```bash
aws configure
# AWS Access Key ID: [your-key]
# AWS Secret Access Key: [your-secret]
# Default region name: us-east-1
# Default output format: json
```

## 4. 테스트 명령어

```bash
# Bedrock 액세스 테스트
aws bedrock list-foundation-models --region us-east-1

# Agent Core 서비스 테스트
aws bedrock-agentcore list-memories --region us-east-1

# Claude 3.7 Sonnet 모델 확인
aws bedrock get-foundation-model --model-identifier anthropic.claude-3-7-sonnet-20250109-v1:0 --region us-east-1
```
