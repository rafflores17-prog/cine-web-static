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
VIP_FILE = "vips.txt"
LOG_FILE = "logs_erros.txt"

TIMEOUT_CONNECT = 8
TIMEOUT_READ = 180
CHUNK_SIZE = 1024 * 256

# =========================
# AGENTES (CHROME + IPTV SAFE)
# =========================

AGENTES = [
    "Mozilla/5.0 (Linux; Android 14) Chrome/120 Mobile Safari/537.36",
    "okhttp/4.12.0",
    "VLC/3.0.20 LibVLC",
    "ExoPlayerLib/2.19.1",
    "Dalvik/2.1.0",
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
# LIMPAR TEXTO (PADRÃO CERTO)
# =========================

def limpar(txt):
    if not txt:
        return ""

    txt = ''.join(
        c for c in unicodedata.normalize('NFD', str(txt))
        if unicodedata.category(c) != 'Mn'
    )

    txt = txt.lower()

    # remove lixo comum IPTV
    lixo = [
        "dublado", "legendado", "dual", "hd", "fhd",
        "1080p", "720p", "4k", "blu-ray", "web-dl"
    ]

    for l in lixo:
        txt = txt.replace(l, "")

    txt = re.sub(r'[^a-z0-9\s]', ' ', txt)
    txt = re.sub(r'\s+', ' ', txt)

    return txt.strip()

# =========================
# DB INIT (OTIMIZADO)
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

    # 🔥 índice para busca rápida (IMPORTANTE)
    c.execute("CREATE INDEX IF NOT EXISTS idx_busca ON filmes(nome_busca)")

    conn.commit()
    conn.close()

init_db()

# =========================
# VIP CACHE
# =========================

def carregar_vip():
    acervo = {}

    if not os.path.exists(VIP_FILE):
        return acervo

    with open(VIP_FILE, "r", encoding="utf-8") as f:
        for linha in f:
            if "|" in linha:
                n, u = linha.split("|", 1)
                acervo[limpar(n)] = u.strip()

    return acervo

VIP_CACHE = carregar_vip()

# =========================
# BUSCA DB (PRIORIDADE ABSOLUTA)
# =========================

def buscar_db(t):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 1 - EXATO
    c.execute("""
        SELECT nome, url
        FROM filmes
        WHERE nome_busca = ?
        LIMIT 1
    """, (t,))

    r = c.fetchone()

    if r:
        conn.close()
        return r

    # 2 - fallback controlado (evita erro de sequência tipo 1 vs 2)
    c.execute("""
        SELECT nome, url
        FROM filmes
        WHERE nome_busca LIKE ?
        LIMIT 20
    """, (f"{t}%",))

    r = c.fetchone()
    conn.close()

    return r

# =========================
# VIP FALLBACK
# =========================

def buscar_vip(t):
    return VIP_CACHE.get(t)

# =========================
# STREAM (CHROME FIX + RANGE)
# =========================

def stream_video(url, titulo):

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

        if r.status_code >= 400:
            log("HTTP ERROR", titulo, url)
            return redirect(url)

        def generate():
            for chunk in r.iter_content(chunk_size=CHUNK_SIZE):
                if chunk:
                    yield chunk

        return Response(
            stream_with_context(generate()),
            headers={
                "Content-Type": r.headers.get("Content-Type", "video/mp4"),
                "Accept-Ranges": "bytes",
                "Access-Control-Allow-Origin": "*",
                "Cache-Control": "no-cache",
                "Connection": "keep-alive"
            }
        )

    except Exception as e:
        log(str(e), titulo, url)
        return redirect(url)

# =========================
# BUSCA PRINCIPAL
# =========================

@app.route("/buscar")
def buscar():

    titulo = request.args.get("titulo")
    if not titulo:
        return "vazio", 400

    t = limpar(titulo)

    # 🔥 1 DB PRIMEIRO
    db = buscar_db(t)
    if db:
        return stream_video(db[1], db[0])

    # 🔥 2 VIP SEGUNDO
    vip = buscar_vip(t)
    if vip:
        return stream_video(vip, titulo)

    # NÃO ENCONTROU
    log("NOT FOUND", titulo, "")
    return "Filme não encontrado", 404

# =========================

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8000))
    )
