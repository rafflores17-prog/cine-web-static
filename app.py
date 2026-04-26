from flask import Flask, render_template, request, send_from_directory, jsonify, Response, stream_with_context
import requests
import re
import os
import random  # 🎲 IMPORTAMOS A ROLETA AQUI
import sqlite3 # 🗄️ IMPORTAMOS A BASE DE DADOS AQUI

app = Flask(__name__)

NOME_SITE = "Cine Mega"
SITE_URL = "https://www.cinemega.online"
TMDB_API_KEY = "c90fb79a2f7d756a49bee848bce5f413"
IMG = "https://image.tmdb.org/t/p/w500"
BG = "https://image.tmdb.org/t/p/original"

SERVIDORES = [
    {"host": "http://serv99.xyz:8880", "user": "1764371", "pass": "2419902"},
    {"host": "http://falcon12.top:80", "user": "175473583", "pass": "643238922"},
    {"host": "http://stmax.top:80", "user": "lucas6043", "pass": "px2926br"},
    {"host": "http://koquwz.com:80", "user": "471204", "pass": "epp4Jx"},
    {"host": "http://techon.one:80", "user": "003008", "pass": "440144634"}
]

# 🛡️ NOSSO ARSENAL DE DISFARCES VIP (Capturados por você!)
AGENTES_VIP = [
    "EPPIPROPLAYER/1.0.8 (Linux;Android 14) AndroidXMedia3/1.5.1",
    "purpleplayer/1.2.82",
    "Dalvik/2.1.0 (Linux; U; Android 14; 2312FPCA6G Build/UP1A.231005.007)",
    "Dart/3.11 (dart:io)"
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
# SEO (GOOGLE ROBOTS E SITEMAP)
# ================================
@app.route('/robots.txt')
def robots():
    conteudo = (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /static/\n"
        f"Sitemap: {SITE_URL}/sitemap.xml\n"
    )
    return Response(conteudo, mimetype="text/plain")

@app.route('/sitemap.xml')
def sitemap():
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <url>
        <loc>{SITE_URL}/</loc>
        <changefreq>hourly</changefreq>
        <priority>1.0</priority>
    </url>
</urlset>"""
    return Response(xml, mimetype="application/xml")

# ================================
# PROXY DE VÍDEO (COM ROLETA DE AGENTES)
# ================================
@app.route("/proxy")
def proxy_video():
    url = request.args.get("url")
    if not url:
        return "URL não fornecida", 400

    try:
        # 🎲 Sorteia um agente diferente a cada play
        disfarce_atual = random.choice(AGENTES_VIP)
        
        headers = {
            "User-Agent": disfarce_atual,
            "Accept": "*/*",
            "Connection": "keep-alive"
        }

        range_header = request.headers.get('Range', None)
        if range_header:
            headers['Range'] = range_header

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

        resp_headers = {
            "Accept-Ranges": "bytes",
            "Cache-Control": "no-store",
            "Connection": "keep-alive"
        }
        
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
# BUSCAR FILME (SISTEMA HÍBRIDO: DB LOCAL -> API)
# ================================
def buscar_filme(titulo):
    # 🗄️ TENTATIVA 1: Procurar na Base de Dados Local (filmes.db)
    try:
        # Pega a primeira palavra do título para ser mais assertivo na busca
        palavra_chave = titulo.split(':')[0].strip()
        titulo_busca_db = f"%{palavra_chave}%"
        
        conn = sqlite3.connect('filmes.db')
        c = conn.cursor()
        c.execute("SELECT url FROM playlist WHERE nome LIKE ? LIMIT 1", (titulo_busca_db,))
        resultado = c.fetchone()
        conn.close()
        
        if resultado:
            # Encontrou! Manda para o nosso Proxy mascarado.
            return f"/proxy?url={resultado[0]}"
    except Exception as e:
        print("Aviso Local DB:", e)

    # 🌐 TENTATIVA 2: Fallback para a API Externa se não achar no DB local
    titulo_busca_api = re.sub(r'[^\w\s]', '', titulo).lower().strip()
    
    # 🎲 Usamos um disfarce também na hora de buscar na API pra não levantar suspeitas
    headers_api = {
        "User-Agent": random.choice(AGENTES_VIP)
    }
    
    for srv in SERVIDORES:
        url_api = f"{srv['host']}/player_api.php?username={srv['user']}&password={srv['pass']}&action=get_vod_streams"
        
        try:
            r = requests.get(url_api, headers=headers_api, timeout=10)
            if r.status_code != 200: continue
            
            for item in r.json():
                nome_iptv = re.sub(r'[^\w\s]', '', item.get('name', '')).lower()
                if titulo_busca_api in nome_iptv:
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
    
    # Atualizado: Agora chama a nova função híbrida `buscar_filme`
    play_link = buscar_filme(data.get('title', ''))
    
    trailer = next((v['key'] for v in data.get('videos', {}).get('results', []) if v['type'] == 'Trailer'), None)
    
    return render_template("detalhes.html", filme=data, img=IMG, bg=BG, play_link=play_link, nome_site=NOME_SITE, trailer_key=trailer)

if __name__ == "__main__":
    PORT = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=PORT)
