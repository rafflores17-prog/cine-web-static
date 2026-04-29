from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse, RedirectResponse
import httpx
import sqlite3
import random
import os
import unicodedata
import re
from datetime import datetime

app = FastAPI()

DB_PATH = "filmes.db"
AGENTES = [
    "VLC/3.0.20",
    "Mozilla/5.0 (Linux; Android 14) Chrome/120 Mobile"
]

# =========================
# LIMPEZA E BUSCA (RESOLVE JUMANJI)
# =========================
def limpar(txt):
    if not txt: return ""
    txt = ''.join(c for c in unicodedata.normalize('NFD', str(txt)) if unicodedata.category(c) != 'Mn')
    return re.sub(r'\s+', ' ', re.sub(r'[^a-zA-Z0-9\s]', ' ', txt)).strip().lower()

def buscar_filme(titulo):
    t = limpar(titulo)
    if not os.path.exists(DB_PATH): return None
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # BUSCA INTELIGENTE: Tenta o nome exato primeiro para não vir filme errado
    c.execute("SELECT nome, url FROM filmes WHERE nome_busca = ? LIMIT 1", (t,))
    res = c.fetchone()
    
    if not res:
        # Se não achou exato, pega o que começa com o nome (evita lixo do meio)
        c.execute("SELECT nome, url FROM filmes WHERE nome_busca LIKE ? LIMIT 1", (f"{t}%",))
        res = c.fetchone()
    
    conn.close()
    return res

# =========================
# MOTOR DE STREAM (ANTI-CRASH CHROME)
# =========================
async def stream_video(url, request: Request):
    headers = {
        "User-Agent": random.choice(AGENTES),
        "Range": request.headers.get("Range", "bytes=0-")
    }
    
    # httpx é assíncrono, não trava o Koyeb!
    client = httpx.AsyncClient(timeout=15.0)
    try:
        # Usamos stream para não carregar o filme na RAM do servidor
        req = client.build_request("GET", url, headers=headers)
        r = await client.send(req, stream=True)

        if r.status_code >= 400:
            return RedirectResponse(url)

        return StreamingResponse(
            r.aiter_bytes(chunk_size=1024*256),
            status_code=r.status_code,
            headers={
                "Content-Type": r.headers.get("Content-Type", "video/mp4"),
                "Accept-Ranges": "bytes",
                "Access-Control-Allow-Origin": "*"
            }
        )
    except:
        return RedirectResponse(url)

# =========================
# ROTAS
# =========================
@app.get("/")
def health():
    return {"status": "ok", "time": str(datetime.now())}

@app.get("/buscar")
async def buscar(titulo: str, request: Request):
    if not titulo: return {"erro": "vazio"}
    
    filme = buscar_filme(titulo)
    if not filme: return {"erro": "não encontrado"}
    
    nome, url = filme
    return await stream_video(url, request)

# Inicia o DB se não existir
if not os.path.exists(DB_PATH):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("CREATE TABLE IF NOT EXISTS filmes (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, nome_busca TEXT, url TEXT)")
    conn.close()
