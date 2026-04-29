from flask import Flask, request, Response, stream_with_context, redirect
import requests
import sqlite3
import random
import os
import unicodedata
import re

app = Flask(__name__)
DB_PATH = "filmes.db"

# CHUNK MÍNIMO para não travar a RAM
CHUNK_SIZE = 1024 * 32 

SERVIDORES_API = [
    {"host": "http://newoneblue.site:80", "user": "58257413", "pass": "19193442"},
    {"host": "http://9thgen.skin:80", "user": "11974034383", "pass": "eduardo0102"},
    {"host": "http://zerohop.sbs:80", "user": "65989464", "pass": "29348534"},
    {"host": "http://zerohop.sbs:80", "user": "8051528", "pass": "2363328"},
    {"host": "http://dnmxelk01.top:80", "user": "881101381017", "pass": "896811296068"}
]

AGENTES = [
    "Lavf_60.3.100 LibVLC/3.0.21",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "AppleCoreMedia/1.0.0.21G72 (iPhone; iPhone OS 17_5_1)"
]

def limpar(txt):
    if not txt: return ""
    txt = ''.join(c for c in unicodedata.normalize('NFD', str(txt)) if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9]', '', txt.lower())

def executar_proxy(url_video):
    # ESTRATÉGIA ANTI-TRAVAMENTO:
    # Se o link for de IPTV direto (.mp4, .mkv ou portas :80, :8880), 
    # mandamos o Player abrir DIRETO. Isso evita 100% o erro de memória no Koyeb.
    if any(x in url_video.lower() for x in [":80", ":8880", "movie", "archive", "blogspot"]):
        return redirect(url_video)

    headers = {
        "User-Agent": random.choice(AGENTES),
        "Range": request.headers.get("Range", "bytes=0-")
    }

    try:
        r = requests.get(url_video, headers=headers, stream=True, timeout=(5, 300))
        def generate():
            try:
                for chunk in r.iter_content(chunk_size=CHUNK_SIZE):
                    if chunk: yield chunk
            except: pass
            finally: r.close()

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

    alvo = limpar(titulo)
    print(f"🎯 Mestre, rastreando: {alvo}")

    # 1. VIP / TXT LOCAL
    for arq in ["vips.txt", "filmes_site.txt"]:
        if os.path.exists(arq):
            with open(arq, "r", encoding="utf-8", errors="ignore") as f:
                for linha in f:
                    if "|" in linha:
                        n, u = linha.split("|", 1)
                        if alvo == limpar(n): return executar_proxy(u.strip())

    # 2. BANCO DE DADOS (Busca Rápida)
    if os.path.exists(DB_PATH):
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT url FROM filmes WHERE nome_busca = ? LIMIT 1", (alvo,))
            res = c.fetchone()
            conn.close()
            if res: return executar_proxy(res[0])
        except: pass

    # 3. APIs (Busca em todos os servidores novos)
    for srv in SERVIDORES_API:
        try:
            url_api = f"{srv['host']}/player_api.php?username={srv['user']}&password={srv['pass']}&action=get_vod_streams"
            r = requests.get(url_api, timeout=5).json()
            for item in r:
                if alvo == limpar(item.get('name', '')):
                    v_url = f"{srv['host']}/movie/{srv['user']}/{srv['pass']}/{item.get('stream_id')}.mp4"
                    return executar_proxy(v_url)
        except: continue

    return "Não encontrado", 404

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port, threaded=True)
