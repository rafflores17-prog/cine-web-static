from flask import Flask, request, Response, stream_with_context
import requests
import sqlite3
import random
import os
from urllib.parse import quote

app = Flask(__name__)

AGENTES_VIP = [
    "EPPIPROPLAYER/1.0.8 (Linux;Android 14) AndroidXMedia3/1.5.1",
    "purpleplayer/1.2.82",
    "Dalvik/2.1.0 (Linux; U; Android 14; 2312FPCA6G Build/UP1A.231005.007)"
]

# 📂 SEU ACERVO DE ELITE (LINKS MANUAIS DO ARCHIVE.ORG)
# Adicione aqui qualquer filme que você queira substituir do servidor original
MEUS_FILMES_VIPS = {
    "american pie": "https://archive.org/download/american-pie-dublado-cine-mega/American%20Pie%201%2C%20A%20Primeira%20Vez%20%C3%A9%20Inesquec%C3%ADvel%20%281999%29.mp4",
}

SERVIDORES_API = [
    {"nome": "Cinevexio", "host": "http://cinevexio.top:80", "user": "175473583", "pass": "643238922"},
    {"nome": "Stmax", "host": "http://stmax.top:80", "user": "lucas6043", "pass": "px2926br"}
]

@app.route("/buscar")
def buscar_e_proxy():
    titulo = request.args.get("titulo")
    if not titulo: return "Título vazio", 400

    titulo_limpo = titulo.strip().lower()

    # 🚀 1º PASSO: CONFERE SE ESTÁ NA SUA LISTA VIP
    for nome_vip, url_vip in MEUS_FILMES_VIPS.items():
        if nome_vip in titulo_limpo:
            print(f"💎 ACERVO VIP: Rodando {nome_vip} direto do seu Archive.org")
            return executar_proxy(url_vip)

    # 🔍 2º PASSO: BUSCA NORMAL NO DB E APIs
    try:
        conn = sqlite3.connect('filmes.db')
        c = conn.cursor()
        palavras = titulo_limpo.split()
        termo_base = palavras[0] if len(palavras) == 1 else " ".join(palavras[:2])
        
        query = "SELECT url, nome FROM playlist WHERE nome LIKE ? ORDER BY ABS(LENGTH(nome) - LENGTH(?)) ASC LIMIT 1"
        c.execute(query, (f"%{termo_base}%", titulo_limpo))
        resultado = c.fetchone()
        conn.close()

        if resultado:
            return executar_proxy(resultado[0])
        
        for srv in SERVIDORES_API:
            try:
                url_api = f"{srv['host']}/player_api.php?username={srv['user']}&password={srv['pass']}&action=get_vod_streams"
                r = requests.get(url_api, timeout=3).json()
                for item in r:
                    if titulo_limpo in item.get('name', '').lower():
                        v_url = f"{srv['host']}/movie/{srv['user']}/{srv['pass']}/{item.get('stream_id')}.mp4"
                        return executar_proxy(v_url)
            except: continue

        return "Não encontrado", 404
    except Exception as e: return str(e), 500

def executar_proxy(url_video):
    agente = random.choice(AGENTES_VIP)
    headers = {"User-Agent": agente, "Accept": "*/*", "Connection": "keep-alive", "Referer": "http://iptv.com"}
    range_header = request.headers.get('Range', None)
    if range_header: headers['Range'] = range_header

    try:
        r = requests.get(url_video, headers=headers, stream=True, timeout=(5, 60), allow_redirects=True)
        c_type = r.headers.get("Content-Type", "video/mp4")
        
        def generate():
            for chunk in r.iter_content(chunk_size=256 * 1024):
                if chunk: yield chunk
        
        resp_headers = {
            "Accept-Ranges": "bytes",
            "Access-Control-Allow-Origin": "*",
            "Cache-Control": "public, max-age=3600"
        }
        if 'Content-Range' in r.headers: resp_headers['Content-Range'] = r.headers['Content-Range']
        if 'Content-Length' in r.headers: resp_headers['Content-Length'] = r.headers['Content-Length']

        return Response(stream_with_context(generate()), status=r.status_code, content_type=c_type, headers=resp_headers)
    except: return "Erro ao processar", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
