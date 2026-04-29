from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse, RedirectResponse
import requests
import sqlite3
import random
import os
import unicodedata
import re
import datetime

app = FastAPI()

# =========================
# CONFIG
# =========================

DB_PATH = "filmes.db"
LOG_FILE = "logs_erros.txt"

TIMEOUT_CONNECT = 5
TIMEOUT_READ = 120
CHUNK_SIZE = 1024 * 256

AGENTES = [
    "EPPIPROPLAYER/1.0.8",
    "OTT Navigator",
    "VLC/3.0.20",
    "ExoPlayerLib/2.19.1",
    "Mozilla/5.0 (Linux; Android 14) Chrome/120 Mobile"
]

# =========================
# HEALTH CHECK (KOYEB OBRIGATÓRIO)
# =========================
@app.get("/")
def home():
    return {"status": "ok", "service": "cine-mega"}

# =========================
# LOG
# =========================

def log(err, title="", url=""):
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"\n{datetime.datetime.now()}\n{title}\n{url}\n{err}\n")
    except:
        pass

# =========================
# LIMPAR TEXTO
# =========================

def limpar(txt):
    if not txt:
        return ""

    txt = ''.join(
        c for c in unicodedata.normalize('NFD', str(txt))
        if unicodedata.category(c) != 'Mn'
    )

    txt = re.sub(r'[^a-zA-Z0-9\s]', ' ', txt)
    txt = re.sub(r'\s+', ' ', txt)

    return txt.strip().lower()

# =========================
# DB SIMPLES E RÁPIDO
# =========================

def buscar_filme(titulo):
    t = limpar(titulo)

    if not os.path.exists(DB_PATH):
        return None

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # exato
    c.execute("""
        SELECT id, nome, url
        FROM filmes
        WHERE nome_busca = ?
        LIMIT 1
    """, (t,))

    res = c.fetchone()

    if res:
        conn.close()
        return res

    # fallback leve
    c.execute("""
        SELECT id, nome, url
        FROM filmes
        WHERE nome_busca LIKE ?
        LIMIT 1
    """, (f"{t}%",))

    res = c.fetchone()
    conn.close()

    return res

# =========================
# STREAM (SEM PENDENTE)
# =========================

def stream(url, title, request):

    try:
        headers = {
            "User-Agent": random.choice(AGENTES),
            "Accept": "*/*",
            "Connection": "keep-alive",
            "Accept-Encoding": "identity"
        }

        range_header = request.headers.get("Range")
        if range_header:
            headers["Range"] = range_header

        r = requests.get(
            url,
            headers=headers,
            stream=True,
            timeout=(TIMEOUT_CONNECT, TIMEOUT_READ),
            allow_redirects=True
        )

        # se falhar não trava
        if r.status_code >= 400:
            return RedirectResponse(url)

        def generate():
            for chunk in r.iter_content(CHUNK_SIZE):
                if chunk:
                    yield chunk

        return StreamingResponse(
            generate(),
            headers={
                "Content-Type": r.headers.get("Content-Type", "video/mp4"),
                "Accept-Ranges": "bytes",
                "Access-Control-Allow-Origin": "*",
                "Cache-Control": "no-cache"
            }
        )

    except Exception as e:
        log(str(e), title, url)
        return RedirectResponse(url)

# =========================
# ROTA PRINCIPAL
# =========================

@app.get("/buscar")
def buscar(request: Request):

    titulo = request.query_params.get("titulo")

    if not titulo:
        return {"erro": "vazio"}

    filme = buscar_filme(titulo)

    if not filme:
        return {"erro": "não encontrado"}

    _id, nome, url = filme

    return stream(url, nome, request)

# =========================
# START SAFE (KOYEB)
# =========================

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app:app", host="0.0.0.0", port=port)
