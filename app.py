from flask import Flask, request, Response, stream_with_context, redirect
import requests
import sqlite3
import random
import os
import unicodedata
import re

app = Flask(__name__)
DB_PATH = "filmes.db"

# CHUNK OTIMIZADO: Evita CPU 100% e IncompleteRead no Koyeb
CHUNK_SIZE = 1024 * 256 

# Suas APIs Atualizadas (Removido Techon, Incluído CLDX com 2 contas)
SERVIDORES_API = [
    {"nome": "serv99", "host": "http://serv99.xyz:8880", "user": "261491762", "pass": "2516895925"},
    {"nome": "CLDX_Rio_1", "host": "http://cldx-rio-go.top:80", "user": "CvkKCt", "pass": "TbCvjD"},
    {"nome": "CLDX_Rio_2", "host": "http://cldx-rio-go.top:80", "user": "JoseCampos", "pass": "jxg78py9mk"}
]

# Agentes de Elite para passar pelos bloqueios
AGENTES = [
    "EPPIPROPLAYER/1.0.8 (Linux;Android 14)",
    "VLC/3.0.4 LibVLC/3.0.4",
    "okhttp/4.12.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
]

def extrair_letras_e_numeros(txt):
    if not txt: return ""
    txt = ''.join(c for c in unicodedata.normalize('NFD', str(txt)) if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9]', '', txt.lower())

def executar_proxy(url_video):
    headers = {
        "User-Agent": random.choice(AGENTES),
        "Connection": "keep-alive",
        "Range": request.headers.get("Range", "bytes=0-")
    }
    try:
        r = requests.get(url_video, headers=headers, stream=True, timeout=(10, 300), allow_redirects=True)
        
        def generate():
            try:
                for chunk in r.iter_content(chunk_size=CHUNK_SIZE):
                    if chunk: yield chunk
            except:
                pass # Evita travar o servidor se o usuário sair do filme

        resp = Response(stream_with_context(generate()), status=r.status_code)
        resp.headers["Content-Type"] = "video/mp4"
        resp.headers["Accept-Ranges"] = "bytes"
        resp.headers["Access-Control-Allow-Origin"] = "*"
        
        if 'Content-Range' in r.headers: resp.headers['Content-Range'] = r.headers['Content-Range']
        if 'Content-Length' in r.headers: resp.headers['Content-Length'] = r.headers['Content-Length']
        return resp
    except:
        return redirect(url_video)

@app.route("/buscar")
def buscar():
    titulo = request.args.get("titulo")
    if not titulo: return "Vazio", 400

    alvo = extrair_letras_e_numeros(titulo)
    print(f"🔎 Mestre, buscando em tudo: {alvo}")

    # 1. BUSCA NOS ARQUIVOS TXT (vips.txt e filmes_site.txt)
    for arq in ["vips.txt", "filmes_site.txt"]:
        if os.path.exists(arq):
            try:
                with open(arq, "r", encoding="utf-8", errors="ignore") as f:
                    for linha in f:
                        if "|" in linha:
                            nome_txt, url_txt = linha.split("|", 1)
                            if alvo == extrair_letras_e_numeros(nome_txt):
                                return executar_proxy(url_txt.strip())
            except: pass

    # 2. BUSCA NO BANCO DE DADOS (filmes.db)
    if os.path.exists(DB_PATH):
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT url, nome FROM filmes")
            for url_db, nome_db in c.fetchall():
                if alvo == extrair_letras_e_numeros(nome_db):
                    conn.close()
                    return executar_proxy(url_db)
            conn.close()
        except: pass

    # 3. BUSCA NAS APIs EXTERNAS (Ordem: serv99 -> CLDX 1 -> CLDX 2)
    for srv in SERVIDORES_API:
        try:
            url_api = f"{srv['host']}/player_api.php?username={srv['user']}&password={srv['pass']}&action=get_vod_streams"
            r = requests.get(url_api, timeout=6).json()
            for item in r:
                nome_api = extrair_letras_e_numeros(item.get('name', ''))
                if alvo == nome_api:
                    v_url = f"{srv['host']}/movie/{srv['user']}/{srv['pass']}/{item.get('stream_id')}.mp4"
                    return executar_proxy(v_url)
        except: continue

    return "Filme nao encontrado", 404

@app.route("/")
def index(): return "🚀 Cine Mega v25 - Multi-API & DB Ativo!"

if __name__ == "__main__":
    # Ajuste automático de porta para o Koyeb
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
