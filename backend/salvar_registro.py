import os
import paho.mqtt.client as mqtt
import mysql.connector
import json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# ── Configurações MQTT ──────────────────────────────────────
MQTT_SERVER   = os.getenv("MQTT_SERVER")
MQTT_PORT     = int(os.getenv("MQTT_PORT", 1883))
MQTT_USER     = os.getenv("MQTT_USER")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD")
TOPICO        = os.getenv("MQTT_TOPICO")

# ── Configurações MySQL ─────────────────────────────────────
DB_CONFIG = {
    'host': os.getenv('MYSQLHOST'),
    'port': int(os.getenv('MYSQLPORT', 3306)),
    'user': os.getenv('MYSQLUSER'),
    'password': os.getenv('MYSQLPASSWORD'),
    'database': os.getenv('MYSQLDATABASE')
}

# ── Banco de dados ──────────────────────────────────────────
ultimo_timestamp_salvo = None

def criar_banco():
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS registros (
            id        INT AUTO_INCREMENT PRIMARY KEY,
            cor       VARCHAR(20),
            timestamp DATETIME,
            recebido  DATETIME
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id            INT AUTO_INCREMENT PRIMARY KEY,
            username      VARCHAR(100) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            criado_em     DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def salvar(cor, timestamp):
    global ultimo_timestamp_salvo

    # ignora se já salvou essa mensagem
    if timestamp == ultimo_timestamp_salvo:
        print(f"Ignorado (duplicado): {timestamp}")
        return

    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()

    try:
        ts = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
    except Exception:
        ts = datetime.now()

    cursor.execute(
        "INSERT INTO registros (cor, timestamp, recebido) VALUES (%s, %s, %s)",
        (cor, ts, datetime.now())
    )
    conn.commit()
    conn.close()

    ultimo_timestamp_salvo = timestamp
    print(f"Salvo: cor={cor} | timestamp={ts}")

# ── Callbacks MQTT ──────────────────────────────────────────
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Conectado ao broker MQTT!")
        client.subscribe(TOPICO)
        print(f"Inscrito no tópico: {TOPICO}")
    else:
        print(f"Falha na conexão, código: {rc}")

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        cor       = payload.get("cor", "desconhecido")
        timestamp = payload.get("timestamp", "")
        salvar(cor, timestamp)
    except Exception as e:
        print(f"Erro ao processar mensagem: {e}")

# ── Início ──────────────────────────────────────────────────
criar_banco()

client = mqtt.Client()
client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
client.on_connect = on_connect
client.on_message = on_message

client.connect(MQTT_SERVER, MQTT_PORT, keepalive=60)
client.loop_forever()