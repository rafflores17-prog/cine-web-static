from flask import Flask, request, Response, stream_with_context, redirect
import requests
import sqlite3
import random
import os
from urllib.parse import quote

app = Flask(__name__)

# 🚀 AGENTES VIP - Blindagem contra bloqueios de servidores IPTV
AGENTES_VIP = [
    "EPPIPROPLAYER/1.0.8 (Linux;Android 14) AndroidXMedia3/1.5.1",
    "purpleplayer/1.2.82",
    "Dalvik/2.1.0 (Linux; U; Android 14; 2312FPCA6G Build/UP1A.231005.007)",
    "Dart/3.9 (dart:io)",
    "VLC/3.0.4 LibVLC/3.0.4",
    "okhttp/4.12.0"
]

SERVIDORES_API = [
    {"nome": "Cinevexio", "host": "http://cinevexio.top:80", "user": "175473583", "pass": "643238922"},
    {"nome": "Stmax", "host": "http://stmax.top:80", "user": "lucas6043", "pass": "px2926br"}
]

def ler_arquivo_txt(caminho):
    acervo = {}
    if os.path.exists(caminho):
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                for linha in f:
                    if "|" in linha:
                        nome, url = linha.split("|", 1)
                        acervo[nome.strip().lower()] = url.strip()
        except: pass
    return acervo

def executar_proxy(url_video):
    """ Proxy Inteligente: Resolve Chrome Crash e engana bloqueios IPTV """
    # Se o link for do Archive.org, podemos ir direto (mais rápido e seguro)
    if "archive.org" in url_video.lower():
        return redirect(url_video, code=302)

    agente = random.choice(AGENTES_VIP)
    headers = {
        "User-Agent": agente,
        "Accept": "*/*",
        "Connection": "keep-alive",
        "Referer": "http://iptv.com"
    }
    
    range_header = request.headers.get('Range', None)
    if range_header:
        headers['Range'] = range_header

    try:
        r = requests.get(url_video, headers=headers, stream=True, timeout=(5, 60), allow_redirects=True)
        
        def generate():
            # Chunk de 256kb para manter o buffer do Chrome feliz
            for chunk in r.iter_content(chunk_size=256 * 1024):
                if chunk: yield chunk
        
        resp_headers = {
            "Accept-Ranges": "bytes",
            "Access-Control-Allow-Origin": "*",
            "Content-Type": r.headers.get("Content-Type", "video/mp4"),
            "Cache-Control": "public, max-age=3600"
        }
        
        if 'Content-Range' in r.headers: resp_headers['Content-Range'] = r.headers['Content-Range']
        if 'Content-Length' in r.headers: resp_headers['Content-Length'] = r.headers['Content-Length']
        
        return Response(stream_with_context(generate()), status=r.status_code, headers=resp_headers)
    except Exception as e:
        return "Erro ao processar vídeo", 500

@app.route("/buscar")
def buscar():
    titulo = request.args.get("titulo")
    if not titulo: return "Título vazio", 400
    
    titulo_limpo = titulo.strip().lower()

    # 🥇 1º LUGAR: ACERVO GIGANTE (filmes_site.txt) - Prioridade para o catálogo geral
    ACERVO_GIGANTE = ler_arquivo_txt("filmes_site.txt")
    for nome_txt, url_txt in ACERVO_GIGANTE.items():
        if nome_txt == titulo_limpo: # Busca exata primeiro
            print(f"🚀 GIGANTE (EXATO): {nome_txt}")
            return executar_proxy(url_txt)

    # 🥈 2º LUGAR: BANCO DE DADOS LOCAL (filmes.db)
    try:
        if os.path.exists('filmes.db'):
            conn = sqlite3.connect('filmes.db')
            c = conn.cursor()
            c.execute("SELECT url FROM playlist WHERE nome LIKE ? LIMIT 1", (f"%{titulo_limpo}%",))
            resultado = c.fetchone()
            conn.close()
            if resultado:
                print("💾 DB LOCAL: Localizado")
                return executar_proxy(resultado[0])
    except: pass

    # 🥉 3º LUGAR: APIs EXTERNAS
    for srv in SERVIDORES_API:
        try:
            url_api = f"{srv['host']}/player_api.php?username={srv['user']}&password={srv['pass']}&action=get_vod_streams"
            r = requests.get(url_api, timeout=4).json()
            for item in r:
                if titulo_limpo == item.get('name', '').lower():
                    v_url = f"{srv['host']}/movie/{srv['user']}/{srv['pass']}/{item.get('stream_id')}.mp4"
                    print(f"📡 API {srv['nome']}: Localizado")
                    return executar_proxy(v_url)
        except: continue

    # 🏅 4º LUGAR (POR ÚLTIMO): SEU VIP (vips.txt)
    # Aqui ele só entra se não achou em lugar nenhum ou se o nome bater certinho
    ACERVO_VIP = ler_arquivo_txt("vips.txt")
    for nome_vip, url_vip in ACERVO_VIP.items():
        if nome_vip == titulo_limpo or (nome_vip in titulo_limpo and len(nome_vip) > 10):
            print(f"💎 ELITE VIP (BACKUP): {nome_vip}")
            return executar_proxy(url_vip)

    return "Não encontrado", 404

@app.route("/")
def index():
    return "🚀 Motor Cine Mega Híbrido v4 - Ajustado!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
