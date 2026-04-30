import os, random, requests, unicodedata, re, time
from flask import Flask, request, Response, stream_with_context, redirect

app = Flask(__name__)

# --- FONTES ATUALIZADAS (Removi a F2 que estava dando erro) ---
FONTES = {
    "1": {"nome": "Servidor 99", "host": "http://serv99.xyz:8880", "user": "1764371", "pass": "2419902"},
    "2": {"nome": "New Gold", "host": "http://gold.pjt.bz:80", "user": "58257413", "pass": "19193442"} 
}

BOTS_PROIBIDOS = ["mj12bot", "ahrefsbot", "dotbot", "semrushbot", "googlebot", "bingbot", "crawler", "spider", "python-requests"]

cache_links = {}

def limpar_busca(txt):
    if not txt: return ""
    txt = re.sub(r'\(\d{4}\)', '', str(txt))
    txt = ''.join(c for c in unicodedata.normalize('NFD', txt) if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9]', '', txt.lower())

@app.route("/play")
def play():
    ua = request.headers.get('User-Agent', '').lower()
    if any(bot in ua for bot in BOTS_PROIBIDOS):
        return "Acesso negado", 403

    titulo = request.args.get("titulo")
    fonte_id = request.args.get("fonte", "1")
    if not titulo: return "Vazio", 400
    
    alvo = limpar_busca(titulo)
    chave_cache = f"{alvo}_{fonte_id}"
    
    if chave_cache in cache_links:
        timestamp, link_salvo = cache_links[chave_cache]
        if time.time() - timestamp < 1800: # Cache subiu para 30 min (Mais folga pra CPU)
            return redirect(link_salvo)

    srv = FONTES.get(fonte_id)
    if not srv: return "Fonte OFF", 404

    try:
        url_api = f"{srv['host']}/player_api.php?username={srv['user']}&password={srv['pass']}&action=get_vod_streams"
        r = requests.get(url_api, timeout=(2, 5))
        dados = r.json()
        
        for item in dados:
            nome_api = limpar_busca(item.get('name', ''))
            # Busca por "contém" para ser mais flexível, mas salva no cache para não repetir
            if alvo in nome_api:
                v_url = f"{srv['host']}/movie/{srv['user']}/{srv['pass']}/{item.get('stream_id')}.mp4"
                cache_links[chave_cache] = (time.time(), v_url)
                return redirect(v_url)
    except: pass
    
    return "Nao encontrado", 404

@app.route("/")
def index():
    return "Cine Mega v50 - Estabilidade Total"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, threaded=True)
