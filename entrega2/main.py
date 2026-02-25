import uvicorn
import sqlite3
from fastapi import FastAPI

app = FastAPI()

DB_PATH = "data.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT NOT NULL,
            value TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

init_db()

@app.get("/api/dados")
def read_dados():
    conn = get_db()
    rows = conn.execute("SELECT * FROM items").fetchall()
    conn.close()
    return {"items": [dict(row) for row in rows]}


@app.post("/api/dados")
def create_dados(data: dict):
    conn = get_db()
    for key, value in data.items():
        conn.execute(
            "INSERT INTO items (key, value) VALUES (?, ?)",
            (str(key), str(value)),
        )
    conn.commit()
    conn.close()
    return {"message": "Dados salvos com sucesso", "data": data}


if __name__ == "__main__":
    uvicorn.run("main:app", host="localhost", port=8000, reload=True)