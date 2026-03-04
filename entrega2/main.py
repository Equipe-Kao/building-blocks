import os

import psycopg2
import psycopg2.extras
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db():
    conn = psycopg2.connect(DATABASE_URL)
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS items (
            id SERIAL PRIMARY KEY,
            key TEXT NOT NULL,
            value TEXT NOT NULL
        )
        """
    )
    conn.commit()
    cur.close()
    conn.close()


init_db()


@app.get("/api/dados")
def read_dados():
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM items")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return {"items": rows}


@app.post("/api/dados")
def create_dados(data: dict):
    conn = get_db()
    cur = conn.cursor()
    for key, value in data.items():
        cur.execute(
            "INSERT INTO items (key, value) VALUES (%s, %s)",
            (str(key), str(value)),
        )
    conn.commit()
    cur.close()
    conn.close()
    return {"message": "Dados salvos com sucesso", "data": data}


if __name__ == "__main__":
    uvicorn.run("main:app", host="localhost", port=8000, reload=True)