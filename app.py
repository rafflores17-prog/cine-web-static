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

LOG_FILE = "logs_erros.txt"

TIMEOUT_CONNECT = 10
TIMEOUT_READ = 180

# 🔥 mais estável no Chrome
CHUNK_SIZE = 1024 * 128

# =========================
# AGENTES
# =========================

AGENTES = [
    "Mozilla/5.0",
    "okhttp/4.12.0",
    "VLC/3.0.4",
    "Dalvik/2.1.0"
]

# =========================
# LOG
# =========================

def registrar_log(titulo, url, erro):
    try:
        agora = datetime.datetime.now()
        linha = (
            f"\n{agora}\n"
            f"FILME: {titulo}\n"
            f"URL: {url}\n"
            f"ERRO: {erro}\n"
            "----------------------\n"
        )
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(linha)
    except:
        pass

# =========================
# LIMPAR TEXTO (CORRIGIDO)
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
# SIMILARIDADE MELHORADA
# =========================

def similaridade(a, b):

    a_words = set(a.split())
    b_words = set(b.split())

    if not a_words or not b_words:
        return 0

    inter = a_words.intersection(b_words)

    score = len(inter) / max(len(a_words), len(b_words))

    # 🔥 evita confundir sequências (1, 2, 3)
    if any(c.isdigit() for c in a) != any(c.isdigit() for c in b):
        score *= 0.6

    return score

# =========================
# CARREGAR TXT
# =========================

def ler_txt(caminho):
    acervo = {}

    try:
        with open(caminho, "r", encoding="utf-8") as f:
            for linha in f:
                if "|" in linha:
                    nome, url = linha.split("|", 1)
                    nome_limpo = limpar_texto(nome)
                    acervo[nome_limpo] = url.strip()
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

print("Listas carregadas.")

# =========================
# BUSCA INTELIGENTE
# =========================

def buscar_txt(titulo_limpo, acervo):

    # 1 - exato
    if titulo_limpo in acervo:
        return acervo[titulo_limpo]

    melhor_url = None
    melhor_score = 0

    for nome, url in acervo.items():

        score = similaridade(titulo_limpo, nome)

        if score > melhor_score:
            melhor_score = score
            melhor_url = url

    if melhor_score >= 0.6:
        return melhor_url

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

        if res:
            return res[0]

    except:
        pass

    return None

# =========================
# PROXY ESTÁVEL (CHROME FIX)
# =========================

def executar_proxy(url_video, titulo):

    try:

        agente = random.choice(AGENTES)

        headers = {

            "User-Agent": agente,

            "Accept": "video/mp4,video/*;q=0.9,*/*;q=0.8",

            "Connection": "keep-alive",

            "Accept-Encoding": "identity"

        }

        range_header = request.headers.get("Range")

        if range_header:
            headers["Range"] = range_header

        r = requests.get(
            url_video,
            headers=headers,
            stream=True,
            timeout=(TIMEOUT_CONNECT, TIMEOUT_READ),
            allow_redirects=True
        )

        # 🔥 fallback seguro
        if not r or r.status_code >= 400:
            registrar_log(titulo, url_video, f"HTTP {getattr(r,'status_code','NO')}")
            return redirect(url_video)

        content_type = r.headers.get("Content-Type", "video/mp4")

        if "video" not in content_type:
            content_type = "video/mp4"

        def generate():
            for chunk in r.iter_content(chunk_size=CHUNK_SIZE):
                if chunk:
                    yield chunk

        return Response(
            stream_with_context(generate()),
            headers={
                "Content-Type": content_type,
                "Accept-Ranges": "bytes",
                "Access-Control-Allow-Origin": "*",
                "Cache-Control": "no-cache",
                "Connection": "keep-alive"
            }
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

    titulo_limpo = limpar_texto(titulo)

    fontes = [

        buscar_txt(titulo_limpo, VIP_CACHE),
        buscar_db(titulo_limpo),
        buscar_txt(titulo_limpo, SITE_CACHE)

    ]

    for url in fontes:
        if url:
            return executar_proxy(url, titulo)

    registrar_log(titulo, "nenhuma fonte", "não encontrado")

    return "Filme não encontrado", 404

# =========================

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8000))
    )
