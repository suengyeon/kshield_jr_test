# 🔧 팀원 환경 설정 동기화 가이드

## 📋 문제점 분석 결과

### 1. DB 동기화 문제
**현상**: 팀원이 가입한 사용자가 Admin 대시보드에 보이지 않음

**원인**: 각 컴퓨터가 독립적인 SQLite DB 파일 사용
```
Admin 노트북:   c:\Users\Admin\cloudsec-app\instance\metadata.db
팀원 노트북:   c:\Users\[팀원명]\cloudsec-app\instance\metadata.db
```

**해결책 (3가지 옵션)**:

#### ✅ 옵션 1: Docker Compose로 공유 DB 사용 (권장)
```bash
# docker-compose.yml에서 PostgreSQL 또는 MySQL 사용
docker-compose up -d
```
→ 모든 팀원이 같은 컨테이너의 DB에 접근

#### ✅ 옵션 2: MySQL/PostgreSQL로 변경
```bash
pip install mysql-connector-python
```

app.py 수정:
```python
import mysql.connector
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password")
DB_NAME = os.getenv("DB_NAME", "cloudsec_app")
```

#### ✅ 옵션 3: 네트워크 공유 폴더로 SQLite DB 공유
```bash
# Windows 공유 폴더 경로
\\[Admin_IP]\cloudsec-app\instance\metadata.db
```
→ 성능 문제 가능성 있음 (권장하지 않음)

---

## 📝 팀원 체크리스트 (필수 설정)

### **Step 1: .env 파일 생성**
```bash
# 팀원 로컬에서 생성
cp .env.example .env
```

### **Step 2: .env 파일에 다음 값 입력**
```env
FLASK_SECRET_KEY=super-secret-change-this
AWS_DEFAULT_REGION=ap-northeast-2
S3_BUCKET_NAME=cloudsec-corp-storage-0501
AWS_ACCESS_KEY_ID=YOUR_AWS_ACCESS_KEY
AWS_SECRET_ACCESS_KEY=YOUR_AWS_SECRET_KEY
APP_DEFAULT_USERNAME=admin
APP_DEFAULT_PASSWORD=ChangeMe123!
```

#### 🔐 AWS 자격증명 확인 방법:
```bash
# 1. 기존 AWS 자격증명 확인
cat ~/.aws/credentials

# 2. AWS CLI로 확인
aws sts get-caller-identity

# 3. 권한 확인
aws s3 ls s3://cloudsec-corp-storage-0501
```

### **Step 3: 환경 변수 로드 확인**
```bash
python app.py
# 로그에서 다음이 보여야 함:
# ==================================================
# Flask 앱 시작 - 환경 변수 로드 상태:
#   DB Path: ...
#   S3 Bucket: cloudsec-corp-storage-0501
#   AWS Region: ap-northeast-2
#   AWS Credentials: ✓ 로드됨
#   FLASK_SECRET_KEY: ✓ 설정됨
# ==================================================
```

---

## 🧪 연결 테스트 코드

### **DB 연결 테스트**
```python
# test_db_connection.py
import sqlite3
from pathlib import Path

DB_PATH = Path("instance/metadata.db")
try:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    users = cursor.execute("SELECT COUNT(*) FROM users").fetchone()
    print(f"✓ DB 연결 성공: {users[0]} 명의 사용자")
    conn.close()
except Exception as e:
    print(f"✗ DB 연결 실패: {e}")
```

### **S3 연결 테스트**
```python
# test_s3_connection.py
import os
import boto3
from dotenv import load_dotenv

load_dotenv()

BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
REGION = os.getenv("AWS_DEFAULT_REGION")
AWS_KEY = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET = os.getenv("AWS_SECRET_ACCESS_KEY")

try:
    s3 = boto3.client(
        "s3",
        region_name=REGION,
        aws_access_key_id=AWS_KEY,
        aws_secret_access_key=AWS_SECRET,
    )
    
    # 버킷 존재 확인
    s3.head_bucket(Bucket=BUCKET_NAME)
    print(f"✓ S3 연결 성공: {BUCKET_NAME}")
    
    # 파일 업로드 권한 테스트
    s3.put_object(
        Bucket=BUCKET_NAME,
        Key="test_connection.txt",
        Body=b"Connection test"
    )
    print("✓ S3 업로드 권한 확인")
    
    # 테스트 파일 삭제
    s3.delete_object(Bucket=BUCKET_NAME, Key="test_connection.txt")
    
except boto3.exceptions.Boto3Error as e:
    print(f"✗ S3 연결 실패: {e}")
    if "NoCredentialsError" in str(type(e).__name__):
        print("  → AWS 자격증명을 확인하세요 (.env 파일)")
    elif "403" in str(e):
        print("  → S3 버킷 접근 권한이 없습니다")
    elif "NoSuchBucket" in str(e):
        print(f"  → 버킷 '{BUCKET_NAME}'이 존재하지 않습니다")
```

### **API 통신 테스트**
```python
# test_api_connection.py
import requests
import json
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "http://localhost:5000"

# 1. 회원가입 테스트
print("1️⃣ 회원가입 테스트...")
response = requests.post(f"{BASE_URL}/register", data={
    "username": "testuser",
    "password": "testpass123",
    "password_confirm": "testpass123"
})
print(f"  상태: {response.status_code} {response.reason}")

# 2. 로그인 테스트
print("\n2️⃣ 로그인 테스트...")
response = requests.post(f"{BASE_URL}/login", data={
    "username": "admin",
    "password": "ChangeMe123!"
})
print(f"  상태: {response.status_code}")
print(f"  쿠키: {response.cookies}")

# 3. 관리자 대시보드 접근 테스트
print("\n3️⃣ 관리자 대시보드 접근 테스트...")
response = requests.get(
    f"{BASE_URL}/admin/users",
    cookies=response.cookies
)
print(f"  상태: {response.status_code}")
```

---

## 🔒 CORS 오류 해결

### **증상**:
```
Access to XMLHttpRequest at 'http://localhost:5000/upload' from origin 'http://192.168.1.X:3000' 
has been blocked by CORS policy
```

### **해결책**:
app.py의 `@app.after_request` 데코레이터가 자동으로 CORS 헤더를 추가합니다.

프로덕션 환경에서는:
```python
# requirements.txt에 추가
flask-cors==4.0.0

# app.py 수정
from flask_cors import CORS
CORS(app, origins=["http://192.168.1.X:3000", "http://localhost:3000"])
```

---

## 📡 Docker 환경에서 실행

### **Admin 노트북**:
```bash
docker-compose up -d
# 또는 로컬 실행:
python app.py
```

### **팀원 노트북**:
```bash
# Admin 노트북의 IP 확인
ipconfig

# 팀원의 .env에 Admin IP 입력
DB_HOST=192.168.1.100  # Admin의 IP
S3_BUCKET_NAME=cloudsec-corp-storage-0501
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...

# 실행
docker-compose up -d
```

---

## 🚀 최종 확인사항

- [ ] `.env` 파일이 생성되었는가?
- [ ] `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` 입력했는가?
- [ ] `python app.py` 실행 시 로그에서 "✓ 로드됨"이 보이는가?
- [ ] `test_s3_connection.py` 테스트가 성공하는가?
- [ ] 파일 업로드가 가능한가?
- [ ] 관리자 대시보드에서 팀원 가입 정보가 보이는가?

---

## ❓ 트러블슈팅

### **"NoCredentialsError" 에러**
```
해결: .env 파일의 AWS 자격증명 확인
aws configure
# 또는 ~/.aws/credentials 파일 확인
```

### **"403 Forbidden" 에러**
```
해결: S3 버킷 권한 확인
aws iam get-user
aws iam list-attached-user-policies --user-name YOUR_USER_NAME
```

### **팀원 DB에 Admin 사용자가 보이지 않음**
```
해결: 공유 DB로 전환 (Docker Compose 권장)
또는 Admin의 instance/metadata.db를 팀원에게 전달
```

