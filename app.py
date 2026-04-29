from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, RedirectResponse
import httpx
import sqlite3
import os
import unicodedata
import re
from contextlib import asynccontextmanager

DB_PATH = "filmes.db"

# GARANTE QUE O DB EXISTE ANTES DE TUDO
@asynccontextmanager
async def lifespan(app: FastAPI):
    if not os.path.exists(DB_PATH):
        conn = sqlite3.connect(DB_PATH)
        conn.execute("CREATE TABLE IF NOT EXISTS filmes (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, nome_busca TEXT, url TEXT)")
        conn.close()
    yield

app = FastAPI(lifespan=lifespan)

def limpar(txt):
    if not txt: return ""
    txt = ''.join(c for c in unicodedata.normalize('NFD', str(txt)) if unicodedata.category(c) != 'Mn')
    return re.sub(r'\s+', ' ', re.sub(r'[^a-zA-Z0-9\s]', ' ', txt)).strip().lower()

@app.get("/")
async def health():
    return {"status": "online", "msg": "Cine Mega Rodando"}

@app.get("/buscar")
async def buscar(titulo: str, request: Request):
    if not titulo: return {"erro": "vazio"}
    
    t = limpar(titulo)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Busca exata primeiro
    c.execute("SELECT url FROM filmes WHERE nome_busca = ? LIMIT 1", (t,))
    res = c.fetchone()
    if not res:
        # Busca aproximada
        c.execute("SELECT url FROM filmes WHERE nome_busca LIKE ? LIMIT 1", (f"{t}%",))
        res = c.fetchone()
    conn.close()

    if not res: return {"erro": "não encontrado"}
    
    url_iptv = res[0]
    
    # MOTOR DE STREAMING QUE NÃO TRAVA O KOYEB
    async def play():
        async with httpx.AsyncClient(follow_redirects=True, timeout=20.0) as client:
            try:
                async with client.stream("GET", url_iptv, headers={"User-Agent": "VLC/3.0.20"}) as r:
                    async for chunk in r.aiter_bytes(chunk_size=1024*256):
                        yield chunk
            except:
                yield b""

    return StreamingResponse(play(), media_type="video/mp4")
