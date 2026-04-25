from flask import Flask, render_template, request, send_from_directory, jsonify, make_response
import requests
import random
import re

app = Flask(__name__)

# CONFIGURAÇÕES BÁSICAS
NOME_SITE = "Cine Mega"
SITE_URL = "https://www.cinemega.online"
TMDB_API_KEY = "c90fb79a2f7d756a49bee848bce5f413"
IMG = "https://image.tmdb.org/t/p/w500"
BG = "https://image.tmdb.org/t/p/original"

# SEUS SERVIDORES IPTV
SERVIDORES = [
    {"host": "http://serv99.xyz:8880", "user": "261491762", "pass": "2516895925"},
    {"host": "http://stmax.top:80", "user": "lucas6043", "pass": "px2926br"},
    {"host": "http://koquwz.com:80", "user": "471204", "pass": "epp4Jx"},
    {"host": "http://koquwz.com:80", "user": "douglas20102010", "pass": "Ss12345678"},
    {"host": "http://techon.one:80", "user": "003008", "pass": "440144634"},
    {"host": "http://sventank.com:80", "user": "123456", "pass": "654321"}
]

# ==========================================
# ROTAS DE ARQUIVOS, PWA E SEO
# ==========================================
@app.route('/static/manifest.json')
def manifest_static():
    return send_from_directory('.', 'manifest.json', mimetype='application/manifest+json')

@app.route('/sw.js')
def sw():
    return send_from_directory('.', 'sw.js', mimetype='application/javascript')

@app.route('/robots.txt')
def robots():
    return send_from_directory('.', 'robots.txt', mimetype='text/plain')

@app.route('/sitemap.xml', methods=['GET'])
def sitemap():
    """Sitemap dinâmico para o Google"""
    pages = [[f"{SITE_URL}/", "1.0"]]
    try:
        # Puxa tendências para o sitemap
        url = f"https://api.themoviedb.org/3/trending/all/week?api_key={TMDB_API_KEY}&language=pt-BR"
        items = requests.get(url, timeout=5).json().get("results", [])
        for i in items:
            tipo = "filme" if i.get('media_type') == 'movie' else "serie"
            pages.append([f"{SITE_URL}/{tipo}/{i['id']}", "0.8"])
    except: pass
    sitemap_xml = render_template('sitemap_template.xml', pages=pages)
    response = make_response(sitemap_xml)
    response.headers["Content-Type"] = "application/xml"
    return response

@app.route('/.well-known/assetlinks.json')
def assetlinks():
    """Verificação para o App Android (Custom Tabs)"""
    return jsonify([{
      "relation": ["delegate_permission/common.handle_all_urls"],
      "target": {
        "namespace": "android_app",
        "package_name": "online.cinemega.www.twa",
        "sha256_cert_fingerprints": ["64:F7:CE:80:D5:1C:79:CE:91:A7:0E:C8:BE:71:49:E6:46:64:F6:D2:96:5F:12:D6:8F:41:DC:57:A9:4E:48:CD"]
      }
    }])

# ==========================================
# LÓGICA DE BUSCA IPTV (FILMES + SÉRIES)
# ==========================================
def buscar_no_iptv(titulo, tipo="movie"):
    titulo_busca = re.sub(r'[^\w\s]', '', titulo).lower().strip()
    acao = "get_vod_streams" if tipo == "movie" else "get_series"
    
    for srv in SERVIDORES:
        url_api = f"{srv['host']}/player_api.php?username={srv['user']}&password={srv['pass']}&action={acao}"
        try:
            r = requests.get(url_api, timeout=4)
            dados = r.json()
            for item in dados:
                nome_iptv = re.sub(r'[^\w\s]', '', item.get('name', '')).lower()
                if titulo_busca in nome_iptv:
                    sid = item.get('stream_id') if tipo == "movie" else item.get('series_id')
                    # Links de séries variam, mas tentamos o padrão
                    return f"{srv['host']}/{tipo}/{srv['user']}/{srv['pass']}/{sid}.mp4"
        except: continue
    return None

# ==========================================
# ROTAS DO SITE (HOME E DETALHES)
# ==========================================
@app.route("/")
def home():
    query = request.args.get("q")
    if query:
        # Busca multi-resultados (Filmes e Séries)
        url = f"https://api.themoviedb.org/3/search/multi?api_key={TMDB_API_KEY}&language=pt-BR&query={query}"
    else:
        # Home com tendências da semana (Mistura Filmes e Séries)
        url = f"https://api.themoviedb.org/3/trending/all/week?api_key={TMDB_API_KEY}&language=pt-BR"
    
    res = requests.get(url).json().get("results", [])
    # Filtra para não aparecer pessoas, apenas filmes e séries
    resultados = [i for i in res if i.get('media_type') in ['movie', 'tv'] or not query]
    return render_template("index.html", filmes=resultados[:24], img=IMG, nome_site=NOME_SITE)

@app.route("/filme/<int:id>")
@app.route("/serie/<int:id>")
def detalhes(id):
    # Identifica o tipo pela URL
    tipo_tmdb = "movie" if "filme" in request.path else "tv"
    f_url = f"https://api.themoviedb.org/3/{tipo_tmdb}/{id}?api_key={TMDB_API_KEY}&language=pt-BR&append_to_response=videos"
    f_data = requests.get(f_url).json()
    
    # Define o título para busca (Filme usa 'title', Série usa 'name')
    titulo = f_data.get('title') if tipo_tmdb == "movie" else f_data.get('name')
    play_link = buscar_no_iptv(titulo, tipo_tmdb)
    
    # Extrai Trailer
    trailer_key = None
    if 'videos' in f_data and f_data['videos']['results']:
        for v in f_data['videos']['results']:
            if v['type'] == 'Trailer' and v['site'] == 'YouTube':
                trailer_key = v['key']; break

    return render_template("detalhes.html", filme=f_data, img=IMG, bg=BG, play_link=play_link, nome_site=NOME_SITE, trailer_key=trailer_key)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
