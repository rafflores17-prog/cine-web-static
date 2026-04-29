from flask import Flask, request, Response, stream_with_context, redirect, jsonify
import requests
import sqlite3
import os
import re
import unicodedata

app = Flask(__name__)
DB_PATH = "filmes.db"

# Limpa o texto para busca (remove acentos e espaços extras)
def limpar(txt):
    if not txt: return ""
    txt = ''.join(c for c in unicodedata.normalize('NFD', str(txt)) if unicodedata.category(c) != 'Mn')
    return re.sub(r'\s+', ' ', re.sub(r'[^a-zA-Z0-9\s]', ' ', txt)).strip().lower()

@app.route("/")
def health():
    return "Motor Cine Mega Online 🚀"

# BUSCA INTELIGENTE: Prioriza o exato para não bugar o Jumanji
@app.route("/buscar")
def buscar():
    titulo = request.args.get("titulo")
    if not titulo: return jsonify({"erro": "vazio"}), 400
    
    t = limpar(titulo)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # 1. Tenta o nome EXATO primeiro
    c.execute("SELECT url, nome FROM filmes WHERE nome_busca = ? LIMIT 1", (t,))
    res = c.fetchone()
    
    # 2. Se não achou exato, tenta o aproximado (LIKE)
    if not res:
        c.execute("SELECT url, nome FROM filmes WHERE nome_busca LIKE ? LIMIT 1", (f"{t}%",))
        res = c.fetchone()
    
    conn.close()

    if not res: return jsonify({"erro": "não encontrado no banco"}), 404
    
    return stream(res["url"], res["nome"])

# MOTOR DE STREAMING (Anti-Crash)
def stream(url, title):
    try:
        headers = {
            "User-Agent": "VLC/3.0.20",
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
            headers={
                "Accept-Ranges": "bytes",
                "Access-Control-Allow-Origin": "*",
                "Cache-Control": "no-cache"
            }
        )
    except:
        return redirect(url)

if __name__ == "__main__":
    if not os.path.exists(DB_PATH):
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS filmes (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, nome_busca TEXT, url TEXT)")
    
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
