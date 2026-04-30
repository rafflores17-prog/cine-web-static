import os, random, requests, unicodedata, re, time
from flask import Flask, request, Response, stream_with_context, redirect

app = Flask(__name__)

# FONTES ATUALIZADAS - FOCO NA ESTABILIDADE
FONTES = {
    "1": {"host": "http://serv99.xyz:8880", "user": "1764371", "pass": "2419902"},
    "2": {"host": "http://nxpanelxr51.info", "user": "sandroalvares2", "pass": "T9er2T"}
}

BOTS_PROIBIDOS = ["mj12bot", "ahrefsbot", "dotbot", "semrushbot", "googlebot"]
cache_links = {}

def limpar_extremo(txt):
    if not txt: return ""
    # Remove TUDO que não é letra ou número (incluindo espaços e acentos)
    txt = re.sub(r'\(\d{4}\)', '', str(txt))
    txt = ''.join(c for c in unicodedata.normalize('NFD', txt) if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9]', '', txt.lower())

@app.route("/play")
def play():
    ua = request.headers.get('User-Agent', '').lower()
    if any(bot in ua for bot in BOTS_PROIBIDOS): return "Bot Block", 403

    titulo = request.args.get("titulo")
    # Se não vier fonte, ou se a fonte 2 falhar, o sistema pode tentar a 1 automaticamente
    fonte_id = request.args.get("fonte", "1")
    
    alvo = limpar_extremo(titulo)
    chave_cache = f"{alvo}_{fonte_id}"
    
    if chave_cache in cache_links:
        timestamp, link_salvo = cache_links[chave_cache]
        if time.time() - timestamp < 3600: # 1 hora de cache (Mais fôlego)
            return redirect(link_salvo)

    srv = FONTES.get(fonte_id)
    try:
        url_api = f"{srv['host']}/player_api.php?username={srv['user']}&password={srv['pass']}&action=get_vod_streams"
        # Timeout aumentado para 8 segundos para dar chance da API responder
        r = requests.get(url_api, timeout=8)
        dados = r.json()
        
        for item in dados:
            nome_api = limpar_extremo(item.get('name', ''))
            # BUSCA TOTAL: Se o que você quer está no nome, ou o nome está no que você quer
            if alvo in nome_api or nome_api in alvo:
                v_url = f"{srv['host']}/movie/{srv['user']}/{srv['pass']}/{item.get('stream_id')}.mp4"
                cache_links[chave_cache] = (time.time(), v_url)
                return redirect(v_url)
    except:
        pass
    
    return "Nao encontrado", 404

@app.route("/")
def index():
    return "Cine Mega v51 - Sistema Online"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)), threaded=True)
