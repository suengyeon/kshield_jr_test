# 🔧 AWS 자격증명 오류 해결 가이드 (팀원용)

## **📋 문제**
```
ModuleNotFoundError: No module named 'dotenv'
또는
AWS 자격증명 설정 오류
```

---

## **✅ 해결 방법 (단계별)**

### **Step 1: 필수 패키지 설치**
```bash
pip install -r requirements.txt
```

또는 빠르게:
```bash
pip install python-dotenv flask boto3 flask-cors
```

### **Step 2: .env 파일 생성**

프로젝트 루트에서:
```bash
# Linux/Mac
cp .env.example .env

# Windows PowerShell
Copy-Item .env.example .env
```

### **Step 3: .env 파일에 AWS 자격증명 입력**

메모장 또는 VS Code로 `.env` 파일을 열어서:

```env
FLASK_SECRET_KEY=replace-with-random-secret
AWS_DEFAULT_REGION=ap-northeast-2
S3_BUCKET_NAME=cloudsec-corp-storage-0501
AWS_ACCESS_KEY_ID=AKIA...       # ← Admin이 준 값
AWS_SECRET_ACCESS_KEY=abc123... # ← Admin이 준 값
APP_DEFAULT_USERNAME=admin
APP_DEFAULT_PASSWORD=ChangeMe123!
```

⚠️ **중요**: Admin이 준 자격증명을 정확히 붙여넣으세요!

### **Step 4: .env 파일이 제대로 생성되었는지 확인**

```bash
# Linux/Mac
ls -la .env

# Windows PowerShell
Get-Item .env -Force
```

출력:
```
Mode                 LastWriteTime         Length Name
----                 -------------         ------ ----
-a---           5/6/2026  3:00 PM            123 .env
```

✅ `.env` 파일이 보이면 성공!

### **Step 5: Docker에서 실행할 경우**

```bash
# docker-compose.yml이 자동으로 .env 파일을 로드합니다
docker-compose up -d
```

### **Step 6: 로컬에서 실행할 경우**

```bash
# 환경 진단 테스트
python test_environment.py
```

출력 예시:
```
======================================================================
🔧 환경 설정 진단 스크립트
======================================================================

[1️⃣ .env 파일 상태]
✓ .env 파일 존재

[2️⃣ 필수 환경 변수 확인]
✓ FLASK_SECRET_KEY: replace...
✓ AWS_DEFAULT_REGION: ap-northeast-2
✓ S3_BUCKET_NAME: cloudsec-corp-storage-0501
✓ AWS_ACCESS_KEY_ID: AKIA...
✓ AWS_SECRET_ACCESS_KEY: g8v9...

[3️⃣ DB 연결 테스트]
✓ DB 연결 성공

[4️⃣ S3 연결 테스트]
✓ S3 연결 성공: cloudsec-corp-storage-0501
✓ S3 업로드 권한 확인

[5️⃣ Flask 앱 실행 준비]
✓ Flask 설치됨
✓ Flask 앱 초기화 성공

======================================================================
✅ 진단 완료! 모든 환경이 올바르게 설정되었습니다.
======================================================================
```

### **Step 7: 서버 실행**

```bash
# 옵션 A: Docker 사용 (권장)
docker-compose up -d
# 또는
docker-compose -f docker-compose.postgresql.yml up -d

# 옵션 B: 로컬에서 직접 실행
python app.py
```

실행하면 다음과 같은 로그가 출력됩니다:

```
======================================================================
🚀 Flask 앱 시작 - 환경 변수 진단
======================================================================
📁 현재 디렉토리: /app
📁 .env 파일 경로: /app/.env
✓ .env 파일 존재: True

📋 환경 변수 로드 상태:
  FLASK_SECRET_KEY: ✓ 설정됨
  AWS_DEFAULT_REGION: ap-northeast-2
  S3_BUCKET_NAME: cloudsec-corp-storage-0501
  AWS_ACCESS_KEY_ID: ✓ 로드됨
  AWS_SECRET_ACCESS_KEY: ✓ 로드됨
  APP_DEFAULT_USERNAME: admin

✅ AWS 자격증명 로드 완료! S3 업로드 가능합니다.
======================================================================
```

✅ **이 로그가 보이면 성공!**

---

## **❓ 여전히 안 되나요?**

### **문제 1: ".env 파일이 없다"는 에러**
```bash
# 확인:
ls -la .env  # Linux/Mac
Get-Item .env  # Windows

# 없으면 생성:
Copy-Item .env.example .env
```

### **문제 2: "AWS_ACCESS_KEY_ID이 미설정" 에러**
```bash
# .env 파일 내용 확인:
cat .env  # Linux/Mac
Get-Content .env  # Windows

# AWS_ACCESS_KEY_ID와 AWS_SECRET_ACCESS_KEY가 비어있지 않은지 확인
```

### **문제 3: Docker에서 .env이 로드되지 않음**
```bash
# docker-compose.yml에서 env_file 설정 확인:
cat docker-compose.yml | grep -A 2 "env_file"

# 출력:
# env_file:
#   - .env
```

만약 이 설정이 없으면 Admin에게 알려주세요!

### **문제 4: S3 연결 실패**
```
ERROR: Could not find a version that satisfies the requirement (403 에러)
```

→ AWS_ACCESS_KEY_ID와 AWS_SECRET_ACCESS_KEY가 정확한지 확인하세요!

### **문제 5: "권한 없음" 에러 (403)**
```
AccessDenied: An error occurred (AccessDenied) when calling the PutObject operation
```

→ AWS IAM 사용자의 S3 권한 확인 필요 (Admin에게 요청)

---

## **🚀 최종 체크리스트**

- [ ] `pip install -r requirements.txt` 실행 완료
- [ ] `.env` 파일 생성됨
- [ ] AWS 자격증명 입력됨 (Admin이 준 값)
- [ ] `python test_environment.py` 성공
- [ ] 로그에서 "✅ AWS 자격증명 로드 완료!" 보임
- [ ] 파일 업로드 테스트 완료
- [ ] Admin 대시보드에서 내 정보 보임

---

## **📞 추가 지원**

여전히 문제가 있으면 Admin에게:
1. 에러 메시지 전체 복사
2. `python test_environment.py` 실행 결과 전달
3. `cat .env` (민감 정보 제외) 또는 파일 크기만 알려주기

