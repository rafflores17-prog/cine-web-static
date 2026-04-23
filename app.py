from flask import Flask, render_template, request
import requests
import random
import re

app = Flask(__name__)

# Configurações do Projeto
NOME_SITE = "Cine Mega"
TMDB_API_KEY = "c90fb79a2f7d756a49bee848bce5f413"
IMG = "https://image.tmdb.org/t/p/w500"
BG = "https://image.tmdb.org/t/p/original"

# 📺 SERVIDORES VIP XTREAM
SERVIDORES = [
    {"host": "http://serv99.xyz:8880", "user": "261491762", "pass": "2516895925"},
    {"host": "http://stmax.top:80", "user": "lucas6043", "pass": "px2926br"},
    {"host": "http://koquwz.com:80", "user": "471204", "pass": "epp4Jx"},
    {"host": "http://koquwz.com:80", "user": "douglas20102010", "pass": "Ss12345678"},
    {"host": "http://techon.one:80", "user": "003008", "pass": "440144634"},
    {"host": "http://sventank.com:80", "user": "123456", "pass": "654321"}
]

def buscar_no_iptv(titulo_filme):
    titulo_busca = re.sub(r'[^\w\s]', '', titulo_filme).lower().strip()
    for srv in SERVIDORES:
        url_api = f"{srv['host']}/player_api.php?username={srv['user']}&password={srv['pass']}&action=get_vod_streams"
        try:
            r = requests.get(url_api, timeout=5)
            lista_vod = r.json()
            for item in lista_vod:
                nome_iptv = re.sub(r'[^\w\s]', '', item.get('name', '')).lower()
                if titulo_busca == nome_iptv or (titulo_busca in nome_iptv and len(nome_iptv) < len(titulo_busca) + 12):
                    stream_id = item.get('stream_id')
                    return f"{srv['host']}/movie/{srv['user']}/{srv['pass']}/{stream_id}.mp4"
        except: continue
    return None

def tmdb(endpoint, params=None):
    if params is None: params = {}
    url = f"https://api.themoviedb.org/3/{endpoint}"
    params.update({"api_key": TMDB_API_KEY, "language": "pt-BR"})
    try: return requests.get(url, params=params, timeout=10).json()
    except: return {}

@app.route("/")
def home():
    query = request.args.get("q")
    if query:
        filmes = tmdb("search/movie", {"query": query}).get("results", [])
    else:
        p, t, tr = tmdb("movie/popular").get("results", []), tmdb("movie/top_rated").get("results", []), tmdb("trending/movie/week").get("results", [])
        vistos, mistura = set(), []
        for f in (p + t + tr):
            if f['id'] not in vistos:
                mistura.append(f); vistos.add(f['id'])
        random.shuffle(mistura)
        filmes = mistura[:20]
    return render_template("index.html", filmes=filmes, img=IMG, nome_site=NOME_SITE)

@app.route("/filme/<int:id>")
def filme(id):
    f_data = tmdb(f"movie/{id}")
    play_link = buscar_no_iptv(f_data.get('title', ''))
    videos = tmdb(f"movie/{id}/videos").get("results", [])
    trailer = next((v['key'] for v in videos if v['type'] == 'Trailer' and v['site'] == 'YouTube'), None)
    return render_template("detalhes.html", filme=f_data, img=IMG, bg=BG, trailer=trailer, play_link=play_link, nome_site=NOME_SITE)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
