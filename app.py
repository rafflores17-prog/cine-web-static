from flask import Flask, request, Response, stream_with_context, redirect, jsonify
import requests
import sqlite3
import os
import re
import unicodedata
import random

app = Flask(__name__)

DB_PATH = "filmes.db"

# =========================
# BUSCA PRECISA (ID ÚNICO)
# =========================

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row # Isso ajuda a pegar pelo nome da coluna
    return conn

@app.route("/pesquisar")
def pesquisar():
    query = request.args.get("q")
    if not query: return jsonify([])

    termo = limpar(query)
    conn = get_db()
    
    # Busca inteligente: Prioriza o que começa com o nome, depois o que contém
    cursor = conn.execute("""
        SELECT id, nome FROM filmes 
        WHERE nome_busca LIKE ? 
        ORDER BY (nome_busca = ?) DESC, nome_busca ASC LIMIT 10
    """, (f"%{termo}%", termo))
    
    resultados = [{"id": r["id"], "nome": r["nome"]} for r in cursor.fetchall()]
    conn.close()
    return jsonify(resultados)

# =========================
# PLAY POR ID (O PULO DO GATO)
# =========================

@app.route("/assistir/<int:filme_id>")
def assistir(filme_id):
    conn = get_db()
    res = conn.execute("SELECT nome, url FROM filmes WHERE id = ?", (filme_id,)).fetchone()
    conn.close()

    if not res:
        return "Filme não encontrado no banco", 404

    return stream(res["url"], res["nome"])

# =========================
# STREAMING SEM TRAVAMENTO
# =========================

def stream(url, title):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
            "Accept-Encoding": "identity",
            "Range": request.headers.get("Range", "bytes=0-")
        }

        r = requests.get(url, headers=headers, stream=True, timeout=15)

        # Se o IPTV bloquear o servidor, faz o redirect direto (fallback)
        if r.status_code >= 400:
            return redirect(url)

        def generate():
            for chunk in r.iter_content(chunk_size=1024*512):
                yield chunk

        return Response(
            stream_with_context(generate()),
            status=r.status_code,
            content_type=r.headers.get("Content-Type", "video/mp4"),
            headers={
                "Accept-Ranges": "bytes",
                "Access-Control-Allow-Origin": "*"
            }
        )
    except:
        return redirect(url)

def limpar(txt):
    txt = ''.join(c for c in unicodedata.normalize('NFD', str(txt)) if unicodedata.category(c) != 'Mn')
    return re.sub(r'\s+', ' ', re.sub(r'[^a-zA-Z0-9\s]', ' ', txt)).strip().lower()

if __name__ == "__main__":
    # Garante que o DB existe antes de rodar
    init_conn = sqlite3.connect(DB_PATH)
    init_conn.execute("CREATE TABLE IF NOT EXISTS filmes (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, nome_busca TEXT, url TEXT)")
    init_conn.close()
    
    app.run(host="0.0.0.0", port=8000)
