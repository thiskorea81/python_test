# 파일: db_connection.py
from __future__ import annotations
import os
from typing import Optional, Tuple
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from pymongo.database import Database

"""
MongoDB 연결 모듈
- 자격정보는 코드에 하드코딩하지 않고, 런타임 주입 또는 환경변수로 사용
- 우선순위 1: 인자로 전달된 username/password
- 우선순위 2: 환경변수 MONGODB_URI 또는 (MONGO_USER/MONGO_PASS/MONGO_HOST/MONGO_APP)
- 반환: (client, db)
"""

DEFAULT_HOST = os.environ.get("MONGO_HOST", "chatbotdb.kq9ai.mongodb.net")
DEFAULT_APP  = os.environ.get("MONGO_APP",  "chatbotdb")
DEFAULT_DB   = os.environ.get("MONGO_DB",   "school_app")


def _build_uri(username: Optional[str], password: Optional[str], host: str, app_name: str) -> str:
    # 전체 URI를 제공하면 최우선 사용
    full_uri = os.environ.get("MONGODB_URI")
    if full_uri:
        return full_uri
    # 런타임 주입
    if username and password:
        return f"mongodb+srv://{username}:{password}@{host}/?appName={app_name}"
    # 환경변수 조합
    env_user = os.environ.get("MONGO_USER")
    env_pass = os.environ.get("MONGO_PASS")
    if env_user and env_pass:
        return f"mongodb+srv://{env_user}:{env_pass}@{host}/?appName={app_name}"
    raise ValueError("MongoDB 자격 정보를 찾을 수 없습니다. (username/password 또는 환경변수)")


def connect(username: Optional[str] = None,
            password: Optional[str] = None,
            host: Optional[str] = None,
            app_name: Optional[str] = None,
            db_name: Optional[str] = None) -> Tuple[MongoClient, Database]:
    """MongoDB 클라이언트/DB 연결을 생성하고 ping으로 확인합니다."""
    host = host or DEFAULT_HOST
    app_name = app_name or DEFAULT_APP
    db_name = db_name or DEFAULT_DB

    uri = _build_uri(username, password, host, app_name)
    client = MongoClient(uri, server_api=ServerApi('1'))
    client.admin.command('ping')  # 연결 확인
    db = client[db_name]
    return client, db


def bootstrap_admin(db: Database,
                    admin_username: str = "admin",
                    admin_password_hash: str = "",
                    hash_ready: bool = False) -> None:
    """기본 admin 계정 생성(없을 때).
    - admin_password_hash 는 반드시 해시로 전달 권장 (hash_ready=True)
    """
    users = db["users"]
    if users.count_documents({"username": admin_username}) == 0:
        doc = {
            "username": admin_username,
            "role": "admin",
            "must_change_pw": True,
        }
        if hash_ready and admin_password_hash:
            doc["password_hash"] = admin_password_hash
        else:
            doc["password_hash"] = admin_password_hash or ""  # 비워두고 이후 변경 강제
        users.insert_one(doc)

