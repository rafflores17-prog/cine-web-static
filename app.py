from flask import Flask, request, Response, stream_with_context, redirect
import requests
import sqlite3
import random
import os
import unicodedata
import re

app = Flask(__name__)
DB_PATH = "filmes.db"

# Chunk equilibrado para manter o CPU baixo e o streaming fluido
CHUNK_SIZE = 1024 * 128 

# SUAS NOVAS APIs (Ordem exata solicitada)
SERVIDORES_API = [
    {"host": "http://newoneblue.site:80", "user": "58257413", "pass": "19193442"},
    {"host": "http://9thgen.skin:80", "user": "11974034383", "pass": "eduardo0102"},
    {"host": "http://zerohop.sbs:80", "user": "65989464", "pass": "29348534"},
    {"host": "http://zerohop.sbs:80", "user": "8051528", "pass": "2363328"},
    {"host": "http://dnmxelk01.top:80", "user": "881101381017", "pass": "896811296068"}
]

# Agentes de elite focados em players de vídeo
AGENTES = [
    "Lavf_60.3.100 LibVLC/3.0.21",
    "VLC/3.0.20 LibVLC/3.0.20",
    "AppleCoreMedia/1.0.0.21G72 (iPhone; iPhone OS 17_5_1)",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
]

def limpar(txt):
    if not txt: return ""
    txt = ''.join(c for c in unicodedata.normalize('NFD', str(txt)) if unicodedata.category(c) != 'Mn')
    # Mantemos letras e números para não confundir sequências (ex: American Pie 1, 2)
    return re.sub(r'[^a-z0-9]', '', txt.lower())

def executar_proxy(url_video):
    # Links de Archive e Blogspot continuam em Redirect para não matar o CPU do Koyeb
    if any(x in url_video.lower() for x in ["archive.org", "googlevideo", "blogspot"]):
        return redirect(url_video)

    headers = {
        "User-Agent": random.choice(AGENTES),
        "Connection": "keep-alive",
        "Accept": "*/*",
        "Range": request.headers.get("Range", "bytes=0-")
    }

    try:
        # Uso de Session para conexões persistentes e rápidas
        with requests.Session() as s:
            r = s.get(url_video, headers=headers, stream=True, timeout=(10, 600), allow_redirects=True)
            
            # Caso algum servidor ainda dê 403, tenta o redirect direto
            if r.status_code == 403:
                return redirect(url_video)

            def generate():
                try:
                    for chunk in r.iter_content(chunk_size=CHUNK_SIZE):
                        if chunk: yield chunk
                except: pass

            resp = Response(stream_with_context(generate()), status=r.status_code)
            resp.headers["Content-Type"] = "video/mp4"
            resp.headers["Accept-Ranges"] = "bytes"
            resp.headers["Access-Control-Allow-Origin"] = "*"
            
            for h in ['Content-Range', 'Content-Length']:
                if h in r.headers: resp.headers[h] = r.headers[h]
            
            return resp
    except:
        return redirect(url_video)

@app.route("/buscar")
def buscar():
    titulo = request.args.get("titulo")
    if not titulo: return "Vazio", 400

    alvo = limpar(titulo)
    print(f"🎯 Mestre, rastreando em novas fontes: {alvo}")

    # 1. VIP.TXT e FILMES_SITE.TXT
    for arq in ["vips.txt", "filmes_site.txt"]:
        if os.path.exists(arq):
            try:
                with open(arq, "r", encoding="utf-8", errors="ignore") as f:
                    for linha in f:
                        if "|" in linha:
                            n, u = linha.split("|", 1)
                            if alvo == limpar(n): return executar_proxy(u.strip())
            except: pass

    # 2. NOVO FILMES.DB (Foco Total)
    if os.path.exists(DB_PATH):
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT url, nome FROM filmes")
            for url_db, nome_db in c.fetchall():
                if alvo == limpar(nome_db):
                    conn.close()
                    return executar_proxy(url_db)
            conn.close()
        except: pass

    # 3. NOVAS APIs (Sequência de 1 a 5)
    for srv in SERVIDORES_API:
        try:
            url_api = f"{srv['host']}/player_api.php?username={srv['user']}&password={srv['pass']}&action=get_vod_streams"
            r = requests.get(url_api, timeout=6).json()
            for item in r:
                if alvo == limpar(item.get('name', '')):
                    v_url = f"{srv['host']}/movie/{srv['user']}/{srv['pass']}/{item.get('stream_id')}.mp4"
                    return executar_proxy(v_url)
        except: continue

    return "Não encontrado", 404

@app.route("/")
def index(): return "🚀 Cine Mega v29 - Direct Connect Ativo"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
