from flask import Flask, request, Response, stream_with_context, redirect, jsonify
import requests
import sqlite3
import random
import os
import unicodedata
import re

app = Flask(__name__)

# =========================
# CONFIGURAÇÕES TÉCNICAS
# =========================
DB_PATH = "filmes.db"
# Aumentamos o CHUNK para o vídeo carregar mais rápido no app
CHUNK_SIZE = 1024 * 512 

API_PRIORITARIA = {"host": "http://serv99.xyz:8880", "user": "261491762", "pass": "2516895925"}
API_SECUNDARIA = {"host": "http://techon.one:80", "user": "003008", "pass": "440144634"}

AGENTES_VIP = [
    "VLC/3.0.20 LibVLC/3.0.20",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "EPPIPROPLAYER/1.0.8 (Linux;Android 14)",
    "okhttp/4.12.0"
]

def limpar(txt):
    if not txt: return ""
    txt = ''.join(c for c in unicodedata.normalize('NFD', str(txt)) if unicodedata.category(c) != 'Mn')
    return re.sub(r'\s+', ' ', re.sub(r'[^a-zA-Z0-9\s]', ' ', txt)).strip().lower()

# =========================
# PROXY CAMALEÃO V12 (CORRIGIDO)
# =========================
def executar_proxy(url_video):
    if "archive.org" in url_video.lower():
        return redirect(url_video)

    headers = {
        "User-Agent": random.choice(AGENTES_VIP),
        "Connection": "keep-alive",
        "Accept": "*/*"
    }
    
    range_header = request.headers.get("Range")
    if range_header:
        headers["Range"] = range_header

    try:
        # Timeout maior para evitar o erro de reprodução
        r = requests.get(url_video, headers=headers, stream=True, timeout=(15, 300), allow_redirects=True)
        
        def generate():
            for chunk in r.iter_content(chunk_size=CHUNK_SIZE):
                if chunk: yield chunk

        # Forçamos o header de vídeo para o player entender o arquivo
        resp = Response(stream_with_context(generate()), status=r.status_code)
        resp.headers["Content-Type"] = "video/mp4"
        resp.headers["Accept-Ranges"] = "bytes"
        resp.headers["Access-Control-Allow-Origin"] = "*"
        
        if 'Content-Range' in r.headers: resp.headers['Content-Range'] = r.headers['Content-Range']
        if 'Content-Length' in r.headers: resp.headers['Content-Length'] = r.headers['Content-Length']
        
        return resp
    except:
        # Se falhar o proxy, tenta o redirect como última chance
        return redirect(url_video)

# =========================
# BUSCA EM TUDO (TXT + DB + API)
# =========================
@app.route("/buscar")
def buscar():
    titulo = request.args.get("titulo")
    if not titulo: return "Vazio", 400
    
    t_limpo = limpar(titulo)
    
    # 1. Busca nos seus arquivos TXT (Prioridade Máxima)
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

    # 2. Busca nas APIs dos servidores serv99 e techon
    for api in [API_PRIORITARIA, API_SECUNDARIA]:
        try:
            url_api = f"{api['host']}/player_api.php?username={api['user']}&password={api['pass']}&action=get_vod_streams"
            # Limitamos a busca para não travar
            r = requests.get(url_api, timeout=6).json()
            for item in r:
                if t_limpo in limpar(item.get('name', '')):
                    v_url = f"{api['host']}/movie/{api['user']}/{api['pass']}/{item.get('stream_id')}.mp4"
                    return executar_proxy(v_url)
        except: continue

    return "Não encontrado", 404

@app.route("/")
def index(): return "🚀 Motor v12 - Online"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
