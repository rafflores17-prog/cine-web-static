from flask import Flask, request, Response, stream_with_context
import requests
import sqlite3
import random
import os
import re
from urllib.parse import quote

app = Flask(__name__)

# 🚀 AGENTES VIP - Mantendo os que você confirmou que funcionam
AGENTES_VIP = [
    "EPPIPROPLAYER/1.0.8 (Linux;Android 14) AndroidXMedia3/1.5.1",
    "purpleplayer/1.2.82",
    "Dalvik/2.1.0 (Linux; U; Android 14; 2312FPCA6G Build/UP1A.231005.007)"
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

    # Limpeza para busca cirúrgica
    titulo_limpo = titulo.strip()
    palavras = titulo_limpo.split()
    termo_base = palavras[0] if len(palavras) == 1 else " ".join(palavras[:2])

    try:
        # 🔍 1º LUGAR: Busca no filmes.db (Serv99 - 2MB)
        conn = sqlite3.connect('filmes.db')
        c = conn.cursor()
        
        # Lógica Anti-Mentira: Busca por similaridade de tamanho para evitar filmes errados
        query = "SELECT url, nome FROM playlist WHERE nome LIKE ? ORDER BY ABS(LENGTH(nome) - LENGTH(?)) ASC LIMIT 1"
        c.execute(query, (f"%{termo_base}%", titulo_limpo))
        resultado = c.fetchone()
        conn.close()

        if resultado:
            print(f"✅ Localizado no DB: {resultado[1]}")
            return executar_proxy(resultado[0])
        
        # 🔍 2º LUGAR: Busca nas APIs externas (Se não achar no DB local)
        for srv in SERVIDORES_API:
            try:
                url_api = f"{srv['host']}/player_api.php?username={srv['user']}&password={srv['pass']}&action=get_vod_streams"
                r = requests.get(url_api, timeout=3).json() 
                for item in r:
                    nome_api = item.get('name', '').lower()
                    if titulo_limpo.lower() in nome_api:
                        v_url = f"{srv['host']}/movie/{srv['user']}/{srv['pass']}/{item.get('stream_id')}.mp4"
                        print(f"✅ Localizado na API {srv['nome']}: {item.get('name')}")
                        return executar_proxy(v_url)
            except: continue

        return "Não encontrado", 404
    except Exception as e:
        return str(e), 500

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
        # Timeout longo (60s) para garantir que filmes pesados não cortem
        r = requests.get(url_video, headers=headers, stream=True, timeout=(5, 60), allow_redirects=True)
        
        # 🛡️ O PULO DO GATO PARA FORMATOS ANTIGOS:
        # Deixamos o Content-Type flexível. Se o servidor disser que é video/x-msvideo (AVI), 
        # o Proxy repassa a informação correta para o Chrome tentar renderizar.
        c_type = r.headers.get("Content-Type", "video/mp4")

        def generate():
            # Chunk de 256kb para carregar o buffer do player mais rápido
            for chunk in r.iter_content(chunk_size=256 * 1024):
                if chunk: yield chunk
        
        resp_headers = {
            "Accept-Ranges": "bytes",
            "Access-Control-Allow-Origin": "*",
            "Cache-Control": "public, max-age=3600",
            "Connection": "keep-alive"
        }
        
        # Repassa informações de tamanho e posição do vídeo (essencial para o "scroll" do player)
        if 'Content-Range' in r.headers: resp_headers['Content-Range'] = r.headers['Content-Range']
        if 'Content-Length' in r.headers: resp_headers['Content-Length'] = r.headers['Content-Length']
        
        return Response(
            stream_with_context(generate()), 
            status=r.status_code, 
            content_type=c_type, 
            headers=resp_headers
        )
    except Exception as e:
        print(f"Erro no streaming: {e}")
        return "Erro ao processar vídeo", 500

@app.route("/")
def index():
    return "🚀 Motor Cine Mega Híbrido - Online e Operacional!"

if __name__ == "__main__":
    # Rodando na porta padrão do Koyeb
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
