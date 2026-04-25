from flask import Flask, render_template, request, send_from_directory, jsonify, Response, stream_with_context
import requests
import re
import os

app = Flask(__name__)

NOME_SITE = "Cine Mega"
SITE_URL = "https://www.cinemega.online"
TMDB_API_KEY = "c90fb79a2f7d756a49bee848bce5f413"
IMG = "https://image.tmdb.org/t/p/w500"
BG = "https://image.tmdb.org/t/p/original"

# ✅ CREDENCIAIS ATUALIZADAS (Serv99 modificado)
SERVIDORES = [
    {"host": "http://serv99.xyz:8880", "user": "1764371", "pass": "2419902"},
    {"host": "http://falcon12.top:80", "user": "175473583", "pass": "643238922"},
    {"host": "http://stmax.top:80", "user": "lucas6043", "pass": "px2926br"},
    {"host": "http://koquwz.com:80", "user": "471204", "pass": "epp4Jx"},
    {"host": "http://techon.one:80", "user": "003008", "pass": "440144634"}
]

# ================================
# CACHE INTELIGENTE
# ================================
@app.after_request
def add_cache_headers(response):
    if request.path.endswith((".js", ".css", ".png", ".jpg", ".jpeg", ".webp", ".svg")):
        response.headers["Cache-Control"] = "public, max-age=86400"
    else:
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return response

@app.route('/sw.js')
def sw():
    return send_from_directory('.', 'sw.js', mimetype='application/javascript')

@app.route("/health")
def health():
    return "OK"

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

# ================================
# PROXY DE VÍDEO (A MÁGICA ACONTECE AQUI)
# ================================
@app.route("/proxy")
def proxy_video():
    url = request.args.get("url")
    if not url:
        return "URL não fornecida", 400

    try:
        # 🕵️‍♂️ DISFARCE: Usando o exato User-Agent do seu print!
        headers = {
            "User-Agent": "EPPIPROPLAYER/1.0.8 (Linux;Android 14) AndroidXMedia3/1.5.1",
            "Accept": "*/*",
            "Connection": "keep-alive"
        }

        # Repassa o comando de "Avançar filme" (Range) se o player pedir
        range_header = request.headers.get('Range', None)
        if range_header:
            headers['Range'] = range_header

        # allow_redirects=True resolve o problema do "token" dinâmico
        r = requests.get(url, headers=headers, stream=True, timeout=(5, 15), allow_redirects=True)

        status_code = r.status_code
        if status_code not in (200, 206):
            return "Servidor de vídeo indisponível", 502

        def generate():
            try:
                for chunk in r.iter_content(1024 * 64):
                    if chunk: yield chunk
            finally:
                r.close()

        # Cabeçalhos de resposta exigidos pelos players nativos (UC/Chrome)
        resp_headers = {
            "Accept-Ranges": "bytes",
            "Cache-Control": "no-store",
            "Connection": "keep-alive"
        }
        
        # Se o servidor devolver o tamanho do vídeo, repassamos pro navegador
        if 'Content-Range' in r.headers:
            resp_headers['Content-Range'] = r.headers['Content-Range']
        if 'Content-Length' in r.headers:
            resp_headers['Content-Length'] = r.headers['Content-Length']

        return Response(
            stream_with_context(generate()),
            status=status_code,
            content_type=r.headers.get("Content-Type", "video/mp4"),
            headers=resp_headers
        )

    except Exception as e:
        print("Erro proxy:", e)
        return "Erro ao carregar vídeo", 500

# ================================
# BUSCAR FILME IPTV
# ================================
def buscar_no_iptv(titulo):
    titulo_busca = re.sub(r'[^\w\s]', '', titulo).lower().strip()
    
    for srv in SERVIDORES:
        url_api = f"{srv['host']}/player_api.php?username={srv['user']}&password={srv['pass']}&action=get_vod_streams"
        
        try:
            r = requests.get(url_api, timeout=10)
            if r.status_code != 200: continue
            
            for item in r.json():
                nome_iptv = re.sub(r'[^\w\s]', '', item.get('name', '')).lower()
                if titulo_busca in nome_iptv:
                    video_url = f"{srv['host']}/movie/{srv['user']}/{srv['pass']}/{item.get('stream_id')}.mp4"
                    return f"/proxy?url={video_url}"
        except Exception as e:
            print("Erro IPTV:", e)
            continue
    return None

# ================================
# ROTAS HOME E DETALHES
# ================================
@app.route("/")
def home():
    q = request.args.get("q")
    if q:
        url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&language=pt-BR&query={q}"
    else:
        url = f"https://api.themoviedb.org/3/movie/popular?api_key={TMDB_API_KEY}&language=pt-BR"
    
    res = requests.get(url, timeout=10).json().get("results", [])
    return render_template("index.html", filmes=res[:20], img=IMG, nome_site=NOME_SITE)

@app.route("/filme/<int:id>")
def detalhes(id):
    data = requests.get(f"https://api.themoviedb.org/3/movie/{id}?api_key={TMDB_API_KEY}&language=pt-BR&append_to_response=videos", timeout=10).json()
    play_link = buscar_no_iptv(data.get('title', ''))
    
    trailer = next((v['key'] for v in data.get('videos', {}).get('results', []) if v['type'] == 'Trailer'), None)
    
    return render_template("detalhes.html", filme=data, img=IMG, bg=BG, play_link=play_link, nome_site=NOME_SITE, trailer_key=trailer)

if __name__ == "__main__":
    PORT = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=PORT)
