from flask import Flask, request, Response, stream_with_context
import requests
import sqlite3
import random
import os
import re
from urllib.parse import quote

app = Flask(__name__)

# 🚀 AGENTES VIP
AGENTES_VIP = [
    "EPPIPROPLAYER/1.0.8 (Linux;Android 14) AndroidXMedia3/1.5.1",
    "purpleplayer/1.2.82",
    "Dalvik/2.1.0 (Linux; U; Android 14; 2312FPCA6G Build/UP1A.231005.007)",
    "Dart/3.11 (dart:io)"
]

# 🛡️ SERVIDORES DE APOIO (Cinevexio e Stmax)
SERVIDORES_API = [
    {"nome": "Cinevexio", "host": "http://cinevexio.top:80", "user": "175473583", "pass": "643238922"},
    {"nome": "Stmax", "host": "http://stmax.top:80", "user": "lucas6043", "pass": "px2926br"}
]

@app.route("/buscar")
def buscar_e_proxy():
    titulo = request.args.get("titulo")
    if not titulo: return "Título vazio", 400

    try:
        palavras = titulo.split()
        termo = " ".join(palavras[:2]) if len(palavras) > 1 else palavras[0]
        termo_api = re.sub(r'[^\w\s]', '', titulo).lower().strip()

        # 🔍 1º LUGAR: Busca no filmes.db (Serv99 - Mais rápido)
        conn = sqlite3.connect('filmes.db')
        c = conn.cursor()
        c.execute("SELECT url FROM playlist WHERE nome LIKE ? LIMIT 1", (f"%{termo}%",))
        resultado = c.fetchone()
        conn.close()

        if resultado:
            print(f"✅ Achado no Banco Local (Serv99): {titulo}")
            return executar_proxy(resultado[0])

        # 🔍 2º LUGAR: Busca nas APIs externas (Cinevexio / Stmax)
        print(f"⚠️ Não achou no DB, tentando APIs externas...")
        for srv in SERVIDORES_API:
            try:
                url_api = f"{srv['host']}/player_api.php?username={srv['user']}&password={srv['pass']}&action=get_vod_streams"
                r = requests.get(url_api, timeout=5).json()
                
                for item in r:
                    nome_iptv = re.sub(r'[^\w\s]', '', item.get('name', '')).lower()
                    if termo_api in nome_iptv:
                        v_url = f"{srv['host']}/movie/{srv['user']}/{srv['pass']}/{item.get('stream_id')}.mp4"
                        print(f"✅ Achado na API do {srv['nome']}: {item.get('name')}")
                        return executar_proxy(v_url)
            except:
                continue

        return "Filme não encontrado em nenhum servidor.", 404

    except Exception as e:
        return f"Erro no motor: {e}", 500

def executar_proxy(url_video):
    agente = random.choice(AGENTES_VIP)
    headers = {
        "User-Agent": agente,
        "Accept": "*/*",
        "Connection": "keep-alive",
        "Referer": "http://iptv.com"
    }
    
    range_header = request.headers.get('Range', None)
    if range_header: headers['Range'] = range_header

    try:
        r = requests.get(url_video, headers=headers, stream=True, timeout=(5, 30), allow_redirects=True)
        
        def generate():
            for chunk in r.iter_content(chunk_size=128 * 1024):
                if chunk: yield chunk
        
        resp_headers = {
            "Accept-Ranges": "bytes",
            "Access-Control-Allow-Origin": "*",
            "Cache-Control": "no-store"
        }
        if 'Content-Range' in r.headers: resp_headers['Content-Range'] = r.headers['Content-Range']
        if 'Content-Length' in r.headers: resp_headers['Content-Length'] = r.headers['Content-Length']

        return Response(
            stream_with_context(generate()),
            status=r.status_code,
            content_type=r.headers.get("Content-Type", "video/mp4"),
            headers=resp_headers
        )
    except:
        return "Erro ao processar streaming", 500

@app.route("/")
def index(): return "🚀 Motor Cine Mega Híbrido Ativo!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
