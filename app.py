from flask import Flask, request, Response, stream_with_context
import requests
import sqlite3
import os
import unicodedata
import re
import random
import datetime

app = Flask(__name__)

# =========================
# CONFIG
# =========================

DB_FILE = "filmes.db"
VIP_FILE = "vips.txt"
LOG_FILE = "logs_erros.txt"

TIMEOUT = (5, 60)
CHUNK_SIZE = 1024 * 64  # 🔥 seguro (64KB)

AGENTES = [
    "Mozilla/5.0",
    "okhttp/4.12.0",
    "VLC/3.0",
    "Dalvik/2.1.0"
]

# =========================
# LOG
# =========================

def log(titulo, url, erro):
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"\n{datetime.datetime.now()}\n{titulo}\n{url}\n{erro}\n")
    except:
        pass

# =========================
# NORMALIZAR TEXTO
# =========================

def normalizar(t):
    if not t:
        return ""

    t = ''.join(
        c for c in unicodedata.normalize("NFD", str(t))
        if unicodedata.category(c) != "Mn"
    )

    t = re.sub(r"[^a-zA-Z0-9\s]", " ", t)
    t = re.sub(r"\s+", " ", t)

    return t.strip().lower()

# =========================
# DB SEARCH (PRIORIDADE TOTAL)
# =========================

def buscar_db(nome):
    try:
        if not os.path.exists(DB_FILE):
            return None

        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()

        n = normalizar(nome)

        # 🔥 exato primeiro
        c.execute("""
            SELECT url FROM filmes
            WHERE nome_busca = ?
            LIMIT 1
        """, (n,))

        r = c.fetchone()

        if r:
            conn.close()
            return r[0]

        # 🔥 fallback LIKE
        c.execute("""
            SELECT url FROM filmes
            WHERE nome_busca LIKE ?
            LIMIT 1
        """, (f"%{n}%",))

        r = c.fetchone()

        conn.close()

        return r[0] if r else None

    except Exception as e:
        log(nome, "DB", str(e))
        return None

# =========================
# VIP TXT (SECUNDÁRIO)
# =========================

def buscar_vip(nome):
    try:
        if not os.path.exists(VIP_FILE):
            return None

        n = normalizar(nome)

        with open(VIP_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if "|" in line:
                    t, url = line.split("|", 1)
                    if normalizar(t) == n:
                        return url.strip()

    except Exception as e:
        log(nome, "VIP", str(e))

    return None

# =========================
# STREAM SEGURO (ANTI CRASH GUNICORN)
# =========================

def stream(url, titulo):
    try:
        headers = {
            "User-Agent": random.choice(AGENTES),
            "Connection": "keep-alive",
            "Accept": "*/*"
        }

        if "Range" in request.headers:
            headers["Range"] = request.headers["Range"]

        r = requests.get(
            url,
            headers=headers,
            stream=True,
            timeout=TIMEOUT,
            allow_redirects=True
        )

        if r.status_code >= 400:
            log(titulo, url, f"HTTP {r.status_code}")
            return ("erro stream", 502)

        def generate():
            try:
                for chunk in r.iter_content(CHUNK_SIZE):
                    if chunk:
                        yield chunk
            except Exception as e:
                log(titulo, url, str(e))

        return Response(
            stream_with_context(generate()),
            status=r.status_code,
            headers={
                "Content-Type": r.headers.get("Content-Type", "video/mp4"),
                "Accept-Ranges": "bytes",
                "Access-Control-Allow-Origin": "*",
                "Cache-Control": "no-cache"
            }
        )

    except Exception as e:
        log(titulo, url, str(e))
        return ("erro geral", 500)

# =========================
# ROTA PRINCIPAL
# =========================

@app.route("/buscar")
def buscar():

    titulo = request.args.get("titulo")

    if not titulo:
        return "sem titulo", 400

    print("BUSCANDO:", titulo)

    url = (
        buscar_db(titulo)
        or buscar_vip(titulo)
    )

    if not url:
        return "não encontrado", 404

    return stream(url, titulo)

# =========================

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8000))
    )
