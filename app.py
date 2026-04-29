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
# CONFIG PREMIUM
# =========================

LOG_FILE = "logs_erros.txt"

TIMEOUT_CONNECT = 8
TIMEOUT_READ = 300

CHUNK_SIZE = 1024 * 256

# =========================
# CACHE SIMPLES (ANTI-REPETIÇÃO)
# =========================

CACHE_STREAM = {}

# =========================
# AGENTES "PLAYER REAL"
# =========================

AGENTES = [
    # IPTV REAL
    "EPPIPROPLAYER/1.0.8 (Linux;Android 14) AndroidXMedia3/1.5.1",
    "PurplePlayer/1.2.82",
    "OTT Navigator/1.6.5",
    "Kodi/20.3 (Linux; Android 14)",

    # PLAYER PROFISSIONAL
    "VLC/3.0.20 LibVLC/3.0.20",
    "ExoPlayerLib/2.19.1",

    # ANDROID REAL
    "Dalvik/2.1.0 (Linux; U; Android 14; Mobile)",

    # CHROME (IMPORTANTE)
    "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Mobile Safari/537.36",

    # BACKUP HTTP
    "okhttp/4.12.0"
]

# =========================
# LOG
# =========================

def registrar_log(titulo, url, erro):
    try:
        now = datetime.datetime.now()
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"\n{now}\n{titulo}\n{url}\n{erro}\n-------------------\n")
    except:
        pass

# =========================
# LIMPEZA
# =========================

def limpar_texto(texto):
    if not texto:
        return ""

    texto = ''.join(
        c for c in unicodedata.normalize('NFD', str(texto))
        if unicodedata.category(c) != 'Mn'
    )

    texto = re.sub(r'[^a-zA-Z0-9\s]', ' ', texto)
    texto = re.sub(r'\s+', ' ', texto)

    return texto.strip().lower()

# =========================
# SIMILARIDADE (MELHORADA)
# =========================

def similaridade(a, b):

    a_set = set(a.split())
    b_set = set(b.split())

    if not a_set or not b_set:
        return 0

    inter = a_set.intersection(b_set)

    score = len(inter) / max(len(a_set), len(b_set))

    if any(c.isdigit() for c in a) != any(c.isdigit() for c in b):
        score *= 0.6

    return score

# =========================
# TXT
# =========================

def ler_txt(caminho):
    acervo = {}

    try:
        with open(caminho, "r", encoding="utf-8") as f:
            for linha in f:
                if "|" in linha:
                    nome, url = linha.split("|", 1)
                    acervo[limpar_texto(nome)] = url.strip()
    except:
        pass

    return acervo


def carregar_txt(nome):
    for arq in [nome, nome.lower(), nome.upper()]:
        if os.path.exists(arq):
            return ler_txt(arq)
    return {}

print("Carregando listas...")

VIP_CACHE = carregar_txt("vips.txt")
SITE_CACHE = carregar_txt("filmes_site.txt")

print("OK")

# =========================
# BUSCA INTELIGENTE
# =========================

def buscar_txt(titulo_limpo, acervo):

    if titulo_limpo in acervo:
        return acervo[titulo_limpo]

    best = None
    best_score = 0

    for nome, url in acervo.items():
        score = similaridade(titulo_limpo, nome)

        if score > best_score:
            best_score = score
            best = url

    if best_score >= 0.6:
        return best

    return None

# =========================
# DB
# =========================

def buscar_db(titulo_limpo):
    try:
        if not os.path.exists("filmes.db"):
            return None

        conn = sqlite3.connect("filmes.db")
        c = conn.cursor()

        c.execute(
            "SELECT url FROM filmes WHERE nome_busca = ? LIMIT 1",
            (titulo_limpo,)
        )

        res = c.fetchone()
        conn.close()

        return res[0] if res else None

    except:
        return None

# =========================
# 🔥 MOTOR NETFLIX PRO LITE (CORRIGIDO)
# =========================

def executar_proxy(url_video, titulo):

    try:
        # 🔥 CACHE (evita travar em requests repetidos)
        if url_video in CACHE_STREAM:
            return redirect(url_video)

        # Detecta se é um player externo para repassar o User-Agent real
        ua_cliente = request.headers.get("User-Agent", "")
        if any(player in ua_cliente for player in ["VLC", "ExoPlayer", "Player", "Kodi"]):
            agente = ua_cliente
        else:
            agente = random.choice(AGENTES)

        range_header = request.headers.get("Range")

        headers = {
            "User-Agent": agente,
            "Accept": "*/*",
            "Connection": "keep-alive",
            "Referer": url_video,
            "Origin": "/".join(url_video.split("/")[:3])
        }

        if range_header:
            headers["Range"] = range_header

        r = requests.get(
            url_video,
            headers=headers,
            stream=True,
            timeout=(TIMEOUT_CONNECT, TIMEOUT_READ),
            allow_redirects=True
        )

        # Removemos a conversão forçada de 200 para 206 que causava erro no Chrome
        status = r.status_code

        if status not in (200, 206):
            registrar_log(titulo, url_video, f"HTTP {status}")
            return redirect(url_video)

        headers_resp = {
            "Content-Type": r.headers.get("Content-Type", "video/mp4"),
            "Accept-Ranges": "bytes",
            "Access-Control-Allow-Origin": "*",
            "Cache-Control": "no-cache",
        }

        if "Content-Range" in r.headers:
            headers_resp["Content-Range"] = r.headers["Content-Range"]
        if "Content-Length" in r.headers:
            headers_resp["Content-Length"] = r.headers["Content-Length"]

        def generate():
            try:
                for chunk in r.iter_content(chunk_size=CHUNK_SIZE):
                    if chunk:
                        yield chunk
            except Exception:
                pass # Evita o registo de erro no log se o visualizador fechar o stream

        # Salva cache leve
        CACHE_STREAM[url_video] = True

        return Response(
            stream_with_context(generate()),
            status=status,
            headers=headers_resp,
            direct_passthrough=True # Garante a entrega nativa e sem estrangulamento
        )

    except Exception as e:
        registrar_log(titulo, url_video, str(e))
        return redirect(url_video)

# =========================
# BUSCA PRINCIPAL
# =========================

@app.route("/buscar")
def buscar():

    titulo = request.args.get("titulo")

    if not titulo:
        return "Título vazio", 400

    t = limpar_texto(titulo)

    fontes = [
        buscar_txt(t, VIP_CACHE),
        buscar_db(t),
        buscar_txt(t, SITE_CACHE)
    ]

    for url in fontes:
        if url:
            return executar_proxy(url, titulo)

    registrar_log(titulo, "nenhuma fonte", "não encontrado")

    return "Filme não encontrado", 404


# =========================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
