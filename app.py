import os
import sqlite3
from datetime import datetime
from functools import wraps
from pathlib import Path
from urllib.parse import quote

import boto3
from flask import (
    Flask,
    Response,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "metadata.db"
BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "cloudsec-corp-storage-0501")
REGION = os.getenv("AWS_DEFAULT_REGION", "ap-northeast-2")
DEFAULT_USERNAME = os.getenv("APP_DEFAULT_USERNAME", "admin")
DEFAULT_PASSWORD = os.getenv("APP_DEFAULT_PASSWORD", "ChangeMe123!")

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-change-me")


def get_s3_client():
    return boto3.client("s3", region_name=REGION)


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_error):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(DB_PATH)
    cursor = db.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id INTEGER NOT NULL,
            uploaded_by INTEGER NOT NULL,
            original_name TEXT NOT NULL,
            s3_key TEXT UNIQUE NOT NULL,
            size_bytes INTEGER NOT NULL,
            uploaded_at TEXT NOT NULL,
            FOREIGN KEY(owner_id) REFERENCES users(id),
            FOREIGN KEY(uploaded_by) REFERENCES users(id)
        )
        """
    )
    columns = {row[1] for row in cursor.execute("PRAGMA table_info(files)").fetchall()}
    if "uploaded_by" not in columns:
        cursor.execute("ALTER TABLE files ADD COLUMN uploaded_by INTEGER")
        cursor.execute("UPDATE files SET uploaded_by = owner_id WHERE uploaded_by IS NULL")

    user = cursor.execute(
        "SELECT id FROM users WHERE username = ?", (DEFAULT_USERNAME,)
    ).fetchone()
    if not user:
        cursor.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (DEFAULT_USERNAME, generate_password_hash(DEFAULT_PASSWORD)),
        )
    db.commit()
    db.close()


def login_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)

    return wrapped


@app.route("/")
@login_required
def index():
    db = get_db()
    files = db.execute(
        """
        SELECT id, uploaded_by, original_name, size_bytes, uploaded_at
        FROM files
        ORDER BY uploaded_at DESC
        """
    ).fetchall()
    return render_template("index.html", files=files, username=session["username"])


@app.route("/upload", methods=["POST"])
@login_required
def upload():
    uploaded_file = request.files.get("file")
    if not uploaded_file or not uploaded_file.filename:
        flash("업로드할 파일을 선택해주세요.", "warning")
        return redirect(url_for("index"))

    filename = uploaded_file.filename
    if not filename.strip():
        flash("유효하지 않은 파일명입니다.", "danger")
        return redirect(url_for("index"))

    # Keep original filename for DB/UI and use sanitized name only in S3 object key.
    safe_name_for_key = secure_filename(filename) or "uploaded_file"
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
    s3_key = f"{session['user_id']}/{timestamp}_{safe_name_for_key}"
    
    # Get file size before uploading
    uploaded_file.stream.seek(0, 2)  # Seek to end
    file_size = uploaded_file.stream.tell()
    uploaded_file.stream.seek(0)  # Reset pointer to beginning
    
    try:
        s3 = get_s3_client()
        s3.upload_fileobj(uploaded_file.stream, BUCKET_NAME, s3_key)
    except Exception:
        flash("S3 업로드 중 오류가 발생했습니다.", "danger")
        return redirect(url_for("index"))

    uploaded_at = datetime.utcnow().isoformat(timespec="seconds")
    db = get_db()
    db.execute(
        """
        INSERT INTO files (owner_id, uploaded_by, original_name, s3_key, size_bytes, uploaded_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            session["user_id"],
            session["user_id"],
            filename,
            s3_key,
            file_size,
            uploaded_at,
        ),
    )
    db.commit()
    flash("파일이 업로드되었습니다.", "success")
    return redirect(url_for("index"))


@app.route("/download")
@login_required
def download():
    file_id = request.args.get("id", type=int)
    if not file_id:
        flash("잘못된 요청입니다.", "danger")
        return redirect(url_for("index"))

    db = get_db()
    file_row = db.execute(
        """
        SELECT original_name, s3_key
        FROM files
        WHERE id = ? AND owner_id = ?
        """,
        (file_id, session["user_id"]),
    ).fetchone()
    if not file_row:
        flash("파일 접근 권한이 없습니다.", "danger")
        return redirect(url_for("index"))

    try:
        s3_obj = get_s3_client().get_object(Bucket=BUCKET_NAME, Key=file_row["s3_key"])
    except Exception:
        flash("파일 다운로드 중 오류가 발생했습니다.", "danger")
        return redirect(url_for("index"))

    filename_header = quote(file_row["original_name"])
    return Response(
        s3_obj["Body"].read(),
        mimetype="application/octet-stream",
        headers={
            "Content-Disposition": (
                f"attachment; filename*=UTF-8''{filename_header}"
            )
        },
    )


@app.route("/delete", methods=["POST"])
@login_required
def delete():
    file_id = request.form.get("id", type=int)
    if not file_id:
        flash("잘못된 요청입니다.", "danger")
        return redirect(url_for("index"))

    db = get_db()
    file_row = db.execute(
        """
        SELECT id, s3_key
        FROM files
        WHERE id = ? AND owner_id = ?
        """,
        (file_id, session["user_id"]),
    ).fetchone()
    if not file_row:
        flash("파일 접근 권한이 없습니다.", "danger")
        return redirect(url_for("index"))

    try:
        get_s3_client().delete_object(Bucket=BUCKET_NAME, Key=file_row["s3_key"])
    except Exception:
        flash("S3 삭제 중 오류가 발생했습니다.", "danger")
        return redirect(url_for("index"))

    db.execute("DELETE FROM files WHERE id = ?", (file_row["id"],))
    db.commit()
    flash("파일이 삭제되었습니다.", "success")
    return redirect(url_for("index"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        db = get_db()
        user = db.execute(
            "SELECT id, username, password_hash FROM users WHERE username = ?",
            (username,),
        ).fetchone()

        if not user or not check_password_hash(user["password_hash"], password):
            flash("아이디 또는 비밀번호가 올바르지 않습니다.", "danger")
            return render_template("login.html")

        session.clear()
        session["user_id"] = user["id"]
        session["username"] = user["username"]
        return redirect(url_for("index"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


init_db()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
