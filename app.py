# ==========================================
# MOTOR CINE MEGA PRO - MODO FUTURO (ASYNC)
# Com Health Check integrado para a Koyeb
# Desenvolvido por: @ApkBugado
# ==========================================

from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse
import httpx
import sqlite3
import random
import os
import unicodedata
import re
import datetime
import uvicorn
import asyncio

app = FastAPI(title="Motor Cine Mega - API Async")

# =========================
# CONFIGURAÇÕES PREMIUM
# =========================

LOG_FILE = "logs_erros.txt"
TIMEOUT_CONNECT = 8.0
TIMEOUT_READ = 300.0
CHUNK_SIZE = 1024 * 256

# =========================
# AGENTES "PLAYER REAL"
# =========================

AGENTES = [
    "EPPIPROPLAYER/1.0.8 (Linux;Android 14) AndroidXMedia3/1.5.1",
    "PurplePlayer/1.2.82",
    "OTT Navigator/1.6.5",
    "Kodi/20.3 (Linux; Android 14)",
    "VLC/3.0.20 LibVLC/3.0.20",
    "ExoPlayerLib/2.19.1",
    "Dalvik/2.1.0 (Linux; U; Android 14; Mobile)",
    "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Mobile Safari/537.36",
    "okhttp/4.12.0"
]

# =========================
# FUNÇÕES DE SUPORTE
# =========================

def registrar_log(titulo, url, erro):
    try:
        now = datetime.datetime.now()
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"\n{now}\n{titulo}\n{url}\n{erro}\n-------------------\n")
    except:
        pass

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
# CARREGAMENTO DE DADOS (TXT E DB)
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

print("[+] Inicializando Sistema @ApkBugado...")
VIP_CACHE = carregar_txt("vips.txt")
SITE_CACHE = carregar_txt("filmes_site.txt")
print("[+] Listas Carregadas com Sucesso.")

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

def buscar_db(titulo_limpo):
    try:
        if not os.path.exists("filmes.db"):
            return None
        conn = sqlite3.connect("filmes.db")
        c = conn.cursor()
        c.execute("SELECT url FROM filmes WHERE nome_busca = ? LIMIT 1", (titulo_limpo,))
        res = c.fetchone()
        conn.close()
        return res[0] if res else None
    except:
        return None

# =========================
# 🔥 MOTOR ASYNC DE STREAMING
# =========================

async def executar_proxy_async(url_video: str, titulo: str, request: Request):
    ua_cliente = request.headers.get("User-Agent", "")
    if any(player in ua_cliente for player in ["VLC", "ExoPlayer", "Player", "Kodi"]):
        agente = ua_cliente
    else:
        agente = random.choice(AGENTES)

    range_header = request.headers.get("Range")

    req_headers = {
        "User-Agent": agente,
        "Accept": "*/*",
        "Connection": "keep-alive",
        "Referer": url_video,
        "Origin": "/".join(url_video.split("/")[:3])
    }

    if range_header:
        req_headers["Range"] = range_header

    try:
        client = httpx.AsyncClient(timeout=httpx.Timeout(TIMEOUT_CONNECT, read=TIMEOUT_READ))
        req = client.build_request("GET", url_video, headers=req_headers)
        
        response = await client.send(req, stream=True, follow_redirects=True)
        status = response.status_code

        if status not in (200, 206):
            registrar_log(titulo, url_video, f"HTTP {status}")
            await response.aclose()
            await client.aclose()
            return Response(content="Erro na fonte", status_code=status)

        headers_resp = {
            "Content-Type": response.headers.get("Content-Type", "video/mp4"),
            "Accept-Ranges": "bytes",
            "Access-Control-Allow-Origin": "*",
            "Cache-Control": "no-cache",
        }

        if "Content-Range" in response.headers:
            headers_resp["Content-Range"] = response.headers["Content-Range"]
        if "Content-Length" in response.headers:
            headers_resp["Content-Length"] = response.headers["Content-Length"]

        async def stream_generator():
            try:
                async for chunk in response.aiter_bytes(chunk_size=CHUNK_SIZE):
                    if chunk:
                        yield chunk
            except asyncio.CancelledError:
                pass
            except Exception:
                pass
            finally:
                await response.aclose()
                await client.aclose()

        return StreamingResponse(
            stream_generator(),
            status_code=status,
            headers=headers_resp
        )

    except Exception as e:
        registrar_log(titulo, url_video, str(e))
        return Response(content="Falha de Conexão Crítica", status_code=500)

# =========================
# HEALTH CHECK PARA A KOYEB (A ROTA VERDE)
# =========================
@app.get("/")
async def raiz():
    return {"status": "online", "motor": "Cine Mega Pro Async", "by": "@ApkBugado"}

# =========================
# ROTA PRINCIPAL DE BUSCA
# =========================

@app.get("/buscar")
async def buscar(request: Request):
    titulo = request.query_params.get("titulo")

    if not titulo:
        return Response(content="Título vazio", status_code=400)

    t = limpar_texto(titulo)

    fontes = [
        buscar_txt(t, VIP_CACHE),
        buscar_db(t),
        buscar_txt(t, SITE_CACHE)
    ]

    for url in fontes:
        if url:
            return await executar_proxy_async(url, titulo, request)

    registrar_log(titulo, "Nenhuma fonte", "Não encontrado")
    return Response(content="Filme não encontrado", status_code=404)

# =========================
# INICIALIZADOR
# =========================

if __name__ == "__main__":
    porta = int(os.environ.get("PORT", 8000))
    uvicorn.run("app:app", host="0.0.0.0", port=porta, workers=2)
