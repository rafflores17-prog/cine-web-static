import os
import random
import requests
import unicodedata
import re
from flask import Flask, request, Response, stream_with_context, redirect

app = Flask(__name__)

# CONFIGURAÇÃO DE FONTES
FONTES = {
    "1": {"host": "http://newoneblue.site:80", "user": "58257413", "pass": "19193442"},
    "2": {"host": "http://9thgen.skin:80", "user": "11974034383", "pass": "eduardo0102"},
    "3": {"host": "http://zerohop.sbs:80", "user": "65989464", "pass": "29348534"},
    "4": {"host": "http://dnmxelk01.top:80", "user": "881101381017", "pass": "896811296068"}
}

AGENTES_VIP = ["VLC/3.0.4 LibVLC/3.0.4", "okhttp/4.12.0", "EPPIPROPLAYER/1.0.8"]

def limpar(txt):
    if not txt: return ""
    txt = ''.join(c for c in unicodedata.normalize('NFD', str(txt)) if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9]', '', txt.lower())

def executar_proxy(url_video):
    # REDIRECT em porta 80 ou Archive: Isso ZERA o uso de CPU no Koyeb nesses casos
    if ":80" in url_video or "archive.org" in url_video or "blogspot" in url_video:
        return redirect(url_video)

    headers = {"User-Agent": random.choice(AGENTES_VIP), "Range": request.headers.get("Range", "bytes=0-")}
    try:
        r = requests.get(url_video, headers=headers, stream=True, timeout=(5, 300))
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
    srv = FONTES.get(fonte_id, FONTES["1"])

    try:
        url_api = f"{srv['host']}/player_api.php?username={srv['user']}&password={srv['pass']}&action=get_vod_streams"
        dados = requests.get(url_api, timeout=5).json()
        for item in dados:
            if alvo in limpar(item.get('name', '')):
                v_url = f"{srv['host']}/movie/{srv['user']}/{srv['pass']}/{item.get('stream_id')}.mp4"
                return executar_proxy(v_url)
    except: pass
    return "Nao encontrado", 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)), threaded=True)
