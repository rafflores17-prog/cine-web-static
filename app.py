from flask import Flask, request, Response, stream_with_context, redirect
import requests
import sqlite3
import random
import os
import unicodedata
import re

app = Flask(__name__)
DB_PATH = "filmes.db"

# Chunk equilibrado para não estourar a RAM
CHUNK_SIZE = 1024 * 128 

SERVIDORES_API = [
    {"nome": "serv99", "host": "http://serv99.xyz:8880", "user": "261491762", "pass": "2516895925"},
    {"nome": "CLDX_1", "host": "http://cldx-rio-go.top:80", "user": "CvkKCt", "pass": "TbCvjD"},
    {"nome": "CLDX_2", "host": "http://cldx-rio-go.top:80", "user": "JoseCampos", "pass": "jxg78py9mk"}
]

# Agentes que simulam dispositivos reais e Apps de IPTV
AGENTES = [
    "Lavf_60.3.100 LibVLC/3.0.21", # Seu agente de teste
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "AppleCoreMedia/1.0.0.21G72 (iPhone; iPhone OS 17_5_1)",
    "DuneHD/1.0 (230331_0206_r21)"
]

def limpar(txt):
    if not txt: return ""
    txt = ''.join(c for c in unicodedata.normalize('NFD', str(txt)) if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9]', '', txt.lower())

def executar_proxy(url_video):
    # Archive e links de Blogspot vão direto (Koyeb não aguenta o peso deles)
    if any(x in url_video.lower() for x in ["archive.org", "googlevideo", "blogspot"]):
        return redirect(url_video)

    headers = {
        "User-Agent": random.choice(AGENTES),
        "Accept": "*/*",
        "Accept-Language": "pt-BR,pt;q=0.9",
        "Connection": "keep-alive",
        "Range": request.headers.get("Range", "bytes=0-")
    }

    try:
        # Usamos uma sessão para reaproveitar a conexão e ser mais rápido
        with requests.Session() as s:
            r = s.get(url_video, headers=headers, stream=True, timeout=(10, 600), allow_redirects=True)
            
            # Se o Cloudflare bloquear (403), tentamos empurrar o link direto
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
            
            # Repassa os tamanhos para o player não bugar na barra de tempo
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
    print(f"🎯 Cruzando dados: {alvo}")

    # --- 1. BUSCA ARQUIVOS ---
    for arq in ["vips.txt", "filmes_site.txt"]:
        if os.path.exists(arq):
            with open(arq, "r", encoding="utf-8", errors="ignore") as f:
                for linha in f:
                    if "|" in linha:
                        n, u = linha.split("|", 1)
                        if alvo == limpar(n): return executar_proxy(u.strip())

    # --- 2. BUSCA DB ---
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

    # --- 3. BUSCA APIs (Aumentei o timeout da busca) ---
    for srv in SERVIDORES_API:
        try:
            url_api = f"{srv['host']}/player_api.php?username={srv['user']}&password={srv['pass']}&action=get_vod_streams"
            r = requests.get(url_api, timeout=7).json()
            for item in r:
                if alvo == limpar(item.get('name', '')):
                    v_url = f"{srv['host']}/movie/{srv['user']}/{srv['pass']}/{item.get('stream_id')}.mp4"
                    return executar_proxy(v_url)
        except: continue

    return "Não encontrado", 404

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
