from flask import Flask, request, Response, stream_with_context, redirect
import requests
import sqlite3
import os
import re
import unicodedata
import random
import datetime

app = Flask(__name__)

# =========================
# CONFIG
# =========================

DB_PATH = "filmes.db"
LOG_FILE = "logs_erros.txt"

CHUNK_SIZE = 1024 * 256
TIMEOUT = (8, 300)

# =========================
# AGENTES IPTV / CHROME
# =========================

AGENTES = [
    "EPPIPROPLAYER/1.0.8",
    "OTT Navigator",
    "VLC/3.0.20",
    "ExoPlayerLib/2.19.1",
    "Dalvik/2.1.0",
    "Mozilla/5.0 (Android 14) Chrome/120 Mobile"
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
# LIMPEZA
# =========================

def limpar(txt):
    txt = ''.join(c for c in unicodedata.normalize('NFD', str(txt))
                  if unicodedata.category(c) != 'Mn')
    txt = re.sub(r'[^a-zA-Z0-9\s]', ' ', txt)
    txt = re.sub(r'\s+', ' ', txt)
    return txt.strip().lower()

# =========================
# CRIA DB AUTOMÁTICO
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
# ROBÔ: ORGANIZAR TXT -> DB
# =========================

def importar_txt_para_db(txt_file):
    if not os.path.exists(txt_file):
        return

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    with open(txt_file, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            if "|" in line:
                nome, url = line.split("|", 1)
                nome_limpo = limpar(nome)

                c.execute("""
                    INSERT INTO filmes (nome, nome_busca, url)
                    VALUES (?, ?, ?)
                """, (nome.strip(), nome_limpo, url.strip()))

    conn.commit()
    conn.close()

# =========================
# BUSCA (SEMPRE POR ID REAL)
# =========================

def buscar_filme(titulo):
    titulo = limpar(titulo)

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 🔥 exato primeiro
    c.execute("SELECT id, nome, url FROM filmes WHERE nome_busca = ? LIMIT 1", (titulo,))
    res = c.fetchone()

    if res:
        conn.close()
        return res

    # 🔥 fallback seguro (sem confundir franquia)
    c.execute("SELECT id, nome, url FROM filmes WHERE nome_busca LIKE ? LIMIT 5", (f"{titulo}%",))
    res = c.fetchall()

    conn.close()

    if res:
        return res[0]

    return None

# =========================
# STREAM ROBUSTO (ANTI-CRASH CHROME)
# =========================

def stream(url, title):

    try:
        agent = random.choice(AGENTES)

        headers = {
            "User-Agent": agent,
            "Accept": "*/*",
            "Connection": "keep-alive",
            "Accept-Encoding": "identity",
            "Referer": url
        }

        range_header = request.headers.get("Range")
        if range_header:
            headers["Range"] = range_header

        r = requests.get(
            url,
            headers=headers,
            stream=True,
            timeout=TIMEOUT,
            allow_redirects=True
        )

        if r.status_code >= 400:
            log("HTTP ERROR", title, url)
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
                "Cache-Control": "no-cache"
            }
        )

    except Exception as e:
        log(str(e), title, url)
        return redirect(url)

# =========================
# SEARCH (RETORNA LISTA ORGANIZADA)
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
# IMPORT AUTOMÁTICO EXEMPLO
# =========================

@app.route("/importar")
def importar():
    importar_txt_para_db("filmes_site.txt")
    return "OK importado"

# =========================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
