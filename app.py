from flask import Flask, request, Response, stream_with_context, redirect, jsonify
import requests
import sqlite3
import random
import os
import unicodedata
import re
from datetime import datetime

app = Flask(__name__)

# =========================
# CONFIGURAÇÕES E APIS MESTRE
# =========================
DB_PATH = "filmes.db"
CHUNK_SIZE = 1024 * 256

# PRIORIDADE TOTAL: serv99.xyz
API_PRIORITARIA = {
    "host": "http://serv99.xyz:8880",
    "user": "261491762",
    "pass": "2516895925"
}

API_SECUNDARIA = {
    "host": "http://techon.one:80",
    "user": "003008",
    "pass": "440144634"
}

# SEUS MELHORES AGENTES (MISTURA DE ELITE)
AGENTES_VIP = [
    "EPPIPROPLAYER/1.0.8 (Linux;Android 14) AndroidXMedia3/1.5.1",
    "purpleplayer/1.2.82",
    "VLC/3.0.4 LibVLC/3.0.4",
    "Dalvik/2.1.0 (Linux; U; Android 14; 2312FPCA6G Build/UP1A.231005.007)",
    "okhttp/4.12.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
]

# =========================
# FUNÇÕES DE LIMPEZA
# =========================

def limpar(txt):
    if not txt: return ""
    txt = ''.join(c for c in unicodedata.normalize('NFD', str(txt)) if unicodedata.category(c) != 'Mn')
    txt = re.sub(r'[^a-zA-Z0-9\s]', ' ', txt)
    return re.sub(r'\s+', ' ', txt).strip().lower()

# =========================
# BUSCA HÍBRIDA (TXT + DB)
# =========================

def buscar_fontes_locais(t_limpo):
    # 1. Prioridade serv99 e vips no TXT
    for arq in ["vips.txt", "filmes_site.txt"]:
        if os.path.exists(arq):
            try:
                with open(arq, "r", encoding="utf-8", errors="ignore") as f:
                    for linha in f:
                        if "|" in linha:
                            nome, url = linha.split("|", 1)
                            if t_limpo in limpar(nome):
                                return url.strip()
            except: pass

    # 2. Banco de Dados
    if os.path.exists(DB_PATH):
        try:
            with sqlite3.connect(DB_PATH) as conn:
                c = conn.cursor()
                c.execute("SELECT url FROM filmes WHERE nome_busca = ? LIMIT 1", (t_limpo,))
                res = c.fetchone()
                if not res:
                    c.execute("SELECT url FROM filmes WHERE nome_busca LIKE ? LIMIT 1", (f"{t_limpo}%",))
                    res = c.fetchone()
                if res: return res[0]
        except: pass
    
    return None

# =========================
# ROTA DE BUSCA (CÉREBRO V11)
# =========================

@app.route("/buscar")
def buscar():
    titulo = request.args.get("titulo")
    if not titulo: return "Título vazio", 400
    
    t_limpo = limpar(titulo)
    print(f"🔍 Mestre, buscando: {t_limpo}")

    # Tenta achar o link base no seu acervo
    url_original = buscar_fontes_locais(t_limpo)
    
    # Se for link de IPTV, reconstrói usando o serv99 (PRIORIDADE)
    if url_original and "/movie/" in url_original:
        try:
            stream_id = url_original.split("/")[-1].split(".")[0]
            url_serv99 = f"{API_PRIORITARIA['host']}/movie/{API_PRIORITARIA['user']}/{API_PRIORITARIA['pass']}/{stream_id}.mp4"
            return executar_proxy(url_serv99)
        except: pass

    # Se não achou ou falhou, busca "ao vivo" nas APIs novas
    for api in [API_PRIORITARIA, API_SECUNDARIA]:
        try:
            url_api = f"{api['host']}/player_api.php?username={api['user']}&password={api['pass']}&action=get_vod_streams"
            r = requests.get(url_api, timeout=4).json()
            for item in r:
                if t_limpo in limpar(item.get('name', '')):
                    v_url = f"{api['host']}/movie/{api['user']}/{api['pass']}/{item.get('stream_id')}.mp4"
                    return executar_proxy(v_url)
        except: continue

    return "Filme não encontrado", 404

# =========================
# PROXY CAMALEÃO
# =========================

def executar_proxy(url_video):
    # Escolhe um agente de elite para cada conexão
    agente = random.choice(AGENTES_VIP)
    
    headers = {
        "User-Agent": agente,
        "Accept": "*/*",
        "Connection": "keep-alive",
        "Range": request.headers.get("Range", "bytes=0-")
    }
    
    try:
        r = requests.get(url_video, headers=headers, stream=True, timeout=(10, 120), allow_redirects=True)
        
        def generate():
            for chunk in r.iter_content(chunk_size=CHUNK_SIZE):
                yield chunk
        
        resp = Response(stream_with_context(generate()), status=r.status_code)
        resp.headers["Content-Type"] = "video/mp4"
        resp.headers["Accept-Ranges"] = "bytes"
        resp.headers["Access-Control-Allow-Origin"] = "*"
        
        if 'Content-Range' in r.headers: resp.headers['Content-Range'] = r.headers['Content-Range']
        if 'Content-Length' in r.headers: resp.headers['Content-Length'] = r.headers['Content-Length']
        
        return resp
    except:
        return redirect(url_video)

@app.route("/")
def index():
    return "🚀 Cine Mega v11 - Blindado & Prioridade serv99 On!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
