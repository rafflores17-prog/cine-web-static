from flask import Flask, render_template, request, send_from_directory, jsonify, Response, stream_with_context
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
    {"host": "http://falcon12.top:80", "user": "175473583", "pass": "643238922"},
    {"host": "http://stmax.top:80", "user": "lucas6043", "pass": "px2926br"},
    {"host": "http://koquwz.com:80", "user": "471204", "pass": "epp4Jx"},
    {"host": "http://techon.one:80", "user": "003008", "pass": "440144634"}
]

# ================================
# CACHE GLOBAL (leve)
# ================================

@app.after_request
def add_cache_headers(response):

    response.headers["Cache-Control"] = \
        "public, max-age=86400"

    return response

# ================================
# SERVICE WORKER
# ================================

@app.route('/sw.js')
def sw():

    return send_from_directory(
        '.',
        'sw.js',
        mimetype='application/javascript'
    )

# ================================
# ASSET LINKS (TWA)
# ================================

@app.route('/.well-known/assetlinks.json')
def assetlinks():

    return jsonify([{
        "relation": ["delegate_permission/common.handle_all_urls"],
        "target": {
            "namespace": "android_app",
            "package_name": "online.cinemega.www.twa",
            "sha256_cert_fingerprints": [
                "64:F7:CE:80:D5:1C:79:CE:91:A7:0E:C8:BE:71:49:E6:46:64:F6:D2:96:5F:12:D6:8F:41:DC:57:A9:4E:48:CD"
            ]
        }
    }])

# ================================
# PROXY DE VÍDEO (ANTI-CRASH)
# ================================

@app.route("/proxy")
def proxy_video():

    url = request.args.get("url")

    if not url:
        return "URL não fornecida", 400

    try:

        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "*/*",
            "Connection": "keep-alive"
        }

        r = requests.get(
            url,
            headers=headers,
            stream=True,
            timeout=(5, 15)
        )

        if r.status_code != 200:
            return "Servidor de vídeo indisponível", 502

        def generate():

            try:

                for chunk in r.iter_content(1024 * 64):

                    if chunk:
                        yield chunk

            except Exception as e:

                print("Erro stream:", e)

            finally:

                r.close()

        return Response(
            stream_with_context(generate()),
            content_type=r.headers.get(
                "Content-Type",
                "video/mp4"
            ),
            headers={
                "Accept-Ranges": "bytes",
                "Cache-Control": "no-store",
                "Connection": "keep-alive"
            }
        )

    except requests.exceptions.Timeout:

        print("Timeout proxy")

        return "Tempo excedido", 504

    except requests.exceptions.ConnectionError:

        print("Erro conexão proxy")

        return "Falha de conexão", 502

    except Exception as e:

        print("Erro proxy:", e)

        return "Erro ao carregar vídeo", 500

# ================================
# BUSCAR FILME IPTV
# ================================

def buscar_no_iptv(titulo):

    titulo_busca = re.sub(
        r'[^\w\s]',
        '',
        titulo
    ).lower().strip()

    for srv in SERVIDORES:

        url_api = (
            f"{srv['host']}/player_api.php"
            f"?username={srv['user']}"
            f"&password={srv['pass']}"
            f"&action=get_vod_streams"
        )

        try:

            headers = {
                "User-Agent": "Mozilla/5.0"
            }

            r = requests.get(
                url_api,
                headers=headers,
                timeout=10
            )

            if r.status_code != 200:
                continue

            for item in r.json():

                nome_iptv = re.sub(
                    r'[^\w\s]',
                    '',
                    item.get('name', '')
                ).lower()

                if titulo_busca in nome_iptv:

                    video_url = (
                        f"{srv['host']}/movie/"
                        f"{srv['user']}/"
                        f"{srv['pass']}/"
                        f"{item.get('stream_id')}.mp4"
                    )

                    return f"/proxy?url={video_url}"

        except Exception as e:

            print("Erro IPTV:", e)

            continue

    return None

# ================================
# HOME
# ================================

@app.route("/")
def home():

    q = request.args.get("q")

    url = (
        f"https://api.themoviedb.org/3/"
        f"{'search/movie' if q else 'movie/popular'}"
        f"?api_key={TMDB_API_KEY}"
        f"&language=pt-BR"
        f"{f'&query={q}' if q else ''}"
    )

    res = requests.get(
        url,
        timeout=10
    ).json().get(
        "results",
        []
    )

    return render_template(
        "index.html",
        filmes=res[:20],
        img=IMG,
        nome_site=NOME_SITE
    )

# ================================
# DETALHES
# ================================

@app.route("/filme/<int:id>")
def detalhes(id):

    data = requests.get(
        f"https://api.themoviedb.org/3/movie/{id}"
        f"?api_key={TMDB_API_KEY}"
        f"&language=pt-BR"
        f"&append_to_response=videos",
        timeout=10
    ).json()

    play_link = buscar_no_iptv(
        data.get(
            'title',
            ''
        )
    )

    trailer = next(
        (
            v['key']
            for v in data
            .get('videos', {})
            .get('results', [])
            if v['type'] == 'Trailer'
        ),
        None
    )

    return render_template(
        "detalhes.html",
        filme=data,
        img=IMG,
        bg=BG,
        play_link=play_link,
        nome_site=NOME_SITE,
        trailer_key=trailer
    )

# ================================
# START
# ================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000
    )
