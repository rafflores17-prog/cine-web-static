from flask import Flask, request, Response, stream_with_context, redirect, jsonify
import requests
import sqlite3
import random
import os
import unicodedata
import re

app = Flask(__name__)
DB_PATH = "filmes.db"
# Chunk maior para dar "fôlego" no carregamento inicial
CHUNK_SIZE = 1024 * 1024 

API_PRIO = {"host": "http://serv99.xyz:8880", "user": "261491762", "pass": "2516895925"}

# Agentes que os servidores IPTV mais "respeitam"
AGENTES = [
    "VLC/3.0.20 LibVLC/3.0.20",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "okhttp/4.12.0"
]

def limpar(txt):
    if not txt: return ""
    txt = ''.join(c for c in unicodedata.normalize('NFD', str(txt)) if unicodedata.category(c) != 'Mn')
    return re.sub(r'\s+', ' ', re.sub(r'[^a-zA-Z0-9\s]', ' ', txt)).strip().lower()

def executar_proxy(url_video):
    # Força headers que fazem o player de HTML5/Android se sentir em casa
    headers = {
        "User-Agent": random.choice(AGENTES),
        "Connection": "keep-alive",
        "Accept-Encoding": "identity"
    }
    
    range_header = request.headers.get("Range")
    if range_header: headers["Range"] = range_header

    try:
        # stream=True é vital para não estourar a RAM do Koyeb
        r = requests.get(url_video, headers=headers, stream=True, timeout=(20, 600), allow_redirects=True)
        
        if request.method == 'HEAD':
            return Response(status=r.status_code, headers={"Accept-Ranges": "bytes", "Content-Type": "video/mp4"})

        def generate():
            for chunk in r.iter_content(chunk_size=CHUNK_SIZE):
                if chunk: yield chunk

        resp = Response(stream_with_context(generate()), status=r.status_code)
        resp.headers["Content-Type"] = "video/mp4"
        resp.headers["Accept-Ranges"] = "bytes"
        resp.headers["Access-Control-Allow-Origin"] = "*"
        
        # Repassa o tamanho real se o servidor IPTV informar
        if 'Content-Length' in r.headers: resp.headers['Content-Length'] = r.headers['Content-Length']
        if 'Content-Range' in r.headers: resp.headers['Content-Range'] = r.headers['Content-Range']
        
        return resp
    except:
        return redirect(url_video)

@app.route("/buscar", methods=['GET', 'HEAD'])
def buscar():
    titulo = request.args.get("titulo")
    if not titulo: return "Vazio", 400
    
    t_limpo = limpar(titulo)
    print(f"🔍 Mestre, buscando: {t_limpo}")
    
    # 1. Arquivos locais
    for arq in ["vips.txt", "filmes_site.txt"]:
        if os.path.exists(arq):
            with open(arq, "r", encoding="utf-8", errors="ignore") as f:
                for linha in f:
                    if "|" in linha:
                        nome, url = linha.split("|", 1)
                        if t_limpo in limpar(nome):
                            return executar_proxy(url.strip())

    # 2. API IPTV (serv99)
    try:
        url_api = f"{API_PRIO['host']}/player_api.php?username={API_PRIO['user']}&password={API_PRIO['pass']}&action=get_vod_streams"
        res_api = requests.get(url_api, timeout=8).json()
        for item in res_api:
            if t_limpo in limpar(item.get('name', '')):
                v_url = f"{API_PRIO['host']}/movie/{API_PRIO['user']}/{API_PRIO['pass']}/{item.get('stream_id')}.mp4"
                return executar_proxy(v_url)
    except: pass

    return "Não encontrado", 404

@app.route("/")
def index(): return "🚀 Cine Mega v14 Estável"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
