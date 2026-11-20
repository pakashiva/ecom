from flask import Flask
from flask_jwt_extended import JWTManager
import redis
import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

app.config.update(
    JWT_SECRET_KEY=os.environ["JWT_SECRET_KEY"],
    SECRET_KEY=os.environ.get("FLASK_SECRET_KEY", os.environ["JWT_SECRET_KEY"]),
    JWT_TOKEN_LOCATION=["cookies"],
    JWT_COOKIE_SECURE=False,
    JWT_COOKIE_SAMESITE="Lax",
    JWT_COOKIE_CSRF_PROTECT=False,
    JWT_CSRF_CHECK_FORM=True,
    JWT_ACCESS_TOKEN_EXPIRES=timedelta(minutes=15),
)

jwt = JWTManager(app)

redis_client = redis.Redis(
    host="127.0.0.1",
    port=6370,
    decode_responses=True,
    socket_connect_timeout=2, # seconds
    socket_timeout=2, # seconds
)

@jwt.token_in_blocklist_loader
def is_revoked(token_header , payload):
    token_id = payload["jti"]
    return redis_client.exists(f"revoked:{token_id}") > 0
