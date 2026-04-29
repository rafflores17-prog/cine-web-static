from flask import Flask, request, Response, stream_with_context, redirect, jsonify
import requests
import sqlite3
import os
import re
import unicodedata
import random

app = Flask(__name__)
DB_PATH = "filmes.db"
# Chunk de 512KB é o ponto ideal para o Archive.org não travar
CHUNK_SIZE = 1024 * 512 

API_PRIO = {"host": "http://serv99.xyz:8880", "user": "261491762", "pass": "2516895925"}

AGENTES = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "VLC/3.0.20 LibVLC/3.0.20",
    "okhttp/4.12.0"
]

def limpar(txt):
    if not txt: return ""
    txt = ''.join(c for c in unicodedata.normalize('NFD', str(txt)) if unicodedata.category(c) != 'Mn')
    # Remove TUDO que não for letra ou número para a busca ser idêntica
    txt = re.sub(r'[^a-zA-Z0-9]', '', txt)
    return txt.strip().lower()

def executar_proxy(url_video):
    # Se for Archive.org, o redirect às vezes é melhor que o proxy se a internet for lenta
    # Mas vamos manter o proxy com suporte total a Range para o Chrome não crashar
    headers = {
        "User-Agent": random.choice(AGENTES),
        "Connection": "keep-alive",
        "Accept-Encoding": "identity"
    }
    
    range_header = request.headers.get("Range")
    if range_header: headers["Range"] = range_header

    try:
        r = requests.get(url_video, headers=headers, stream=True, timeout=(15, 300), allow_redirects=True)
        
        if request.method == 'HEAD':
            return Response(status=r.status_code, headers={"Accept-Ranges": "bytes", "Content-Type": "video/mp4"})

        def generate():
            for chunk in r.iter_content(chunk_size=CHUNK_SIZE):
                if chunk: yield chunk

        resp = Response(stream_with_context(generate()), status=r.status_code)
        resp.headers["Content-Type"] = "video/mp4"
        resp.headers["Accept-Ranges"] = "bytes"
        resp.headers["Access-Control-Allow-Origin"] = "*"
        
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
    print(f"🔍 Buscando: {t_limpo}")
    
    # 1. Busca nos Arquivos TXT (vips.txt e filmes_site.txt)
    # AJUSTE MESTRE: Agora ele ignora espaços extras no arquivo
    for arq in ["vips.txt", "filmes_site.txt"]:
        if os.path.exists(arq):
            with open(arq, "r", encoding="utf-8", errors="ignore") as f:
                for linha in f:
                    if "|" in linha:
                        partes = linha.split("|")
                        nome_txt = limpar(partes[0])
                        url_txt = partes[1].strip()
                        # Se o que você digitou contém no nome do arquivo ou vice-versa
                        if t_limpo in nome_txt or nome_txt in t_limpo:
                            return executar_proxy(url_txt)

    # 2. API IPTV (serv99)
    try:
        url_api = f"{API_PRIO['host']}/player_api.php?username={API_PRIO['user']}&password={API_PRIO['pass']}&action=get_vod_streams"
        res_api = requests.get(url_api, timeout=7).json()
        for item in res_api:
            nome_api = limpar(item.get('name', ''))
            if t_limpo in nome_api or nome_api in t_limpo:
                v_url = f"{API_PRIO['host']}/movie/{API_PRIO['user']}/{API_PRIO['pass']}/{item.get('stream_id')}.mp4"
                return executar_proxy(v_url)
    except: pass

    return "Não encontrado", 404

@app.route("/")
def index(): return "🚀 Cine Mega v15 - Archive.org Fix"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
