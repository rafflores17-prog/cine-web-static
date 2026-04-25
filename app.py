from flask import Flask, render_template, request, send_from_directory, Response, stream_with_context
import requests
import re
import os

app = Flask(__name__)

NOME_SITE = "Cine Mega"

TMDB_API_KEY = "c90fb79a2f7d756a49bee848bce5f413"

IMG = "https://image.tmdb.org/t/p/w500"
BG = "https://image.tmdb.org/t/p/original"

# SERVIDORES IPTV

SERVIDORES = [

    # NOVO SERVIDOR ADICIONADO (o que você enviou)

    {
        "host": "http://serv99.xyz:8880",
        "user": "1764371",
        "pass": "2419902"
    },

    # SEU SERVIDOR ORIGINAL

    {
        "host": "http://serv99.xyz:8880",
        "user": "261491762",
        "pass": "2516895925"
    },

    {
        "host": "http://falcon12.top:80",
        "user": "175473583",
        "pass": "643238922"
    },

    {
        "host": "http://stmax.top:80",
        "user": "lucas6043",
        "pass": "px2926br"
    },

    {
        "host": "http://koquwz.com:80",
        "user": "471204",
        "pass": "epp4Jx"
    },

    {
        "host": "http://techon.one:80",
        "user": "003008",
        "pass": "440144634"
    }

]


# CACHE INTELIGENTE

@app.after_request
def add_cache_headers(response):

    if request.path.endswith((
        ".js",
        ".css",
        ".png",
        ".jpg",
        ".jpeg",
        ".webp",
        ".svg"
    )):

        response.headers["Cache-Control"] = \
            "public, max-age=86400"

    else:

        response.headers["Cache-Control"] = \
            "no-store, no-cache, must-revalidate, max-age=0"

    return response


# SERVICE WORKER

@app.route('/sw.js')
def sw():

    return send_from_directory(
        '.',
        'sw.js',
        mimetype='application/javascript'
    )


# HEALTH CHECK

@app.route("/health")
def health():
    return "OK"


# PROXY ORIGINAL (ESTÁVEL)

@app.route("/proxy")
def proxy_video():

    url = request.args.get("url")

    if not url:
        return "URL não fornecida", 400

    try:

        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "*/*",
            "Connection": "keep-alive",
            "Range": request.headers.get("Range", "bytes=0-")
        }

        r = requests.get(
            url,
            headers=headers,
            stream=True,
            timeout=(5, 20)
        )

        if r.status_code not in [200, 206]:
            return "Servidor de vídeo indisponível", 502

        def generate():

            try:

                for chunk in r.iter_content(1024 * 64):

                    if chunk:
                        yield chunk

            finally:

                r.close()

        return Response(
            stream_with_context(generate()),
            status=r.status_code,
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

    except Exception as e:

        print("Erro proxy:", e)

        return "Erro ao carregar vídeo", 500


# BUSCAR FILME IPTV

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

            r = requests.get(
                url_api,
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


# HOME

@app.route("/")
def home():

    q = request.args.get("q")

    if q:

        url = (
            "https://api.themoviedb.org/3/search/movie"
            f"?api_key={TMDB_API_KEY}"
            "&language=pt-BR"
            f"&query={q}"
        )

    else:

        url = (
            "https://api.themoviedb.org/3/movie/popular"
            f"?api_key={TMDB_API_KEY}"
            "&language=pt-BR"
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


# DETALHES

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
        data.get('title', '')
    )

    videos = data.get(
        'videos',
        {}
    ).get(
        'results',
        []
    )

    trailer = None

    for v in videos:

        if (
            v.get('site') == 'YouTube'
            and v.get('type') in ['Trailer', 'Teaser']
        ):

            trailer = v.get('key')
            break

    return render_template(
        "detalhes.html",
        filme=data,
        img=IMG,
        bg=BG,
        play_link=play_link,
        nome_site=NOME_SITE,
        trailer_key=trailer
    )


# START

if __name__ == "__main__":

    PORT = int(
        os.environ.get(
            "PORT",
            8000
        )
    )

    app.run(
        host="0.0.0.0",
        port=PORT
    )
