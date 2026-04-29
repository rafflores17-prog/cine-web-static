from flask import Flask, request, Response, stream_with_context, redirect
import requests
import sqlite3
import random
import os
import unicodedata
import re
import datetime
from difflib import SequenceMatcher

app = Flask(__name__)

# =========================
# CONFIG
# =========================

DB_PATH = "filmes.db"
VIP_FILE = "vips.txt"
LOG_FILE = "logs_erros.txt"

TIMEOUT = (10, 180)
CHUNK_SIZE = 1024 * 512

AGENTES = [
    "Mozilla/5.0 (Linux; Android 14) Chrome/120",
    "okhttp/4.12.0",
    "VLC/3.0.20",
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
# NORMALIZAÇÃO (CRÍTICO)
# =========================

def norm(t):
    if not t:
        return ""

    t = unicodedata.normalize("NFD", str(t))
    t = ''.join(c for c in t if unicodedata.category(c) != 'Mn')
    t = t.lower()

    t = re.sub(r'[^a-z0-9\s]', ' ', t)
    t = re.sub(r'\s+', ' ', t)

    return t.strip()

# =========================
# SIMILARIDADE INTELIGENTE
# =========================

def score(a, b):
    return SequenceMatcher(None, a, b).ratio()

# =========================
# VIP TXT
# =========================

def load_txt(file):
    data = {}
    if not os.path.exists(file):
        return data

    with open(file, "r", encoding="utf-8") as f:
        for line in f:
            if "|" in line:
                name, url = line.split("|", 1)
                data[norm(name)] = url.strip()

    return data

VIP = load_txt(VIP_FILE)

# =========================
# DB SEARCH (ROBUSTO)
# =========================

def buscar_db(title):
    if not os.path.exists(DB_PATH):
        return None

    t = norm(title)

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("SELECT nome, url FROM filmes")
    rows = c.fetchall()
    conn.close()

    best = None
    best_score = 0

    for nome, url in rows:
        n = norm(nome)
        s = score(t, n)

        if s > best_score:
            best_score = s
            best = url

    if best_score >= 0.65:
        return best

    return None

# =========================
# VIP SEARCH
# =========================

def buscar_vip(title):
    t = norm(title)

    if t in VIP:
        return VIP[t]

    best = None
    best_score = 0

    for k, v in VIP.items():
        s = score(t, k)
        if s > best_score:
            best_score = s
            best = v

    return best if best_score >= 0.7 else None

# =========================
# STREAM RESISTENTE
# =========================

def stream(url, title):
    try:
        headers = {
            "User-Agent": random.choice(AGENTES),
            "Accept": "*/*",
            "Connection": "keep-alive",
            "Accept-Encoding": "identity"
        }

        if "Range" in request.headers:
            headers["Range"] = request.headers["Range"]

        r = requests.get(url, headers=headers, stream=True, timeout=TIMEOUT)

        if r.status_code >= 400:
            return redirect(url)

        def gen():
            try:
                for chunk in r.iter_content(CHUNK_SIZE):
                    if chunk:
                        yield chunk
            except Exception as e:
                log(str(e), title, url)

        return Response(
            stream_with_context(gen()),
            status=r.status_code,
            headers={
                "Content-Type": r.headers.get("Content-Type", "video/mp4"),
                "Accept-Ranges": "bytes",
                "Access-Control-Allow-Origin": "*",
                "Cache-Control": "no-cache"
            }
        )

    except Exception as e:
        log(str(e), title, url)
        return redirect(url)

# =========================
# ROUTE
# =========================

@app.route("/buscar")
def buscar():
    titulo = request.args.get("titulo")

    if not titulo:
        return "sem titulo", 400

    # ordem REAL
    url = buscar_db(titulo) or buscar_vip(titulo)

    if not url:
        return "nao encontrado", 404

    return stream(url, titulo)

# =========================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
