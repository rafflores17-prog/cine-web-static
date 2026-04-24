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
# ROTAS DO PWA 
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
# ROTA DE VERIFICAÇÃO DO APLICATIVO (APK) COM NOVA CHAVE
# ==========================================
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

# ==========================================
# LÓGICA DO SITE E BUSCA DE TRAILER
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
    # Puxa o filme e a lista de vídeos
    f_url = f"https://api.themoviedb.org/3/movie/{id}?api_key={TMDB_API_KEY}&language=pt-BR&append_to_response=videos"
    f_data = requests.get(f_url).json()
    play_link = buscar_no_iptv(f_data.get('title', ''))
    
    # Extrai a chave do trailer do YouTube (se existir)
    trailer_key = None
    if 'videos' in f_data and 'results' in f_data['videos']:
        for v in f_data['videos']['results']:
            if v['type'] == 'Trailer' and v['site'] == 'YouTube':
                trailer_key = v['key']
                break

    return render_template("detalhes.html", filme=f_data, img=IMG, bg=BG, play_link=play_link, nome_site=NOME_SITE, trailer_key=trailer_key)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
