from flask import Flask, request, Response, stream_with_context, redirect
import requests
import sqlite3
import random
import os

app = Flask(__name__)

# 🚀 AGENTES DE ELITE - Enganam o servidor IPTV dizendo que somos um App Real
AGENTES_VIP = [
    "EPPIPROPLAYER/1.0.8 (Linux;Android 14) AndroidXMedia3/1.5.1",
    "purpleplayer/1.2.82",
    "Dalvik/2.1.0 (Linux; U; Android 14; 2312FPCA6G Build/UP1A.231005.007)",
    "VLC/3.0.4 LibVLC/3.0.4",
    "Dart/3.9 (dart:io)",
    "okhttp/4.12.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36"
]

# 🛡️ SERVIDORES DE APOIO (Backup do Backup)
SERVIDORES_API = [
    {"nome": "Cinevexio", "host": "http://cinevexio.top:80", "user": "175473583", "pass": "643238922"},
    {"nome": "Stmax", "host": "http://stmax.top:80", "user": "lucas6043", "pass": "px2926br"}
]

def ler_txt(caminho):
    """Lê arquivos TXT e transforma em dicionário para busca ultra rápida"""
    acervo = {}
    if os.path.exists(caminho):
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                for linha in f:
                    if "|" in linha:
                        n, u = linha.split("|", 1)
                        acervo[n.strip().lower()] = u.strip()
        except: pass
    return acervo

def executar_proxy(url_video):
    """ Proxy Camaleão: Resolve o erro de 'Só Áudio' e protege o servidor contra quedas """
    
    # Regra de Ouro: Archive.org vai direto (Redirect) pois é HTTPS e rápido.
    if "archive.org" in url_video.lower():
        return redirect(url_video, code=302)

    agente = random.choice(AGENTES_VIP)
    
    # Cabeçalhos para enganar o servidor IPTV e forçar o Chrome a mostrar vídeo
    headers = {
        "User-Agent": agente,
        "Accept": "video/webm,video/ogg,video/*;q=0.9,application/ogg;q=0.7,audio/*;q=0.6,*/*;q=0.5",
        "Connection": "keep-alive",
        "Icy-MetaData": "1"
    }
    
    # Repassa a posição do vídeo (Range) para o usuário conseguir adiantar o filme
    range_header = request.headers.get('Range', None)
    if range_header:
        headers['Range'] = range_header

    try:
        # Timeout de 120s para o servidor IPTV não desistir de carregar
        r = requests.get(url_video, headers=headers, stream=True, timeout=(10, 120), allow_redirects=True)
        
        def generate():
            # Chunk de 256kb: O tamanho perfeito para o Chrome não travar
            for chunk in r.iter_content(chunk_size=256 * 1024):
                if chunk: yield chunk
        
        resp_headers = {
            "Accept-Ranges": "bytes",
            "Access-Control-Allow-Origin": "*",
            "Content-Type": "video/mp4", # Força o motor de vídeo do navegador
            "X-Content-Type-Options": "nosniff", # Impede o bug de carregar só áudio
            "Cache-Control": "no-cache"
        }
        
        # Repassa metadados do arquivo original para o player funcionar 100%
        if 'Content-Range' in r.headers: resp_headers['Content-Range'] = r.headers['Content-Range']
        if 'Content-Length' in r.headers: resp_headers['Content-Length'] = r.headers['Content-Length']
        
        return Response(stream_with_context(generate()), status=r.status_code, headers=resp_headers)
    except Exception as e:
        print(f"Erro no Proxy: {e}")
        # Tentativa final: Redirect se o Proxy falhar
        return redirect(url_video.replace("http://", "https://"))

@app.route("/buscar")
def buscar():
    titulo = request.args.get("titulo")
    if not titulo: return "Título vazio", 400
    
    t_limpo = titulo.strip().lower()

    # 🥇 1º LUGAR: SEU VIP (vips.txt) - Prioridade Máxima
    VIP = ler_txt("vips.txt")
    if t_limpo in VIP:
        print(f"💎 VIP ENCONTRADO: {t_limpo}")
        return executar_proxy(VIP[t_limpo])

    # 🥈 2º LUGAR: FILMES_SITE.TXT (O seu novo acervo gigante)
    GIGANTE = ler_txt("filmes_site.txt")
    if t_limpo in GIGANTE:
        print(f"🚀 GIGANTE ENCONTRADO: {t_limpo}")
        return executar_proxy(GIGANTE[t_limpo])

    # 🥉 3º LUGAR: BANCO DE DADOS LOCAL (filmes.db)
    try:
        if os.path.exists('filmes.db'):
            conn = sqlite3.connect('filmes.db')
            c = conn.cursor()
            c.execute("SELECT url FROM playlist WHERE nome LIKE ? LIMIT 1", (f"%{t_limpo}%",))
            res = c.fetchone()
            conn.close()
            if res: 
                print(f"💾 DB ENCONTRADO: {t_limpo}")
                return executar_proxy(res[0])
    except: pass

    # 🏅 4º LUGAR: APIs EXTERNAS (Cinevexio / Stmax)
    for srv in SERVIDORES_API:
        try:
            url_api = f"{srv['host']}/player_api.php?username={srv['user']}&password={srv['pass']}&action=get_vod_streams"
            r = requests.get(url_api, timeout=4).json()
            for item in r:
                if t_limpo == item.get('name', '').lower():
                    v_url = f"{srv['host']}/movie/{srv['user']}/{srv['pass']}/{item.get('stream_id')}.mp4"
                    print(f"📡 API {srv['nome']} ENCONTRADA")
                    return executar_proxy(v_url)
        except: continue

    return "Filme não encontrado nas bases de dados", 404

@app.route("/")
def index():
    return "🚀 Motor Cine Mega v7 Híbrido - Online e Operacional!"

if __name__ == "__main__":
    # Rodando na porta do Koyeb
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
