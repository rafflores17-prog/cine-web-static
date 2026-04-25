from flask import Flask, render_template, request, send_from_directory, jsonify, make_response
import requests
import re

app = Flask(__name__)

NOME_SITE = "Cine Mega"
# Adicionei a SITE_URL para o sistema saber o domínio oficial
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

# ROTA PARA O SERVICE WORKER (PWA)
@app.route('/sw.js')
def sw(): return send_from_directory('.', 'sw.js', mimetype='application/javascript')

# 🛡️ ROTA DO ASSET LINKS (PARA SUMIR A BARRA DO APP)
@app.route('/.well-known/assetlinks.json')
def assetlinks():
    return jsonify([{
      "relation": ["delegate_permission/common.handle_all_urls"],
      "target": {
        "namespace": "android_app",
        "package_name": "online.cinemega.www.twa",
        "sha256_cert_fingerprints": ["64:F7:CE:80:D5:1C:79:CE:91:A7:0E:C8:BE:71:49:E6:46:64:F6:D2:96:5F:12:D6:8F:41:DC:57:A9:4E:48:CD"]
      }
    }])

def buscar_no_iptv(titulo):
    titulo_busca = re.sub(r'[^\w\s]', '', titulo).lower().strip()
    for srv in SERVIDORES:
        url_api = f"{srv['host']}/player_api.php?username={srv['user']}&password={srv['pass']}&action=get_vod_streams"
        try:
            r = requests.get(url_api, timeout=4)
            for item in r.json():
                nome_iptv = re.sub(r'[^\w\s]', '', item.get('name', '')).lower()
                if titulo_busca in nome_iptv:
                    return f"{srv['host']}/movie/{srv['user']}/{srv['pass']}/{item.get('stream_id')}.mp4"
        except: continue
    return None

@app.route("/")
def home():
    q = request.args.get("q")
    url = f"https://api.themoviedb.org/3/{'search/movie' if q else 'movie/popular'}?api_key={TMDB_API_KEY}&language=pt-BR{f'&query={q}' if q else ''}"
    res = requests.get(url).json().get("results", [])
    return render_template("index.html", filmes=res[:20], img=IMG, nome_site=NOME_SITE)

@app.route("/filme/<int:id>")
def detalhes(id):
    data = requests.get(f"https://api.themoviedb.org/3/movie/{id}?api_key={TMDB_API_KEY}&language=pt-BR&append_to_response=videos").json()
    play_link = buscar_no_iptv(data.get('title', ''))
    trailer = next((v['key'] for v in data.get('videos', {}).get('results', []) if v['type'] == 'Trailer'), None)
    return render_template("detalhes.html", filme=data, img=IMG, bg=BG, play_link=play_link, nome_site=NOME_SITE, trailer_key=trailer)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
