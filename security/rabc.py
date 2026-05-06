from flask import session, abort
from functools import wraps


# 역할 계층
ROLE_HIERARCHY = {
    "user": 1,       # 일반 사용자
    "manager": 2,    # 중간 관리자
    "admin": 3,      # 최상위 관리자
}


# 역할 확인 함수
def has_role(required_role):

    current_role = session.get("role", "user")

    return (
        ROLE_HIERARCHY.get(current_role, 0)
        >= ROLE_HIERARCHY.get(required_role, 0)
    )


# 관리자 전용 데코레이터
def admin_required(view_func):

    @wraps(view_func)
    def wrapped(*args, **kwargs):

        if not has_role("manager"):
            abort(403)

        return view_func(*args, **kwargs)

    return wrapped


# 다운로드 권한 검사
def can_download_file(file_row):

    current_role = session.get("role", "user")
    user_id = session.get("user_id")

    # 파일 소유자
    if file_row["owner_id"] == user_id:
        return True

    # 최상위 관리자
    if current_role == "admin":
        return True

    # 중간 관리자
    if current_role == "manager":
        return True

    # 일반 사용자
    target_levels = [
        int(l.strip())
        for l in file_row["target_levels"].split(",")git --version
    ]

    user_level = session.get("level", 1)

    return user_level in target_levels