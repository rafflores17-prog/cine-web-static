from flask import Flask, request, Response, stream_with_context
import requests
import sqlite3
import random
import os
import re
from urllib.parse import quote

app = Flask(__name__)

# AGENTES VIP QUE NÃO TRAVAM
AGENTES_VIP = [
    "EPPIPROPLAYER/1.0.8 (Linux;Android 14) AndroidXMedia3/1.5.1",
    "purpleplayer/1.2.82",
    "Dalvik/2.1.0 (Linux; U; Android 14; 2312FPCA6G Build/UP1A.231005.007)",
    "Dart/3.11 (dart:io)"
]

# ================================
# ROTA DE BUSCA E PROXY (TUDO EM UM)
# ================================
@app.route("/buscar")
def buscar_e_proxy():
    titulo = request.args.get("titulo")
    if not titulo: return "Título vazio", 400

    try:
        # Limpeza para busca precisa
        palavras = titulo.split()
        termo = " ".join(palavras[:2]) if len(palavras) > 1 else palavras[0]
        
        # 🔍 Busca no seu banco único de 2MB
        conn = sqlite3.connect('filmes.db')
        c = conn.cursor()
        c.execute("SELECT url FROM playlist WHERE nome LIKE ? LIMIT 1", (f"%{termo}%",))
        resultado = c.fetchone()
        conn.close()

        if resultado:
            return executar_proxy(resultado[0])
        else:
            return "Filme não encontrado no acervo.", 404
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
    
    # Suporte a Range para o Chrome/UC não travarem
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
        return "Erro ao processar vídeo", 500

@app.route("/")
def index(): return "🚀 Motor Cine Mega Ativo!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
