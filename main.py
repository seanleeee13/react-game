from fastapi import FastAPI, HTTPException, status, Response, Depends, Cookie
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher
from contextlib import asynccontextmanager
import aiosqlite
import datetime
import dotenv
import jwt
import re
import os

dotenv.load_dotenv()

@asynccontextmanager
async def lifespan(_: FastAPI):
    async with aiosqlite.connect("data.db") as con:
        await con.execute(cols)
        await con.commit()
    yield

app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("CLIENT_ADDRESS")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

pwd = PasswordHash(hashers=[Argon2Hasher])
cols = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL
    score INTEGER DEFAULT 0
)
"""

def create_token(data: dict, time: datetime.timedelta=datetime.timedelta(hours=24)):
    expire = now = datetime.datetime.now(datetime.timezone.utc)
    expire += time
    payload = data.copy()
    payload.update({"exp": expire, "iat": now})
    return jwt.encode(payload, os.getenv("SECRET_KEY"))

def decode_token(token: str):
    try:
        payload = jwt.decode(token, os.getenv("SECRET_KEY"), algorithms=["HS256"])
        return True, payload
    except jwt.ExpiredSignatureError:
        return False, jwt.ExpiredSignatureError
    except jwt.InvalidTokenError:
        return False, jwt.InvalidTokenError

@app.get("/")
async def root():
    return {"message": "Hello, world!"}

@app.post("/user", status_code=status.HTTP_201_CREATED)
async def signup(form_data: OAuth2PasswordRequestForm):
    if not re.fullmatch("[A-Za-z_0-9]{6,20}", form_data.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bad username"
        )
    if not re.fullmatch("[A-Za-z0-9!@#$%^&*-_+=\|/.,~]{8,20}", form_data.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bad password"
        )
    async with aiosqlite.connect("data.db") as con:
        cur = await con.cursor()
        await cur.execute(cols)
        try:
            await cur.execute(
                "INSERT INTO users (username, password) VALUES (?, ?)",
                (form_data.username, pwd.hash(form_data.password))
            )
        except aiosqlite.IntegrityError:
            raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Used username"
        )
    return {"detail": "Created", }

@app.post("/user/login")
async def login(response: Response, form_data: OAuth2PasswordRequestForm):
    if not re.fullmatch("[A-Za-z_0-9]{6,20}", form_data.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bad username"
        )
    if not re.fullmatch("[A-Za-z0-9!@#$%^&*-_+=\|/.,~]{8,20}", form_data.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bad password"
        )
    async with aiosqlite.connect("data.db") as con:
        con.row_factory = aiosqlite.Row
        cur = await con.cursor()
        await cur.execute(cols)
        user = await cur.execute(
            "SELECT * FROM users WHERE username = ?",
            (form_data.username, )
        )
        user = await user.fetchone()
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Wrong username or password"
            )
        ver = pwd.verify_and_update(form_data.password, user["password"])
        if not ver[0]:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Wrong username or password"
            )
        if ver[1]:
            await cur.execute(
                "UPDATE OR IGNORE users SET password = ? WHERE username = ?",
                (ver[1], form_data.username)
            )
            await con.commit()
    token = create_token({"sub": form_data.username})
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        max_age=604800,
        expires=604800,
        samesite="none",
        secure=os.getenv("IS_PRODUCTION") == "true"
    )
    return {"detail": "Success"}

async def get_current_user(access_token: str=Cookie(None)):
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="" # not loged in? TODO 여기
        )

@app.post("/user/logout")
async def logout(response: Response, score: int, current_user: str=Depends(get_current_user)): # TODO: 여기!
    # 1. 점수 업데이트 (aiosqlite)
    async with aiosqlite.connect("data.db") as con:
        await con.execute(
            "UPDATE users SET score = ? WHERE username = ?",
            (score, current_user)
        )
        await con.commit()

    # 2. 쿠키 삭제 (로그인 때와 옵션이 똑같아야 확실히 삭제됨)
    response.delete_cookie(
        key="access_token",
        httponly=True,
        secure=True,     # 배포 환경 기준
        samesite="none"  # 배포 환경 기준
    )
    return {"detail": "Logged out and score saved"}