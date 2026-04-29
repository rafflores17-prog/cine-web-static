from flask import Flask, request, Response, stream_with_context, redirect
import requests
import sqlite3
import random
import os
import unicodedata
import re

app = Flask(__name__)
DB_PATH = "filmes.db"
CHUNK_SIZE = 1024 * 256 

AGENTES = [
    "VLC/3.0.20 LibVLC/3.0.20",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "okhttp/4.12.0"
]

# Função que deixa apenas LETRAS (Mata o erro do ano e pontos)
def extrair_letras(txt):
    if not txt: return ""
    txt = ''.join(c for c in unicodedata.normalize('NFD', str(txt)) if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z]', '', txt.lower())

def executar_proxy(url_video):
    headers = {"User-Agent": random.choice(AGENTES), "Connection": "keep-alive"}
    range_header = request.headers.get("Range")
    if range_header: headers["Range"] = range_header

    try:
        r = requests.get(url_video, headers=headers, stream=True, timeout=(15, 300), allow_redirects=True)
        def generate():
            for chunk in r.iter_content(chunk_size=CHUNK_SIZE):
                if chunk: yield chunk
        resp = Response(stream_with_context(generate()), status=r.status_code)
        resp.headers["Content-Type"] = "video/mp4"
        resp.headers["Accept-Ranges"] = "bytes"
        resp.headers["Access-Control-Allow-Origin"] = "*"
        return resp
    except:
        return redirect(url_video)

@app.route("/buscar")
def buscar():
    titulo = request.args.get("titulo")
    if not titulo: return "Vazio", 400

    alvo = extrair_letras(titulo)
    print(f"🔎 Rastreando: {alvo}")

    if os.path.exists(DB_PATH):
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT url, nome FROM filmes")
            todos = c.fetchall()
            conn.close()

            for row in todos:
                url_db, nome_db = row
                # Se o que o site pede está no banco ou vice-versa (só letras!)
                if alvo in extrair_letras(nome_db) or extrair_letras(nome_db) in alvo:
                    return executar_proxy(url_db)
        except: pass

    # Backup VIP.txt
    if os.path.exists("vips.txt"):
        with open("vips.txt", "r", encoding="utf-8", errors="ignore") as f:
            for linha in f:
                if "|" in linha:
                    nome_vip, url_vip = linha.split("|", 1)
                    if alvo in extrair_letras(nome_vip) or extrair_letras(nome_vip) in alvo:
                        return executar_proxy(url_vip.strip())

    return "Nao encontrado", 404

@app.route("/")
def index(): return "🚀 Motor v22 - Limpo e Operacional"

if __name__ == "__main__":
    # O segredo para o Koyeb rodar sem comando manual é ler a porta do sistema
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
