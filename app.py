from flask import Flask, request, Response, stream_with_context, redirect
import requests
import sqlite3
import random
import os
import unicodedata
import re

app = Flask(__name__)

# 🚀 AGENTES DE ELITE
AGENTES_VIP = [
    "EPPIPROPLAYER/1.0.8 (Linux;Android 14) AndroidXMedia3/1.5.1",
    "purpleplayer/1.2.82",
    "Dalvik/2.1.0 (Linux; U; Android 14; 2312FPCA6G Build/UP1A.231005.007)",
    "VLC/3.0.4 LibVLC/3.0.4",
    "Dart/3.9 (dart:io)",
    "okhttp/4.12.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36"
]

SERVIDORES_API = [
    {"nome": "Cinevexio", "host": "http://cinevexio.top:80", "user": "175473583", "pass": "643238922"},
    {"nome": "Stmax", "host": "http://stmax.top:80", "user": "lucas6043", "pass": "px2926br"}
]

# 🔥 A MÁGICA DO MESTRE: Limpa o texto para a busca não falhar por causa de acentos
def limpar_texto(texto):
    if not texto: return ""
    texto = ''.join(c for c in unicodedata.normalize('NFD', str(texto)) if unicodedata.category(c) != 'Mn')
    texto = re.sub(r'[^a-zA-Z0-9\s]', ' ', texto)
    return re.sub(r'\s+', ' ', texto).strip().lower()

def ler_txt(caminho):
    """Lê arquivos TXT e já limpa os nomes na memória para busca ultra rápida"""
    acervo = {}
    if os.path.exists(caminho):
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                for linha in f:
                    if "|" in linha:
                        n, u = linha.split("|", 1)
                        acervo[limpar_texto(n)] = u.strip()
        except Exception as e: 
            pass
    return acervo

def executar_proxy(url_video):
    if "archive.org" in url_video.lower():
        return redirect(url_video, code=302)

    agente = random.choice(AGENTES_VIP)
    headers = {
        "User-Agent": agente,
        "Accept": "video/webm,video/ogg,video/*;q=0.9,application/ogg;q=0.7,audio/*;q=0.6,*/*;q=0.5",
        "Connection": "keep-alive",
        "Icy-MetaData": "1"
    }
    
    range_header = request.headers.get('Range', None)
    if range_header: headers['Range'] = range_header

    try:
        r = requests.get(url_video, headers=headers, stream=True, timeout=(10, 120), allow_redirects=True)
        def generate():
            for chunk in r.iter_content(chunk_size=256 * 1024):
                if chunk: yield chunk
        
        resp_headers = {
            "Accept-Ranges": "bytes",
            "Access-Control-Allow-Origin": "*",
            "Content-Type": "video/mp4",
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "no-cache"
        }
        if 'Content-Range' in r.headers: resp_headers['Content-Range'] = r.headers['Content-Range']
        if 'Content-Length' in r.headers: resp_headers['Content-Length'] = r.headers['Content-Length']
        
        return Response(stream_with_context(generate()), status=r.status_code, headers=resp_headers)
    except Exception as e:
        return redirect(url_video.replace("http://", "https://"))

@app.route("/buscar")
def buscar():
    titulo = request.args.get("titulo")
    if not titulo: return "Título vazio", 400
    
    t_limpo = limpar_texto(titulo)

    # 🥇 1º LUGAR: SEU VIP (Busca Direta Instantânea)
    VIP = ler_txt("vips.txt")
    if t_limpo in VIP:
        print(f"💎 VIP ENCONTRADO: {t_limpo}")
        return executar_proxy(VIP[t_limpo])

    # 🥈 2º LUGAR: FILMES_SITE.TXT (Busca Direta Instantânea)
    GIGANTE = ler_txt("filmes_site.txt")
    if t_limpo in GIGANTE:
        print(f"🚀 GIGANTE ENCONTRADO: {t_limpo}")
        return executar_proxy(GIGANTE[t_limpo])

    # 🥉 3º LUGAR: BANCO DE DADOS LOCAL
    try:
        if os.path.exists('filmes.db'):
            conn = sqlite3.connect('filmes.db')
            c = conn.cursor()
            
            try:
                # Busca pelo search_name exato ou parecido
                c.execute("""
                    SELECT url FROM playlist 
                    WHERE LOWER(search_name) LIKE ? 
                    OR LOWER(name) LIKE ? 
                    LIMIT 1
                """, (f"%{t_limpo}%", f"%{t_limpo}%"))
            except sqlite3.OperationalError:
                c.execute("SELECT url FROM playlist WHERE LOWER(name) LIKE ? LIMIT 1", (f"%{t_limpo}%",))
                
            res = c.fetchone()
            conn.close()
            if res: 
                print(f"💾 DB ENCONTRADO: {t_limpo}")
                return executar_proxy(res[0])
    except Exception as e: 
        print(f"Erro no DB local: {e}")

    # 🏅 4º LUGAR: APIs EXTERNAS
    for srv in SERVIDORES_API:
        try:
            url_api = f"{srv['host']}/player_api.php?username={srv['user']}&password={srv['pass']}&action=get_vod_streams"
            r = requests.get(url_api, timeout=4).json()
            for item in r:
                nome_api = limpar_texto(item.get('name', ''))
                if t_limpo == nome_api:
                    v_url = f"{srv['host']}/movie/{srv['user']}/{srv['pass']}/{item.get('stream_id')}.mp4"
                    return executar_proxy(v_url)
        except: continue

    return "Filme não encontrado nas bases de dados", 404

@app.route("/")
def index():
    return "🚀 Motor Cine Mega Híbrido DB - Corrigido e Ultra Rápido!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
