from flask import Flask, request, Response, stream_with_context, redirect
import requests
import sqlite3
import random
import os
import unicodedata
import re
import datetime

app = Flask(__name__)

# =========================
# CONFIG
# =========================

DB_PATH = "filmes.db"
LOG_FILE = "logs_erros.txt"

TIMEOUT_CONNECT = 5
TIMEOUT_READ = 120
CHUNK_SIZE = 1024 * 256

# =========================
# AGENTES (CHROME + IPTV)
# =========================

AGENTES = [
    "EPPIPROPLAYER/1.0.8",
    "OTT Navigator",
    "VLC/3.0.20",
    "ExoPlayerLib/2.19.1",
    "Dalvik/2.1.0",
    "Mozilla/5.0 (Linux; Android 14) Chrome/120 Mobile"
]

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

    txt = ''.join(c for c in unicodedata.normalize('NFD', str(txt))
                  if unicodedata.category(c) != 'Mn')

    txt = re.sub(r'[^a-zA-Z0-9\s]', ' ', txt)
    txt = re.sub(r'\s+', ' ', txt)

    return txt.strip().lower()

# =========================
# INIT DB
# =========================

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS filmes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT,
        nome_busca TEXT,
        url TEXT
    )
    """)

    conn.commit()
    conn.close()

init_db()

# =========================
# BUSCA SIMPLES (SEM VARREDURA PESADA)
# =========================

def buscar_filme(titulo):
    t = limpar(titulo)

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 🔥 EXATO PRIMEIRO
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

    # 🔥 fallback leve (LIMITADO)
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
# STREAM DIRETO (SEM LOOP, SEM PENDENTE)
# =========================

def stream(url, title):

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

        # 🔥 se falhar, NÃO trava request
        if r.status_code >= 400:
            return redirect(url)

        status = 206 if range_header else 200

        def generate():
            for chunk in r.iter_content(CHUNK_SIZE):
                if chunk:
                    yield chunk

        return Response(
            stream_with_context(generate()),
            status=status,
            headers={
                "Content-Type": r.headers.get("Content-Type", "video/mp4"),
                "Accept-Ranges": "bytes",
                "Access-Control-Allow-Origin": "*",
                "Cache-Control": "no-cache",
                "Connection": "keep-alive"
            }
        )

    except Exception as e:
        log(str(e), title, url)
        return redirect(url)

# =========================
# ROTA PRINCIPAL (SEM PENDÊNCIA)
# =========================

@app.route("/buscar")
def buscar():

    titulo = request.args.get("titulo")

    if not titulo:
        return "vazio", 400

    filme = buscar_filme(titulo)

    if not filme:
        return "não encontrado", 404

    _id, nome, url = filme

    return stream(url, nome)

# =========================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
