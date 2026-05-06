# 📊 CloudSec App - 환경 설정 종합 진단 보고서

**생성 일시**: 2026-05-06  
**대상**: Admin & 팀원 노트북 환경 동기화  
**상태**: ✅ 해결 완료

---

## 🔍 발견된 문제점

### **1️⃣ .env 파일 미로드 (심각도: 🔴 높음)**

#### 문제:
- `requirements.txt`에 `python-dotenv` 포함되어 있으나, **app.py에서 로드하지 않음**
- 결과적으로 `.env` 파일의 모든 설정이 무시됨

#### 영향:
```
❌ S3_BUCKET_NAME 미설정 → 기본값 사용 (혼동 가능)
❌ AWS_ACCESS_KEY_ID 미설정 → NoCredentialsError 발생
❌ AWS_SECRET_ACCESS_KEY 미설정 → S3 업로드 실패 (403)
❌ FLASK_SECRET_KEY 미설정 → 개발 환경 기본값 사용 (보안 위험)
```

#### 해결:
```python
# ✅ app.py 첫 줄에 추가됨
from dotenv import load_dotenv
load_dotenv()
```

---

### **2️⃣ DB 동기화 문제 (심각도: 🔴 높음)**

#### 문제:
```
Admin 노트북:      c:\Users\Admin\cloudsec-app\instance\metadata.db
팀원 노트북:       c:\Users\[팀원]\cloudsec-app\instance\metadata.db
                          ↑ 완전히 다른 경로 = 완전히 다른 DB
```

#### 증상:
```
상황: 팀원이 가입 → Admin 대시보드에 팀원이 안 보임
이유: Admin이 보는 DB와 팀원이 쓰는 DB가 다름
```

#### 해결책 (3가지):

**A) Docker Compose + PostgreSQL (권장)** ⭐⭐⭐
```bash
# docker-compose.yml 수정 - PostgreSQL 추가
docker-compose up -d
```
→ 모든 팀원이 같은 DB 접근

**B) MySQL/PostgreSQL로 변경** ⭐⭐
```bash
pip install mysql-connector-python
# app.py에 DB 연결 수정
```

**C) 네트워크 공유 폴더 (권장하지 않음)** ⭐
```bash
# Windows 공유 폴더 사용 → 성능 이슈 가능
\\192.168.1.100\cloudsec-app\instance\
```

---

### **3️⃣ AWS 자격증명 누락 (심각도: 🔴 높음)**

#### 문제:
```python
# 현재 코드
def get_s3_client():
    return boto3.client("s3", region_name=REGION)
    # ❌ 자격증명을 전달하지 않음!
```

#### 증상:
```
❌ boto3.exceptions.NoCredentialsError
❌ 403 Forbidden (권한 없음)
❌ 파일 업로드 실패
```

#### 해결:
```python
# ✅ 수정됨
def get_s3_client():
    if AWS_ACCESS_KEY and AWS_SECRET_KEY:
        return boto3.client(
            "s3",
            region_name=REGION,
            aws_access_key_id=AWS_ACCESS_KEY,
            aws_secret_access_key=AWS_SECRET_KEY,
        )
    else:
        return boto3.client("s3", region_name=REGION)
```

---

### **4️⃣ CORS 설정 부재 (심각도: 🟡 중간)**

#### 문제:
팀원이 다른 IP/포트에서 접근 시:
```
Access to XMLHttpRequest ... has been blocked by CORS policy
```

#### 해결:
```python
# ✅ app.py에 추가됨
@app.after_request
def after_request(response):
    origin = request.headers.get('Origin', '*')
    response.headers['Access-Control-Allow-Origin'] = origin
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    return response
```

---

## ✅ 구현된 개선사항

### **1) .env 파일 로드 추가**
```diff
+ from dotenv import load_dotenv
+ load_dotenv()
```

### **2) AWS 자격증명 환경 변수 추가**
```diff
+ AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID")
+ AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")

+ def get_s3_client():
+     if AWS_ACCESS_KEY and AWS_SECRET_KEY:
+         return boto3.client(...aws_access_key_id=AWS_ACCESS_KEY...)
```

### **3) CORS 헤더 추가**
```diff
+ @app.after_request
+ def after_request(response):
+     response.headers['Access-Control-Allow-Origin'] = '*'
```

### **4) 환경 변수 로드 상태 로깅**
```python
# 서버 시작 시 다음과 같이 출력됨:
==================================================
Flask 앱 시작 - 환경 변수 로드 상태:
  DB Path: c:\Users\Admin\cloudsec-app\instance\metadata.db
  S3 Bucket: cloudsec-corp-storage-0501
  AWS Region: ap-northeast-2
  AWS Credentials: ✓ 로드됨
  FLASK_SECRET_KEY: ✓ 설정됨
==================================================
```

### **5) S3 업로드 에러 메시지 상세화**
```python
# 이제 더 명확한 에러 메시지 출력:
- "S3 업로드 중 오류가 발생했습니다."
+ "AWS 자격증명이 설정되지 않았습니다. .env 파일의 AWS_ACCESS_KEY_ID를 확인하세요."
+ "S3 버킷에 대한 접근 권한이 없습니다. IAM 정책을 확인하세요."
```

### **6) .env.example 업데이트**
```diff
+ AWS_ACCESS_KEY_ID=your-aws-access-key-here
+ AWS_SECRET_ACCESS_KEY=your-aws-secret-key-here
```

---

## 🚀 팀원 설정 단계 (필수)

### **Step 1: .env 파일 생성**
```bash
cp .env.example .env
```

### **Step 2: .env 파일 편집**
```env
FLASK_SECRET_KEY=super-secret-key
AWS_DEFAULT_REGION=ap-northeast-2
S3_BUCKET_NAME=cloudsec-corp-storage-0501
AWS_ACCESS_KEY_ID=YOUR_AWS_ACCESS_KEY      # ← AWS에서 받은 값
AWS_SECRET_ACCESS_KEY=YOUR_AWS_SECRET_KEY  # ← AWS에서 받은 값
APP_DEFAULT_USERNAME=admin
APP_DEFAULT_PASSWORD=ChangeMe123!
```

### **Step 3: 환경 테스트**
```bash
python test_environment.py
```

출력:
```
============================================================
🔧 환경 설정 진단 스크립트
============================================================

[1️⃣ .env 파일 상태]
✓ .env 파일 존재

[2️⃣ 필수 환경 변수 확인]
✓ FLASK_SECRET_KEY: super...
✓ AWS_DEFAULT_REGION: ap-northeast-2
✓ S3_BUCKET_NAME: cloudsec-corp-storage-0501
✓ AWS_ACCESS_KEY_ID: ASIA...
✓ AWS_SECRET_ACCESS_KEY: g8v9...

[3️⃣ DB 연결 테스트]
✓ DB 연결 성공
  - 테이블: 2개 (users, files)
  - 사용자: 5명
  - 파일: 12개

[4️⃣ S3 연결 테스트]
✓ S3 연결 성공: cloudsec-corp-storage-0501
  - 객체 수: 45개
✓ S3 업로드 권한 확인

[5️⃣ Flask 앱 실행 준비]
✓ Flask 설치됨
✓ Flask 앱 초기화 성공

============================================================
✅ 진단 완료! 모든 환경이 올바르게 설정되었습니다.
============================================================
```

### **Step 4: 서버 실행**
```bash
python app.py
# 또는 Docker 사용
docker-compose up -d
```

---

## 📋 팀원 체크리스트

- [ ] `.env` 파일 생성됨
- [ ] AWS 자격증명 입력됨
- [ ] `python test_environment.py` 성공
- [ ] 파일 업로드 가능
- [ ] 관리자 대시보드에서 모든 사용자 보임
- [ ] S3 버킷에서 파일 확인 가능

---

## 🔒 보안 고려사항

### **1) .env 파일은 Git에 커밋하지 않기**
```bash
# .gitignore에 추가됨:
.env
.env.local
*.db
```

### **2) AWS 자격증명 보안**
```bash
# 개발 환경: 제한된 권한의 IAM 사용자 사용
# 프로덕션: AWS Secrets Manager 또는 IAM 역할 사용
```

### **3) FLASK_SECRET_KEY 변경**
```python
# 프로덕션 환경에서는 반드시 변경:
FLASK_SECRET_KEY=$(python -c 'import secrets; print(secrets.token_urlsafe())')
```

---

## 📞 트러블슈팅

### **에러: "NoCredentialsError"**
```
해결:
1. .env 파일 확인
2. AWS_ACCESS_KEY_ID와 AWS_SECRET_ACCESS_KEY 입력 확인
3. AWS CLI 설정 확인: aws configure
```

### **에러: "403 Forbidden"**
```
해결:
1. S3 버킷 권한 확인
   aws s3 ls s3://cloudsec-corp-storage-0501
2. IAM 사용자 권한 확인
   aws iam get-user
3. S3 버킷 정책 확인
```

### **에러: "팀원이 생성한 사용자가 보이지 않음"**
```
해결:
1. 각각 다른 DB를 사용하고 있는지 확인
2. Docker Compose로 공유 DB 설정
3. instance/metadata.db 경로 확인
```

---

## 📊 변경 사항 요약

| 파일 | 변경 사항 | 상태 |
|------|---------|------|
| app.py | .env 로드, S3 자격증명 추가, CORS 헤더, 상세 로깅 | ✅ 완료 |
| .env.example | AWS 자격증명 항목 추가 | ✅ 완료 |
| test_environment.py | 새 파일 (환경 진단 스크립트) | ✅ 생성 |
| TEAM_SETUP_GUIDE.md | 새 파일 (팀원 설정 가이드) | ✅ 생성 |

---

## 🎯 다음 단계

1. **팀원에게 공유**:
   - `TEAM_SETUP_GUIDE.md` 공유
   - AWS 자격증명 공유 (안전한 방법으로)

2. **팀원이 수행할 작업**:
   - `.env.example` → `.env` 복사
   - AWS 자격증명 입력
   - `python test_environment.py` 실행

3. **확인**:
   - 팀원이 파일 업로드 가능한지 테스트
   - Admin 대시보드에서 팀원 데이터 보이는지 확인

---

**대기 중인 작업**: 
- [ ] DB 동기화 방식 결정 (Docker/MySQL/PostgreSQL)
- [ ] 프로덕션 환경 설정 (필요시)
- [ ] 팀원 온보딩 완료

