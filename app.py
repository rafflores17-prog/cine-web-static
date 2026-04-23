from flask import Flask, render_template, request
import requests
import random
import re

app = Flask(__name__)

# 🔑 CONFIGURAÇÕES
TMDB_API_KEY = "c90fb79a2f7d756a49bee848bce5f413"
IMG = "https://image.tmdb.org/t/p/w500"
BG = "https://image.tmdb.org/t/p/original"

# 📺 CREDENCIAIS XTREAM (Sua API VIP)
XTREAM_HOST = "http://serv99.xyz:8880"
XTREAM_USER = "261491762"
XTREAM_PASS = "2516895925"

# =========================
# MOTOR XTREAM CODES
# =========================
def buscar_no_iptv(titulo_filme):
    """Procura o filme no seu servidor de IPTV e retorna o link direto"""
    # 1. Endpoint para pegar todos os filmes (VOD)
    url_api = f"{XTREAM_HOST}/player_api.php?username={XTREAM_USER}&password={XTREAM_PASS}&action=get_vod_streams"
    
    try:
        # Limpamos o título para busca
        titulo_busca = re.sub(r'[^\w\s]', '', titulo_filme).lower()
        
        r = requests.get(url_api, timeout=10)
        lista_vod = r.json()

        for item in lista_vod:
            nome_iptv = item.get('name', '').lower()
            # Se o título do TMDB bater com o nome no IPTV
            if titulo_busca in nome_iptv:
                stream_id = item.get('stream_id')
                ext = item.get('container_extension', 'mp4')
                
                # Monta o link final que o player vai ler
                link_final = f"{XTREAM_HOST}/movie/{XTREAM_USER}/{XTREAM_PASS}/{stream_id}.{ext}"
                return link_final
    except:
        return None
    return None

# =========================
# FUNÇÃO TMDB
# =========================
def tmdb(endpoint, params=None):
    if params is None: params = {}
    url = f"https://api.themoviedb.org/3/{endpoint}"
    params["api_key"] = TMDB_API_KEY
    params["language"] = "pt-BR"
    try:
        r = requests.get(url, params=params, timeout=10)
        return r.json()
    except:
        return {}

# =========================
# HOME
# =========================
@app.route("/")
def home():
    query = request.args.get("q")
    if query:
        filmes = tmdb("search/movie", {"query": query}).get("results", [])
    else:
        populares = tmdb("movie/popular").get("results", [])
        top = tmdb("movie/top_rated").get("results", [])
        trending = tmdb("trending/movie/week").get("results", [])
        mistura = populares + top + trending
        random.shuffle(mistura)
        filmes = mistura[:20]

    return render_template("index.html", filmes=filmes, img=IMG)

# =========================
# DETALHES (COM PLAY DIRETO)
# =========================
@app.route("/filme/<int:id>")
def filme(id):
    # Pega dados do filme
    dados_filme = tmdb(f"movie/{id}")
    titulo = dados_filme.get('title')

    # 🚀 BUSCA O LINK NO SEU IPTV
    link_player = buscar_no_iptv(titulo)

    # Pega Trailer
    videos = tmdb(f"movie/{id}/videos").get("results", [])
    trailer = next((v.get('key') for v in videos if v.get('type') == 'Trailer' and v.get('site') == 'YouTube'), None)

    return render_template(
        "detalhes.html",
        filme=dados_filme,
        img=IMG,
        bg=BG,
        trailer=trailer,
        play_link=link_player # Envia o link do IPTV pro HTML
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
