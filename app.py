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
# BUSCA INTELIGENTE (SEM ERRO DE JUMANJI)
# =========================

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.route("/pesquisar")
def pesquisar():
    query = request.args.get("q")
    if not query: return jsonify([])

    termo = limpar(query)
    conn = get_db()
    
    # BUSCA: Prioriza o nome EXATO, depois nomes que COMEÇAM com o que você digitou
    cursor = conn.execute("""
        SELECT id, nome FROM filmes 
        WHERE nome_busca LIKE ? 
        ORDER BY (nome_busca = ?) DESC, (nome_busca LIKE ?) DESC, nome_busca ASC 
        LIMIT 10
    """, (f"%{termo}%", termo, f"{termo}%"))
    
    resultados = [{"id": r["id"], "nome": r["nome"]} for r in cursor.fetchall()]
    conn.close()
    return jsonify(resultados)

# =========================
# PLAY POR ID (O CLIQUE CERTO)
# =========================

@app.route("/assistir/<int:filme_id>")
def assistir(filme_id):
    conn = get_db()
    res = conn.execute("SELECT nome, url FROM filmes WHERE id = ?", (filme_id,)).fetchone()
    conn.close()

    if not res:
        return "Filme não encontrado", 404

    return stream(res["url"], res["nome"])

# =========================
# STREAMING REFORMULADO
# =========================

def stream(url, title):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
            "Range": request.headers.get("Range", "bytes=0-")
        }

        r = requests.get(url, headers=headers, stream=True, timeout=15)

        if r.status_code >= 400:
            return redirect(url)

        def generate():
            for chunk in r.iter_content(chunk_size=1024*256):
                yield chunk

        return Response(
            stream_with_context(generate()),
            status=r.status_code,
            content_type=r.headers.get("Content-Type", "video/mp4"),
            headers={"Accept-Ranges": "bytes", "Access-Control-Allow-Origin": "*"}
        )
    except:
        return redirect(url)

def limpar(txt):
    txt = ''.join(c for c in unicodedata.normalize('NFD', str(txt)) if unicodedata.category(c) != 'Mn')
    return re.sub(r'\s+', ' ', re.sub(r'[^a-zA-Z0-9\s]', ' ', txt)).strip().lower()

if __name__ == "__main__":
    # Inicia o banco de dados Flask
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS filmes (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, nome_busca TEXT, url TEXT)")
    
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
