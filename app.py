from flask import Flask, request, Response, stream_with_context, redirect
import requests
import os
import re
import unicodedata
import random

app = Flask(__name__)

# Cache para não ler o arquivo TXT toda hora (ganha velocidade)
ACERVO_CACHE = {}

def limpar_pro(txt):
    if not txt: return ""
    # Normaliza e deixa apenas letras e números, sem espaços
    txt = ''.join(c for c in unicodedata.normalize('NFD', str(txt)) if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9]', '', txt.lower())

def executar_proxy(url_video):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Connection": "keep-alive"
    }
    try:
        r = requests.get(url_video, headers=headers, stream=True, timeout=(10, 300), allow_redirects=True)
        def generate():
            for chunk in r.iter_content(chunk_size=1024*256):
                yield chunk
        resp = Response(stream_with_context(generate()), status=r.status_code)
        resp.headers["Content-Type"] = "video/mp4"
        resp.headers["Accept-Ranges"] = "bytes"
        resp.headers["Access-Control-Allow-Origin"] = "*"
        return resp
    except:
        return redirect(url_video)

@app.route("/buscar", methods=['GET', 'HEAD'])
def buscar():
    titulo = request.args.get("titulo")
    if not titulo: return "Vazio", 400
    
    t_alvo = limpar_pro(titulo)
    print(f"🎯 Mestre, Alvo: {t_alvo}")

    # --- LÓGICA DE BUSCA DE PRECISÃO ---
    melhor_match = None
    
    for arq in ["vips.txt", "filmes_site.txt"]:
        if os.path.exists(arq):
            with open(arq, "r", encoding="utf-8", errors="ignore") as f:
                for linha in f:
                    if "|" in linha:
                        partes = linha.split("|")
                        nome_txt = partes[0].strip()
                        url_txt = partes[1].strip()
                        nome_limpo = limpar_pro(nome_txt)
                        
                        # 1. Se for IDENTICO, para tudo e dá o play (Resolve o Jumanji/Pie)
                        if t_alvo == nome_limpo:
                            return executar_proxy(url_txt)
                        
                        # 2. Guarda o que começa com o nome (fallback seguro)
                        if nome_limpo.startswith(t_alvo) and melhor_match is None:
                            melhor_match = url_txt

    # Se não achou identico, vai no melhor aproximado
    if melhor_match:
        return executar_proxy(melhor_match)

    # --- BUSCA IPTV (serv99) ---
    try:
        url_api = f"http://serv99.xyz:8880/player_api.php?username=261491762&password=2516895925&action=get_vod_streams"
        res_api = requests.get(url_api, timeout=5).json()
        for item in res_api:
            nome_api = limpar_pro(item.get('name', ''))
            if t_alvo == nome_api:
                v_url = f"http://serv99.xyz:8880/movie/261491762/2516895925/{item.get('stream_id')}.mp4"
                return executar_proxy(v_url)
    except: pass

    return "Não encontrado", 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
