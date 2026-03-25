import os
import json
import threading
import psycopg2
import psycopg2.extras
import uvicorn
import paho.mqtt.client as mqtt
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL   = os.environ.get("DATABASE_URL")
MQTT_BROKER    = str(os.environ.get("MQTT_BROKER"))
MQTT_PORT      = 8883
MQTT_CLIENT_ID = "fastapi-subscriber"
MQTT_USER      = os.environ.get("MQTT_USER")
MQTT_PASSWORD  = os.environ.get("MQTT_PASSWORD")

TOPIC_DADOS      = "building-blocks/dados"
TOPIC_LED_CMD    = "building-blocks/led/comando"   # publish  → ESP32
TOPIC_LED_STATUS = "building-blocks/led/status"    # subscribe ← ESP32

# ── DB ────────────────────────────────────────────────────────────────────────

def get_db():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS sensor_data (
            id          SERIAL PRIMARY KEY,
            device_id   TEXT,
            timestamp   BIGINT,
            temperature FLOAT,
            humidity    FLOAT,
            received_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS led_status (
            id          SERIAL PRIMARY KEY,
            status      TEXT NOT NULL CHECK (status IN ('on', 'off')),
            received_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    conn.commit()
    cur.close()
    conn.close()
    print("Banco inicializado.")

def save_reading(data: dict):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO sensor_data (device_id, timestamp, temperature, humidity)
        VALUES (%s, %s, %s, %s)
        """,
        (
            data.get("device_id"),
            data.get("timestamp"),
            data.get("temperature"),
            data.get("humidity"),
        ),
    )
    conn.commit()
    cur.close()
    conn.close()

def save_led_status(status: str):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO led_status (status) VALUES (%s)",
        (status,),
    )
    conn.commit()
    cur.close()
    conn.close()

def get_last_led_status():
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM led_status ORDER BY received_at DESC LIMIT 1")
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row

# ── MQTT ──────────────────────────────────────────────────────────────────────

# Cliente global para poder publicar nas rotas da API
_mqtt_client: mqtt.Client | None = None

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("MQTT conectado!")
        client.subscribe(TOPIC_DADOS)
        print(f"Subscrito em '{TOPIC_DADOS}'")
        client.subscribe(TOPIC_LED_STATUS)
        print(f"Subscrito em '{TOPIC_LED_STATUS}'")
    else:
        print(f"Falha na conexão MQTT. rc={rc}")

def on_message(client, userdata, msg):
    topic = msg.topic
    try:
        payload = msg.payload.decode().strip()

        if topic == TOPIC_DADOS:
            data = json.loads(payload)
            print(f"[sensor] {data}")
            save_reading(data)

        elif topic == TOPIC_LED_STATUS:
            status = payload.lower()
            if status in ("on", "off"):
                print(f"[led status] {status}")
                save_led_status(status)
            else:
                print(f"[led status] payload inválido: '{payload}'")

    except Exception as e:
        print(f"Erro ao processar mensagem ({topic}): {e}")

def start_mqtt():
    global _mqtt_client
    client = mqtt.Client(client_id=MQTT_CLIENT_ID)
    client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
    client.tls_set()
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_BROKER, MQTT_PORT)
    _mqtt_client = client
    client.loop_forever()

# ── App startup ───────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    thread = threading.Thread(target=start_mqtt, daemon=True)
    thread.start()
    yield

# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Schemas ───────────────────────────────────────────────────────────────────

class InterruptorPayload(BaseModel):
    estado: str   # "on" ou "off"

# ── Rotas ─────────────────────────────────────────────────────────────────────

@app.get("/api/dados")
def read_dados():
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM sensor_data ORDER BY received_at DESC")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return {"items": rows}


@app.post("/api/interruptor")
def interruptor(body: InterruptorPayload):
    """
    Publica 'on' ou 'off' no tópico de comando da LED.
    Corpo: { "estado": "on" } ou { "estado": "off" }
    """
    estado = body.estado.strip().lower()

    if estado not in ("on", "off"):
        raise HTTPException(
            status_code=422,
            detail="Campo 'estado' deve ser 'on' ou 'off'."
        )

    if _mqtt_client is None or not _mqtt_client.is_connected():
        raise HTTPException(
            status_code=503,
            detail="Cliente MQTT não está conectado. Tente novamente em instantes."
        )

    _mqtt_client.publish(TOPIC_LED_CMD, estado)
    print(f"[interruptor] publicado '{estado}' em '{TOPIC_LED_CMD}'")
    return {"message": f"Comando '{estado}' enviado para a LED."}


@app.get("/api/led/status")
def led_status():
    """
    Retorna o último estado confirmado da LED (vindo da ESP32 via MQTT).
    """
    row = get_last_led_status()
    if row is None:
        raise HTTPException(
            status_code=404,
            detail="Nenhum status de LED registrado ainda."
        )
    return dict(row)


if __name__ == "__main__":
    uvicorn.run("main:app", host="localhost", port=8000, reload=True)