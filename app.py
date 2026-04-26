from flask import Flask, render_template, request, send_from_directory, jsonify, Response, stream_with_context
import requests
import re
import os
import random
import sqlite3
import glob # 🚀 ESSENCIAL PARA LER OS 12 BANCOS

app = Flask(__name__)

NOME_SITE = "Cine Mega"
SITE_URL = "https://www.cinemega.online"
TMDB_API_KEY = "c90fb79a2f7d756a49bee848bce5f413"
IMG = "https://image.tmdb.org/t/p/w500"
BG = "https://image.tmdb.org/t/p/original"

SERVIDORES = [
    {"host": "http://cinevexio.top:80", "user": "175473583", "pass": "643238922"},
    {"host": "http://serv99.xyz:8880", "user": "1764371", "pass": "2419902"},
    {"host": "http://stmax.top:80", "user": "lucas6043", "pass": "px2926br"},
    {"host": "http://koquwz.com:80", "user": "471204", "pass": "epp4Jx"},
    {"host": "http://techon.one:80", "user": "003008", "pass": "440144634"}
]

AGENTES_VIP = [
    "EPPIPROPLAYER/1.0.8 (Linux;Android 14) AndroidXMedia3/1.5.1",
    "purpleplayer/1.2.82",
    "Dalvik/2.1.0 (Linux; U; Android 14; 2312FPCA6G Build/UP1A.231005.007)",
    "Dart/3.11 (dart:io)"
]

# ================================
# PROXY DE VÍDEO (REVISADO)
# ================================
@app.route("/proxy")
def proxy_video():
    url = request.args.get("url")
    user_agent_custom = request.args.get("user_agent") # Pega o agente enviado pelo site
    
    if not url:
        return "URL não fornecida", 400

    try:
        # Usa o agente enviado ou sorteia um novo
        disfarce_atual = user_agent_custom if user_agent_custom else random.choice(AGENTES_VIP)
        
        headers = {
            "User-Agent": disfarce_atual,
            "Accept": "*/*",
            "Connection": "keep-alive",
            "Referer": "http://iptv.com" # 🛡️ Ajuda a enganar o bloqueio
        }

        range_header = request.headers.get('Range', None)
        if range_header:
            headers['Range'] = range_header

        r = requests.get(url, headers=headers, stream=True, timeout=(5, 20), allow_redirects=True, verify=False)

        status_code = r.status_code
        if status_code not in (200, 206):
            return "Servidor indisponível", 502

        def generate():
            try:
                for chunk in r.iter_content(chunk_size=1024 * 128): # 128kb para fluidez
                    if chunk: yield chunk
            finally:
                r.close()

        resp_headers = {
            "Accept-Ranges": "bytes",
            "Cache-Control": "no-store",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*" # 🔓 Libera para o Chrome
        }
        
        if 'Content-Range' in r.headers:
            resp_headers['Content-Range'] = r.headers['Content-Range']
        if 'Content-Length' in r.headers:
            resp_headers['Content-Length'] = r.headers['Content-Length']

        return Response(
            stream_with_context(generate()),
            status=status_code,
            content_type=r.headers.get("Content-Type", "video/mp4"),
            headers=resp_headers
        )

    except Exception as e:
        return f"Erro proxy: {e}", 500

# ================================
# BUSCAR FILME (SISTEMA MULTI-BANCO DATA*.DB)
# ================================
def buscar_filme(titulo):
    try:
        palavra_chave = titulo.split(':')[0].strip()
        termo_busca = f"%{palavra_chave}%"
        
        # 🔍 ESCANEIA TODOS OS BANCOS DATA1.DB, DATA2.DB...
        bancos = glob.glob("data*.db")
        
        for db_nome in sorted(bancos):
            try:
                conn = sqlite3.connect(db_nome)
                c = conn.cursor()
                c.execute("SELECT url FROM playlist WHERE nome LIKE ? LIMIT 1", (termo_busca,))
                resultado = c.fetchone()
                conn.close()
                
                if resultado:
                    # Envia para o proxy com a proteção de agente
                    agente = random.choice(AGENTES_VIP)
                    from urllib.parse import quote
                    return f"/proxy?url={quote(resultado[0], safe='')}&user_agent={quote(agente)}"
            except: continue
            
    except Exception as e:
        print("Erro DB:", e)

    # 🌐 FALLBACK API (SE NÃO ACHAR NOS BANCOS)
    for srv in SERVIDORES:
        try:
            url_api = f"{srv['host']}/player_api.php?username={srv['user']}&password={srv['pass']}&action=get_vod_streams"
            r = requests.get(url_api, timeout=5).json()
            for item in r:
                if palavra_chave.lower() in item.get('name', '').lower():
                    v_url = f"{srv['host']}/movie/{srv['user']}/{srv['pass']}/{item.get('stream_id')}.mp4"
                    return f"/proxy?url={v_url}"
        except: continue
            
    return None

# ================================
# ROTAS RESTANTES
# ================================
@app.route("/")
def home():
    q = request.args.get("q")
    url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&language=pt-BR&query={q}" if q else f"https://api.themoviedb.org/3/movie/popular?api_key={TMDB_API_KEY}&language=pt-BR"
    try:
        res = requests.get(url, timeout=10).json().get("results", [])
    except: res = []
    return render_template("index.html", filmes=res[:20], img=IMG, nome_site=NOME_SITE)

@app.route("/filme/<int:id>")
def detalhes(id):
    try:
        data = requests.get(f"https://api.themoviedb.org/3/movie/{id}?api_key={TMDB_API_KEY}&language=pt-BR&append_to_response=videos", timeout=10).json()
        play_link = buscar_filme(data.get('title', ''))
        trailer = next((v['key'] for v in data.get('videos', {}).get('results', []) if v['type'] == 'Trailer'), None)
        return render_template("detalhes.html", filme=data, img=IMG, bg=BG, play_link=play_link, nome_site=NOME_SITE, trailer_key=trailer)
    except: return "Erro", 404

if __name__ == "__main__":
    PORT = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=PORT)
