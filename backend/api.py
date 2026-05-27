import os
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import mysql.connector
from datetime import datetime, timedelta
from dotenv import load_dotenv
from pydantic import BaseModel
import jwt
import bcrypt

load_dotenv()
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Configurações MySQL ─────────────────────────────────────
DB_CONFIG = {
    'host': os.getenv('MYSQLHOST'),
    'port': int(os.getenv('MYSQLPORT', 3306)),
    'user': os.getenv('MYSQLUSER'),
    'password': os.getenv('MYSQLPASSWORD'),
    'database': os.getenv('MYSQLDATABASE')
}

JWT_SECRET      = os.getenv("JWT_SECRET")
JWT_EXPIRY_HOURS = 8

security = HTTPBearer()

# ── Modelos ─────────────────────────────────────────────────
class LoginInput(BaseModel):
    username: str
    password: str

# ── Banco ───────────────────────────────────────────────────
def conectar():
    return mysql.connector.connect(**DB_CONFIG)

def serializar(dados):
    for r in dados:
        if isinstance(r.get("timestamp"), datetime):
            r["timestamp"] = r["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
        if isinstance(r.get("recebido"), datetime):
            r["recebido"] = r["recebido"].strftime("%Y-%m-%d %H:%M:%S")
    return dados

# ── JWT ─────────────────────────────────────────────────────
def criar_token(username: str) -> str:
    payload = {
        "sub": username,
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRY_HOURS)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

def verificar_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=["HS256"])
        return payload["sub"]
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado")
    except Exception:
        raise HTTPException(status_code=401, detail="Token inválido")


# ── Auth ────────────────────────────────────────────────────
@app.post("/login")
def login(data: LoginInput):
    conn = conectar()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM usuarios WHERE username = %s", (data.username,))
    usuario = cursor.fetchone()
    conn.close()

    if not usuario:
        raise HTTPException(status_code=401, detail="Usuário ou senha inválidos")

    senha_valida = bcrypt.checkpw(data.password.encode(), usuario["password_hash"].encode())
    if not senha_valida:
        raise HTTPException(status_code=401, detail="Usuário ou senha inválidos")

    return { "access_token": criar_token(data.username) }

@app.post("/usuarios")
def criar_usuario(data: LoginInput, username: str = Depends(verificar_token)):
    password_hash = bcrypt.hashpw(data.password.encode(), bcrypt.gensalt()).decode()
    try:
        conn = conectar()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO usuarios (username, password_hash) VALUES (%s, %s)",
            (data.username, password_hash)
        )
        conn.commit()
        conn.close()
        return { "message": f"Usuário {data.username} criado com sucesso" }
    except Exception:
        raise HTTPException(status_code=400, detail="Usuário já existe")

# ── Endpoints protegidos ────────────────────────────────────
@app.get("/registros")
def listar_registros(username: str = Depends(verificar_token)):
    conn = conectar()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM registros ORDER BY id DESC")
    dados = cursor.fetchall()
    conn.close()
    return serializar(dados)

@app.get("/tomados")
def listar_tomados(username: str = Depends(verificar_token)):
    conn = conectar()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM registros WHERE cor = 'verde' ORDER BY id DESC")
    dados = cursor.fetchall()
    conn.close()
    return serializar(dados)

@app.get("/resumo")
def resumo(username: str = Depends(verificar_token)):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM registros WHERE cor = 'verde'")
    tomados = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM registros WHERE cor = 'vermelho'")
    nao_tomados = cursor.fetchone()[0]

    conn.close()
    return {
        "total_tomados":     tomados,
        "total_nao_tomados": nao_tomados,
    }

@app.get("/registros/{data}")
def registros_por_data(data: str, username: str = Depends(verificar_token)):
    conn = conectar()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM registros WHERE DATE(timestamp) = %s ORDER BY id DESC",
        (data,)
    )
    dados = cursor.fetchall()
    conn.close()
    return serializar(dados)