from flask import Flask, request, Response, stream_with_context
import requests
import sqlite3
import random
import os

app = Flask(__name__)

# Agentes de usuário para evitar bloqueios
AGENTES_VIP = [
    "EPPIPROPLAYER/1.0.8 (Linux;Android 14) AndroidXMedia3/1.5.1",
    "purpleplayer/1.2.82",
    "Dalvik/2.1.0 (Linux; U; Android 14; 2312FPCA6G Build/UP1A.231005.007)"
]

# Servidores de Backup (IPTV)
SERVIDORES_API = [
    {"nome": "Cinevexio", "host": "http://cinevexio.top:80", "user": "175473583", "pass": "643238922"},
    {"nome": "Stmax", "host": "http://stmax.top:80", "user": "lucas6043", "pass": "px2926br"}
]

def carregar_vips_dinamicamente():
    """Lê o arquivo vips.txt na raiz do projeto e retorna um dicionário"""
    vips = {}
    caminho = "vips.txt"
    if os.path.exists(caminho):
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                for linha in f:
                    if "|" in linha:
                        nome, url = linha.split("|")
                        vips[nome.strip().lower()] = url.strip()
        except Exception as e:
            print(f"Erro ao ler vips.txt: {e}")
    return vips

@app.route("/buscar")
def buscar_e_proxy():
    titulo = request.args.get("titulo")
    if not titulo: return "Título vazio", 400

    titulo_limpo = titulo.strip().lower()

    # 🚀 1º PASSO: BUSCA NO SEU ACERVO DE ELITE (vips.txt)
    acervo_elite = carregar_vips_dinamicamente()
    for nome_vip, url_vip in acervo_elite.items():
        if nome_vip in titulo_limpo:
            print(f"💎 ELITE: Entregando {nome_vip} via vips.txt")
            return executar_proxy(url_vip)

    # 🔍 2º PASSO: BUSCA NO BANCO DE DADOS LOCAL (filmes.db)
    try:
        conn = sqlite3.connect('filmes.db')
        c = conn.cursor()
        palavras = titulo_limpo.split()
        termo_base = palavras[0] if len(palavras) == 1 else " ".join(palavras[:2])
        
        # Busca o mais próximo do título solicitado
        c.execute("SELECT url FROM playlist WHERE nome LIKE ? LIMIT 1", (f"%{termo_base}%",))
        resultado = c.fetchone()
        conn.close()

        if resultado:
            return executar_proxy(resultado[0])
        
        # 🔍 3º PASSO: BUSCA NAS APIs IPTV (Último recurso)
        for srv in SERVIDORES_API:
            try:
                url_api = f"{srv['host']}/player_api.php?username={srv['user']}&password={srv['pass']}&action=get_vod_streams"
                r = requests.get(url_api, timeout=4).json()
                for item in r:
                    if titulo_limpo in item.get('name', '').lower():
                        v_url = f"{srv['host']}/movie/{srv['user']}/{srv['pass']}/{item.get('stream_id')}.mp4"
                        return executar_proxy(v_url)
            except: continue

        return "Filme não encontrado", 404
    except Exception as e: return str(e), 500

def executar_proxy(url_video):
    """Executa o streaming do vídeo via proxy para o player"""
    agente = random.choice(AGENTES_VIP)
    headers = {
        "User-Agent": agente,
        "Accept": "*/*",
        "Connection": "keep-alive"
    }
    
    # Suporte a Range (importante para o player do Chrome)
    range_header = request.headers.get('Range', None)
    if range_header: headers['Range'] = range_header

    try:
        r = requests.get(url_video, headers=headers, stream=True, timeout=(5, 120), allow_redirects=True)
        
        def generate():
            for chunk in r.iter_content(chunk_size=512 * 1024):
                if chunk: yield chunk
        
        resp_headers = {
            "Accept-Ranges": "bytes",
            "Access-Control-Allow-Origin": "*",
            "Content-Type": r.headers.get("Content-Type", "video/mp4")
        }
        if 'Content-Range' in r.headers: resp_headers['Content-Range'] = r.headers['Content-Range']
        if 'Content-Length' in r.headers: resp_headers['Content-Length'] = r.headers['Content-Length']

        return Response(stream_with_context(generate()), status=r.status_code, headers=resp_headers)
    except: return "Erro no streaming", 500

if __name__ == "__main__":
    # Porta padrão para o Koyeb
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
