import os
import random
import requests
import unicodedata
import re
from flask import Flask, request, Response, stream_with_context, redirect

app = Flask(__name__)

FONTES = {
    "1": {"nome": "Servidor 99", "host": "http://serv99.xyz:8880", "user": "1764371", "pass": "2419902"},
    "2": {"nome": "NX Panel", "host": "http://nxpanelxr51.info", "user": "sandroalvares2", "pass": "T9er2T"}
}

def limpar_radical(txt):
    if not txt: return ""
    txt = re.sub(r'\(\d{4}\)', '', str(txt))
    txt = ''.join(c for c in unicodedata.normalize('NFD', txt) if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9]', '', txt.lower())

def executar_proxy(url_video):
    # ESTRATÉGIA DE FLUXO: Se o redirect falhou, vamos forçar o Proxy Leve
    # Isso engana o bloqueio de HTTPS do navegador
    headers = {
        "User-Agent": "VLC/3.0.4 LibVLC/3.0.4",
        "Range": request.headers.get("Range", "bytes=0-"),
        "Connection": "keep-alive"
    }
    try:
        r = requests.get(url_video, headers=headers, stream=True, timeout=(5, 300))
        def generate():
            try:
                for chunk in r.iter_content(chunk_size=1024*64):
                    if chunk: yield chunk
            except: pass
            finally: r.close()
        
        resp = Response(stream_with_context(generate()), status=r.status_code, content_type="video/mp4")
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["Content-Disposition"] = "inline"
        resp.headers["Accept-Ranges"] = "bytes"
        return resp
    except:
        return redirect(url_video)

@app.route("/play")
def play():
    titulo = request.args.get("titulo")
    fonte_id = request.args.get("fonte", "1")
    alvo = limpar_radical(titulo)
    srv = FONTES.get(fonte_id)
    
    if not srv: return "Fonte OFF", 404

    try:
        url_api = f"{srv['host']}/player_api.php?username={srv['user']}&password={srv['pass']}&action=get_vod_streams"
        dados = requests.get(url_api, timeout=4).json()
        
        for item in dados:
            nome_api = limpar_radical(item.get('name', ''))
            if alvo in nome_api or nome_api in alvo:
                v_url = f"{srv['host']}/movie/{srv['user']}/{srv['pass']}/{item.get('stream_id')}.mp4"
                # Forçamos o Proxy para o navegador aceitar o vídeo
                return executar_proxy(v_url)
    except: pass
    return "Nao achou", 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, threaded=True)
