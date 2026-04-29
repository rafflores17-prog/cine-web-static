import os
import random
import requests
import unicodedata
import re
from flask import Flask, request, Response, stream_with_context, redirect

app = Flask(__name__)

# --- APENAS OS DOIS SERVIDORES "QUERIDINHOS" ---
FONTES = {
    "1": {"nome": "Servidor 99", "host": "http://serv99.xyz:8880", "user": "1764371", "pass": "2419902"},
    "2": {"nome": "NX Panel", "host": "http://nxpanelxr51.info", "user": "sandroalvares2", "pass": "T9er2T"}
}

AGENTES_VIP = ["VLC/3.0.4 LibVLC/3.0.4", "okhttp/4.12.0", "EPPIPROPLAYER/1.0.8"]

def limpar(txt):
    if not txt: return ""
    txt = ''.join(c for c in unicodedata.normalize('NFD', str(txt)) if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9]', '', txt.lower())

def executar_proxy(url_video):
    # REDIRECT em portas 80 e 8880 para manter a CPU em 0%
    if any(x in url_video.lower() for x in [":80", ":8880", "archive", "storage"]):
        return redirect(url_video)

    headers = {"User-Agent": random.choice(AGENTES_VIP), "Range": request.headers.get("Range", "bytes=0-")}
    try:
        r = requests.get(url_video, headers=headers, stream=True, timeout=(3, 300))
        def generate():
            try:
                for chunk in r.iter_content(chunk_size=1024*32):
                    if chunk: yield chunk
            except: pass
            finally: r.close()
        return Response(stream_with_context(generate()), status=r.status_code, content_type="video/mp4")
    except:
        return redirect(url_video)

@app.route("/play")
def play():
    titulo = request.args.get("titulo")
    fonte_id = request.args.get("fonte", "1")
    alvo = limpar(titulo)
    srv = FONTES.get(fonte_id)
    
    if not srv: return "Fonte OFF", 404

    try:
        # Busca na API dos queridinhos
        url_api = f"{srv['host']}/player_api.php?username={srv['user']}&password={srv['pass']}&action=get_vod_streams"
        dados = requests.get(url_api, timeout=4).json()
        
        for item in dados:
            if alvo in limpar(item.get('name', '')):
                # Link final para VOD
                v_url = f"{srv['host']}/movie/{srv['user']}/{srv['pass']}/{item.get('stream_id')}.mp4"
                return executar_proxy(v_url)
    except: pass
    return "Nao encontrado", 404

@app.route("/")
def index():
    return "Cine Mega v44 - Queridinhos Ativos"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, threaded=True)
