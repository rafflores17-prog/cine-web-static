from flask import Flask, render_template, request, send_from_directory, jsonify
import requests
import random
import re

app = Flask(__name__)

NOME_SITE = "Cine Mega"
TMDB_API_KEY = "c90fb79a2f7d756a49bee848bce5f413"
IMG = "https://image.tmdb.org/t/p/w500"
BG = "https://image.tmdb.org/t/p/original"

SERVIDORES = [
    {"host": "http://serv99.xyz:8880", "user": "261491762", "pass": "2516895925"},
    {"host": "http://stmax.top:80", "user": "lucas6043", "pass": "px2926br"},
    {"host": "http://koquwz.com:80", "user": "471204", "pass": "epp4Jx"},
    {"host": "http://koquwz.com:80", "user": "douglas20102010", "pass": "Ss12345678"},
    {"host": "http://techon.one:80", "user": "003008", "pass": "440144634"},
    {"host": "http://sventank.com:80", "user": "123456", "pass": "654321"}
]

# ==========================================
# ROTAS DO PWA (Enganando o cache do PWABuilder)
# ==========================================
@app.route('/static/manifest.json')
def manifest_static():
    return send_from_directory('.', 'manifest.json', mimetype='application/manifest+json')

@app.route('/static/icon-192.png')
def icon192_static():
    return send_from_directory('.', 'icon-192.png', mimetype='image/png')

@app.route('/static/icon-512.png')
def icon512_static():
    return send_from_directory('.', 'icon-512.png', mimetype='image/png')

@app.route('/sw.js')
def sw():
    return send_from_directory('.', 'sw.js', mimetype='application/javascript')
# ==========================================

def buscar_no_iptv(titulo_filme):
    titulo_busca = re.sub(r'[^\w\s]', '', titulo_filme).lower().strip()
    for srv in SERVIDORES:
        url_api = f"{srv['host']}/player_api.php?username={srv['user']}&password={srv['pass']}&action=get_vod_streams"
        try:
            r = requests.get(url_api, timeout=4)
            dados = r.json()
            for item in dados:
                nome_iptv = re.sub(r'[^\w\s]', '', item.get('name', '')).lower()
                if titulo_busca in nome_iptv:
                    stream_id = item.get('stream_id')
                    return f"{srv['host']}/movie/{srv['user']}/{srv['pass']}/{stream_id}.mp4"
        except: continue
    return None

@app.route("/")
def home():
    query = request.args.get("q")
    if query:
        url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&language=pt-BR&query={query}"
        filmes = requests.get(url).json().get("results", [])
    else:
        url = f"https://api.themoviedb.org/3/movie/popular?api_key={TMDB_API_KEY}&language=pt-BR"
        filmes = requests.get(url).json().get("results", [])
        random.shuffle(filmes)
    return render_template("index.html", filmes=filmes[:20], img=IMG, nome_site=NOME_SITE)

@app.route("/filme/<int:id>")
def filme(id):
    f_url = f"https://api.themoviedb.org/3/movie/{id}?api_key={TMDB_API_KEY}&language=pt-BR"
    f_data = requests.get(f_url).json()
    play_link = buscar_no_iptv(f_data.get('title', ''))
    return render_template("detalhes.html", filme=f_data, img=IMG, bg=BG, play_link=play_link, nome_site=NOME_SITE)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
