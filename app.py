from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse, RedirectResponse
import httpx
import sqlite3
import re
import unicodedata

app = FastAPI()
DB_PATH = "filmes.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# Cria a tabela ao iniciar sem depender de Flask
with sqlite3.connect(DB_PATH) as conn:
    conn.execute("CREATE TABLE IF NOT EXISTS filmes (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, nome_busca TEXT, url TEXT)")

def limpar(txt):
    txt = ''.join(c for c in unicodedata.normalize('NFD', str(txt)) if unicodedata.category(c) != 'Mn')
    return re.sub(r'\s+', ' ', re.sub(r'[^a-zA-Z0-9\s]', ' ', txt)).strip().lower()

@app.get("/pesquisar")
async def pesquisar(q: str = ""):
    if not q: return []
    termo = limpar(q)
    conn = get_db()
    cursor = conn.execute("""
        SELECT id, nome FROM filmes 
        WHERE nome_busca LIKE ? 
        ORDER BY (nome_busca = ?) DESC, (nome_busca LIKE ?) DESC, nome_busca ASC 
        LIMIT 15
    """, (f"%{termo}%", termo, f"{termo}%"))
    res = [{"id": r["id"], "nome": r["nome"]} for r in cursor.fetchall()]
    conn.close()
    return res

@app.get("/assistir/{filme_id}")
async def assistir(filme_id: int):
    conn = get_db()
    res = conn.execute("SELECT nome, url FROM filmes WHERE id = ?", (filme_id,)).fetchone()
    conn.close()
    if not res: return Response(content="Não encontrado", status_code=404)
    url = res["url"]
    async def stream_video():
        async with httpx.AsyncClient() as client:
            try:
                async with client.stream("GET", url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15) as r:
                    async for chunk in r.aiter_bytes(chunk_size=1024*512):
                        yield chunk
            except: pass
    return StreamingResponse(stream_video(), media_type="video/mp4")
