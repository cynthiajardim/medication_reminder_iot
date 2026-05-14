import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import mysql.connector
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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

def conectar():
    return mysql.connector.connect(**DB_CONFIG)

def serializar(dados):
    for r in dados:
        if isinstance(r.get("timestamp"), datetime):
            r["timestamp"] = r["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
        if isinstance(r.get("recebido"), datetime):
            r["recebido"] = r["recebido"].strftime("%Y-%m-%d %H:%M:%S")
    return dados

# ── Endpoints ───────────────────────────────────────────────
@app.get("/registros")
def listar_registros():
    conn = conectar()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM registros ORDER BY id DESC")
    dados = cursor.fetchall()
    conn.close()
    return serializar(dados)

@app.get("/tomados")
def listar_tomados():
    conn = conectar()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM registros WHERE cor = 'verde' ORDER BY id DESC")
    dados = cursor.fetchall()
    conn.close()
    return serializar(dados)

@app.get("/resumo")
def resumo():
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
def registros_por_data(data: str):
    conn = conectar()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM registros WHERE DATE(timestamp) = %s ORDER BY id DESC",
        (data,)
    )
    dados = cursor.fetchall()
    conn.close()
    return serializar(dados)