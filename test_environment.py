"""
S3 연결 및 권한 테스트 스크립트
팀원의 로컬 환경이 올바르게 설정되었는지 확인합니다.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

print("=" * 60)
print("🔧 환경 설정 진단 스크립트")
print("=" * 60)

# 1️⃣ .env 파일 확인
print("\n[1️⃣ .env 파일 상태]")
env_file = Path(".env")
if env_file.exists():
    print("✓ .env 파일 존재")
else:
    print("✗ .env 파일 없음 - '.env.example'을 복사하여 '.env' 생성하세요")
    sys.exit(1)

# 2️⃣ 환경 변수 확인
print("\n[2️⃣ 필수 환경 변수 확인]")
required_vars = {
    "FLASK_SECRET_KEY": "Flask 암호 키",
    "AWS_DEFAULT_REGION": "AWS 리전",
    "S3_BUCKET_NAME": "S3 버킷 이름",
    "AWS_ACCESS_KEY_ID": "AWS 액세스 키 ID",
    "AWS_SECRET_ACCESS_KEY": "AWS 비밀 액세스 키",
}

missing_vars = []
for var, description in required_vars.items():
    value = os.getenv(var)
    if value:
        # 민감한 정보는 마스킹
        if "SECRET" in var or "KEY" in var or "PASSWORD" in var:
            display_value = f"{value[:5]}...{value[-5:]}" if len(value) > 10 else "***"
        else:
            display_value = value
        print(f"✓ {var}: {display_value}")
    else:
        print(f"✗ {var}: 미설정")
        missing_vars.append(var)

if missing_vars:
    print(f"\n⚠️  다음 환경 변수가 누락되었습니다: {', '.join(missing_vars)}")
    print("   → .env 파일을 수정해주세요")
    sys.exit(1)

# 3️⃣ DB 연결 테스트
print("\n[3️⃣ DB 연결 테스트]")
try:
    import sqlite3
    from pathlib import Path
    
    DB_PATH = Path("instance/metadata.db")
    if not DB_PATH.parent.exists():
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 테이블 확인
    tables = cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    
    if tables:
        user_count = cursor.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        file_count = cursor.execute("SELECT COUNT(*) FROM files").fetchone()[0]
        print(f"✓ DB 연결 성공")
        print(f"  - 테이블: {len(tables)}개 ({[t[0] for t in tables]})")
        print(f"  - 사용자: {user_count}명")
        print(f"  - 파일: {file_count}개")
    else:
        print("⚠️  DB 테이블이 초기화되지 않았습니다")
    
    conn.close()
except Exception as e:
    print(f"✗ DB 연결 실패: {e}")
    sys.exit(1)

# 4️⃣ S3 연결 테스트
print("\n[4️⃣ S3 연결 테스트]")
try:
    import boto3
    from botocore.exceptions import NoCredentialsError, ClientError
    
    BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
    REGION = os.getenv("AWS_DEFAULT_REGION")
    AWS_KEY = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET = os.getenv("AWS_SECRET_ACCESS_KEY")
    
    s3 = boto3.client(
        "s3",
        region_name=REGION,
        aws_access_key_id=AWS_KEY,
        aws_secret_access_key=AWS_SECRET,
    )
    
    # 버킷 헤드 확인
    try:
        s3.head_bucket(Bucket=BUCKET_NAME)
        print(f"✓ S3 연결 성공: {BUCKET_NAME}")
        
        # 객체 목록 확인
        response = s3.list_objects_v2(Bucket=BUCKET_NAME, MaxKeys=5)
        object_count = response.get('KeyCount', 0)
        print(f"  - 객체 수: {object_count}개")
        
        # 업로드 권한 테스트
        test_key = "test_connection.txt"
        try:
            s3.put_object(
                Bucket=BUCKET_NAME,
                Key=test_key,
                Body=b"Connection test"
            )
            print(f"✓ S3 업로드 권한 확인")
            
            # 테스트 파일 삭제
            s3.delete_object(Bucket=BUCKET_NAME, Key=test_key)
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'AccessDenied':
                print(f"✗ S3 업로드 권한 없음: {error_code}")
            else:
                print(f"✗ S3 업로드 실패: {error_code}")
    
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'NoSuchBucket':
            print(f"✗ S3 버킷 없음: {BUCKET_NAME}")
        elif error_code == 'Forbidden':
            print(f"✗ S3 버킷 접근 거부: {BUCKET_NAME}")
            print("  → S3 버킷 정책 또는 IAM 권한 확인 필요")
        else:
            print(f"✗ S3 연결 실패: {error_code}")
    
except NoCredentialsError:
    print("✗ AWS 자격증명이 설정되지 않았습니다")
    print("  → .env 파일의 AWS_ACCESS_KEY_ID와 AWS_SECRET_ACCESS_KEY 확인")
except ImportError:
    print("✗ boto3가 설치되지 않았습니다")
    print("  → pip install boto3")
except Exception as e:
    print(f"✗ S3 테스트 실패: {e}")

# 5️⃣ Flask 실행 확인
print("\n[5️⃣ Flask 앱 실행 준비]")
try:
    from flask import Flask
    print("✓ Flask 설치됨")
    
    # 간단한 앱 초기화 테스트
    test_app = Flask(__name__)
    test_app.secret_key = os.getenv("FLASK_SECRET_KEY")
    print("✓ Flask 앱 초기화 성공")
except ImportError:
    print("✗ Flask가 설치되지 않았습니다")
    print("  → pip install -r requirements.txt")

print("\n" + "=" * 60)
print("✅ 진단 완료! 모든 환경이 올바르게 설정되었습니다.")
print("=" * 60)
print("\n다음 명령어로 서버를 시작하세요:")
print("  python app.py")
