from fastapi import FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher
import aiosqlite
import datetime
import dotenv
import jwt
import re
import os

app = FastAPI()

pwd = PasswordHash(hashers=[Argon2Hasher])
cols = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY UNIQUE KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL
)
"""
dotenv.load_dotenv()

def create_token(data: dict, time: datetime.timedelta | None=datetime.timedelta(hours=1)):
    if time:
        expire = datetime.datetime.now(datetime.timezone.utc)
        expire += time
    else:
        expire = None
    return jwt.encode(data.copy().update({"exp": expire}), os.getenv("SECRET_KEY"))

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
    if not re.fullmatch("[A-Za-z_0-9]{6, 20}", form_data.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bad username"
        )
    if not re.fullmatch("[A-Za-z0-9!@#$%^&*-_+=\|/.,~]{8, 20}", form_data.password):
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
async def login(form_data: OAuth2PasswordRequestForm):
    if not re.fullmatch("[A-Za-z_0-9]{6, 20}", form_data.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bad username"
        )
    if not re.fullmatch("[A-Za-z0-9!@#$%^&*-_+=\|/.,~]{8, 20}", form_data.password):
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
        user = user.fetchone()
        ver = pwd.verify_and_update(form_data.password, user["password"])
        if user is None or not ver[0]:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Wrong username or password"
            )
        if ver[1]:
            await cur.execute(
                "UPDATE OR IGNORE users SET password = ? WHERE username = ?",
                (ver[1], form_data.username)
            )
    create_token() # TODO: 여기부터 작성!
    return {"detail": "Success"}