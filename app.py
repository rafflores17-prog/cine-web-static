from flask import Flask, request, Response, stream_with_context, redirect, jsonify
import requests
import sqlite3
import random
import os
import unicodedata
import re

app = Flask(__name__)

# =========================
# CONFIGURAÇÕES DE ELITE
# =========================
DB_PATH = "filmes.db"
CHUNK_SIZE = 1024 * 512 

API_PRIO = {"host": "http://serv99.xyz:8880", "user": "261491762", "pass": "2516895925"}

AGENTES = [
    "VLC/3.0.20 LibVLC/3.0.20",
    "EPPIPROPLAYER/1.0.8 (Linux;Android 14)",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
]

def limpar(txt):
    if not txt: return ""
    txt = ''.join(c for c in unicodedata.normalize('NFD', str(txt)) if unicodedata.category(c) != 'Mn')
    return re.sub(r'\s+', ' ', re.sub(r'[^a-zA-Z0-9\s]', ' ', txt)).strip().lower()

# =========================
# MOTOR DE STREAMING (RESOLVE O CRASH)
# =========================
def executar_proxy(url_video):
    # Se o link for YouTube ou lixo, a gente avisa no log
    if "youtube.com" in url_video or "youtu.be" in url_video:
        return "Link do YouTube detectado. O motor não processa links externos de redes sociais.", 403

    headers = {"User-Agent": random.choice(AGENTES), "Connection": "keep-alive"}
    range_header = request.headers.get("Range")
    if range_header: headers["Range"] = range_header

    try:
        # allow_redirects=True é o que faz ele seguir até o arquivo final .mp4 ou .ts
        r = requests.get(url_video, headers=headers, stream=True, timeout=(15, 300), allow_redirects=True)
        
        # Resolve o erro 405 (Method Not Allowed) para o site
        if request.method == 'HEAD':
            return Response(status=r.status_code, headers={"Accept-Ranges": "bytes"})

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

# =========================
# BUSCA (AGORA ACEITA HEAD E GET)
# =========================
@app.route("/buscar", methods=['GET', 'HEAD'])
def buscar():
    titulo = request.args.get("titulo")
    if not titulo: return "Vazio", 400
    
    t_limpo = limpar(titulo)
    print(f"🔍 Mestre, buscando: {t_limpo}")
    
    # 1. Busca nos Arquivos TXT
    for arq in ["vips.txt", "filmes_site.txt"]:
        if os.path.exists(arq):
            try:
                with open(arq, "r", encoding="utf-8", errors="ignore") as f:
                    for linha in f:
                        if "|" in linha:
                            nome, url = linha.split("|", 1)
                            if t_limpo in limpar(nome):
                                return executar_proxy(url.strip())
            except: pass

    # 2. Busca na API Prioritária (serv99)
    try:
        url_api = f"{API_PRIO['host']}/player_api.php?username={API_PRIO['user']}&password={API_PRIO['pass']}&action=get_vod_streams"
        r = requests.get(url_api, timeout=5).json()
        for item in r:
            if t_limpo in limpar(item.get('name', '')):
                v_url = f"{API_PRIO['host']}/movie/{API_PRIO['user']}/{API_PRIO['pass']}/{item.get('stream_id')}.mp4"
                return executar_proxy(v_url)
    except: pass

    return "Não encontrado", 404

@app.route("/")
def index(): return "🚀 Motor v13 Online"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
