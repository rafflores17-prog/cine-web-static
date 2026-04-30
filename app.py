import os, random, requests, unicodedata, re, time
from flask import Flask, request, Response, stream_with_context, redirect

app = Flask(__name__)

# --- OS 2 QUERIDINHOS (DADOS REVISADOS) ---
FONTES = {
    "1": {"host": "http://serv99.xyz:8880", "user": "1764371", "pass": "2419902"},
    "2": {"host": "http://nxpanelxr51.info", "user": "sandroalvares2", "pass": "T9er2T"}
}

# 🛡️ LISTA NEGRA DE ROBÔS (Para parar o MJ12bot que está fritando sua CPU)
BOTS_PROIBIDOS = ["mj12bot", "ahrefsbot", "dotbot", "semrushbot", "googlebot", "bingbot", "crawler", "spider"]

# 🧠 CACHE PARA ECONOMIZAR API
cache_links = {}

def limpar_busca(txt):
    if not txt: return ""
    txt = re.sub(r'\(\d{4}\)', '', str(txt)) # Remove ano
    txt = ''.join(c for c in unicodedata.normalize('NFD', txt) if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9]', '', txt.lower())

@app.route("/play")
def play():
    # 1. BLOQUEIO DE ROBÔS
    ua = request.headers.get('User-Agent', '').lower()
    if any(bot in ua for bot in BOTS_PROIBIDOS):
        print(f"🚫 Bot Bloqueado: {ua}")
        return "Acesso negado para robôs", 403

    titulo = request.args.get("titulo")
    fonte_id = request.args.get("fonte", "1")
    if not titulo: return "Vazio", 400
    
    alvo = limpar_busca(titulo)
    chave_cache = f"{alvo}_{fonte_id}"
    
    # 2. VERIFICA CACHE
    if chave_cache in cache_links:
        timestamp, link_salvo = cache_links[chave_cache]
        if time.time() - timestamp < 600: # 10 minutos de cache
            return redirect(link_salvo)

    srv = FONTES.get(fonte_id)
    if not srv: return "Fonte OFF", 404

    print(f"🔍 Buscando Real: {alvo} na F{fonte_id}")

    try:
        url_api = f"{srv['host']}/player_api.php?username={srv['user']}&password={srv['pass']}&action=get_vod_streams"
        r = requests.get(url_api, timeout=(3, 7))
        dados = r.json()
        
        for item in dados:
            nome_api = limpar_busca(item.get('name', ''))
            
            # 🧠 BUSCA REFINADA (startswith): 
            # Evita que "O Pássaro Azul" ache filmes russos aleatórios.
            # O nome na API deve COMEÇAR com o que você buscou ou ser idêntico.
            if nome_api.startswith(alvo) or alvo == nome_api:
                v_url = f"{srv['host']}/movie/{srv['user']}/{srv['pass']}/{item.get('stream_id')}.mp4"
                cache_links[chave_cache] = (time.time(), v_url)
                print(f"✅ Achou: {item.get('name')}")
                return redirect(v_url)
    except Exception as e:
        print(f"❌ Erro F{fonte_id}: {e}")
    
    return "Nao encontrado", 404

@app.route("/")
def index():
    return "Cine Mega v49 - Escudo Anti-Bot Ativo"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, threaded=True)
