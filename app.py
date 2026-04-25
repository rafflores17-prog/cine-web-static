from flask import Flask, render_template, request, send_from_directory, jsonify, make_response
import requests
import re

app = Flask(__name__)

NOME_SITE = "Cine Mega"
SITE_URL = "https://www.cinemega.online"
TMDB_API_KEY = "c90fb79a2f7d756a49bee848bce5f413"
IMG = "https://image.tmdb.org/t/p/w500"
BG = "https://image.tmdb.org/t/p/original"

SERVIDORES = [
    {"host": "http://serv99.xyz:8880", "user": "261491762", "pass": "2516895925"},
    {"host": "http://stmax.top:80", "user": "lucas6043", "pass": "px2926br"},
    {"host": "http://koquwz.com:80", "user": "471204", "pass": "epp4Jx"},
    {"host": "http://techon.one:80", "user": "003008", "pass": "440144634"}
]

@app.route('/sw.js')
def sw(): return send_from_directory('.', 'sw.js', mimetype='application/javascript')

@app.route('/sitemap.xml')
def sitemap():
    pages = [[f"{SITE_URL}/", "1.0"]]
    return make_response(render_template('sitemap_template.xml', pages=pages), 200, {'Content-Type': 'application/xml'})

def buscar_no_iptv(titulo, tipo="movie"):
    titulo_busca = re.sub(r'[^\w\s]', '', titulo).lower().strip()
    acao = "get_vod_streams" if tipo == "movie" else "get_series"
    
    for srv in SERVIDORES:
        url_api = f"{srv['host']}/player_api.php?username={srv['user']}&password={srv['pass']}&action={acao}"
        try:
            r = requests.get(url_api, timeout=5)
            for item in r.json():
                nome_iptv = re.sub(r'[^\w\s]', '', item.get('name', '')).lower()
                if titulo_busca in nome_iptv:
                    sid = item.get('stream_id') if tipo == "movie" else item.get('series_id')
                    # Link direto que o VLC/MX Player reconhecem na hora
                    return f"{srv['host']}/{'movie' if tipo=='movie' else 'series'}/{srv['user']}/{srv['pass']}/{sid}.mp4"
        except: continue
    return None

@app.route("/")
def home():
    q = request.args.get("q")
    url = f"https://api.themoviedb.org/3/{'search/multi' if q else 'trending/all/week'}?api_key={TMDB_API_KEY}&language=pt-BR{f'&query={q}' if q else ''}"
    res = requests.get(url).json().get("results", [])
    return render_template("index.html", filmes=res[:24], img=IMG, nome_site=NOME_SITE)

@app.route("/filme/<int:id>")
@app.route("/serie/<int:id>")
def detalhes(id):
    tipo = "movie" if "filme" in request.path else "tv"
    data = requests.get(f"https://api.themoviedb.org/3/{tipo}/{id}?api_key={TMDB_API_KEY}&language=pt-BR&append_to_response=videos").json()
    titulo = data.get('title') or data.get('name')
    play_link = buscar_no_iptv(titulo, "movie" if tipo=="movie" else "series")
    
    trailer = next((v['key'] for v in data.get('videos', {}).get('results', []) if v['type'] == 'Trailer'), None)
    return render_template("detalhes.html", filme=data, img=IMG, bg=BG, play_link=play_link, nome_site=NOME_SITE, trailer_key=trailer)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
