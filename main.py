from fastapi import FastAPI, HTTPException, status, Response, Depends, Cookie
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
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

pwd = PasswordHash(hashers=[Argon2Hasher])
cols = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    score INTEGER DEFAULT 0
)
"""

def create_token(data: dict, time: datetime.timedelta = datetime.timedelta(hours=24)):
    expire = now = datetime.datetime.now(datetime.timezone.utc)
    expire += time
    payload = data.copy()
    payload.update({"exp": expire, "iat": now})
    return jwt.encode(payload, os.getenv("SECRET_KEY"), algorithm="HS256")

def decode_token(token: str):
    try:
        payload = jwt.decode(token, os.getenv("SECRET_KEY"), algorithms=["HS256"])
        return True, payload
    except jwt.ExpiredSignatureError:
        return False, jwt.ExpiredSignatureError
    except jwt.InvalidTokenError:
        return False, jwt.InvalidTokenError

@app.post("/api/user", status_code=status.HTTP_201_CREATED)
async def signup(form_data: OAuth2PasswordRequestForm = Depends()):
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
            await con.commit()
        except aiosqlite.IntegrityError:
            raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Used username"
        )
    return {"detail": "Created", }

@app.post("/api/user/login")
async def login(response: Response, form_data: OAuth2PasswordRequestForm = Depends()):
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
                detail="Wrong username or password",
                headers={"WWW-Authenticate": "Bearer"}
            )
        ver = pwd.verify_and_update(form_data.password, user["password"])
        if not ver[0]:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Wrong username or password",
                headers={"WWW-Authenticate": "Bearer"}
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
        samesite="lax",
        secure=os.getenv("IS_PRODUCTION") == "true"
    )
    return {"detail": "Success"}

async def get_current_user(access_token: str = Cookie(None)):
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not logged in",
            headers={"WWW-Authenticate": "Bearer"}
        )
    success, payload = decode_token(access_token)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or invalid request",
            headers={"WWW-Authenticate": "Bearer"}
        )
    username = payload.get("sub")
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid request",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return username

@app.post("/api/user/logout")
async def logout(response: Response, score: int, current_user: str = Depends(get_current_user)):
    async with aiosqlite.connect("data.db") as con:
        await con.execute(
            "UPDATE users SET score = ? WHERE username = ?",
            (score, current_user)
        )
        await con.commit()
    response.delete_cookie(
        key="access_token",
        httponly=True,
        secure=os.getenv("IS_PRODUCTION") == "true",
        samesite="lax"
    )
    return {"detail": "Logged out"}

app.mount("/assets", StaticFiles(directory="react-game/dist/assets"), name="assets")
app.mount("/images", StaticFiles(directory="react-game/dist/images"), name="images")

@app.get("/{catchall:path}")
async def serve_frontend():
    return FileResponse("react-game/dist/index.html")