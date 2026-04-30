from flask import Flask, request, Response, stream_with_context, redirect
import requests
import sqlite3
import random
import os
import unicodedata
import re

app = Flask(__name__)
DB_PATH = "filmes.db"
CHUNK_SIZE = 1024 * 128  # 128KB para estabilidade no streaming

# 🛡️ APIS DE ELITE (MNBA, DNSROT, KMEDIAPLAY)
SERVIDORES_API = [
    {"nome": "Mnba", "host": "http://mnba.shop:80", "user": "danicamara", "pass": "acg2010v"},
    {"nome": "Dnsrot", "host": "http://play.dnsrot.vip:80", "user": "sheilalima11", "pass": "s6dfkck1jlq"},
    {"nome": "Kmediaplay", "host": "http://kmediaplay.click:80", "user": "Indio1432", "pass": "indio1433"}
]

# 🚀 AGENTES VIP (Preservando a compatibilidade)
AGENTES_VIP = [
    "EPPIPROPLAYER/1.0.8 (Linux;Android 14) AndroidXMedia3/1.5.1",
    "purpleplayer/1.2.82",
    "Dalvik/2.1.0 (Linux; U; Android 14; 2312FPCA6G Build/UP1A.231005.007)",
    "VLC/3.0.4 LibVLC/3.0.4",
    "okhttp/4.12.0"
]

def limpar(txt):
    if not txt: return ""
    txt = ''.join(c for c in unicodedata.normalize('NFD', str(txt)) if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9]', '', txt.lower())

def executar_proxy(url_video):
    # Archive e Blogspot vão direto (Redirect 302) para poupar o servidor
    if any(x in url_video.lower() for x in ["archive.org", "googlevideo", "blogspot"]):
        return redirect(url_video, code=302)

    headers = {
        "User-Agent": random.choice(AGENTES_VIP),
        "Connection": "keep-alive",
        "Range": request.headers.get("Range", "bytes=0-")
    }

    try:
        # Timeout longo para evitar quedas no Chrome e UC Browser
        r = requests.get(url_video, headers=headers, stream=True, timeout=(10, 600), allow_redirects=True)
        
        if r.status_code >= 400: 
            return redirect(url_video, code=302)

        def generate():
            try:
                for chunk in r.iter_content(chunk_size=CHUNK_SIZE):
                    if chunk: yield chunk
            except: 
                pass
            finally:
                r.close()

        resp = Response(stream_with_context(generate()), status=r.status_code)
        
        # 🛡️ HEADERS PARA O CHROME ACEITAR O STREAMING DIRETO
        resp.headers["Content-Type"] = "video/mp4"
        resp.headers["Accept-Ranges"] = "bytes"
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["X-Content-Type-Options"] = "nosniff"
        
        # Repassa os dados de tamanho para o player habilitar o "Seek" (pular tempo)
        if 'Content-Length' in r.headers:
            resp.headers["Content-Length"] = r.headers["Content-Length"]
        if 'Content-Range' in r.headers:
            resp.headers["Content-Range"] = r.headers["Content-Range"]
            
        return resp
    except:
        return redirect(url_video, code=302)

@app.route("/buscar")
def buscar():
    titulo = request.args.get("titulo")
    if not titulo: return "Título vazio", 400
    alvo = limpar(titulo)

    # 1. VIP e TXT (Sua curadoria)
    for arq in ["vips.txt", "filmes_site.txt"]:
        if os.path.exists(arq):
            with open(arq, "r", encoding="utf-8", errors="ignore") as f:
                for linha in f:
                    if "|" in linha:
                        n, u = linha.split("|", 1)
                        if alvo in limpar(n): return executar_proxy(u.strip())

    # 2. BANCO DE DADOS (Prioridade sobre API)
    if os.path.exists(DB_PATH):
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT url FROM filmes WHERE nome_busca LIKE ? OR nome_busca = ? LIMIT 1", (f'%{alvo}%', alvo))
            res = c.fetchone()
            conn.close()
            if res: return executar_proxy(res[0])
        except: pass

    # 3. APIs DE ELITE (MNBA, DNSROT...)
    for srv in SERVIDORES_API:
        try:
            url_api = f"{srv['host']}/player_api.php?username={srv['user']}&password={srv['pass']}&action=get_vod_streams"
            r = requests.get(url_api, timeout=5)
            if r.status_code == 200:
                for item in r.json():
                    if alvo in limpar(item.get('name', '')):
                        v_url = f"{srv['host']}/movie/{srv['user']}/{srv['pass']}/{item.get('stream_id')}.mp4"
                        return executar_proxy(v_url)
        except: continue

    return "Não encontrado", 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)), threaded=True)
