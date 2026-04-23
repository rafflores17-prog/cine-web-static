from flask import Flask, render_template, request, jsonify
import requests

app = Flask(__name__)

TMDB_API_KEY = "c90fb79a2f7d756a49bee848bce5f413"

IMG = "https://image.tmdb.org/t/p/w500"
BG = "https://image.tmdb.org/t/p/original"


# =========================
# TMDB
# =========================
def tmdb(endpoint, params=None):
    if params is None:
        params = {}

    url = f"https://api.themoviedb.org/3/{endpoint}"
    params["api_key"] = TMDB_API_KEY
    params["language"] = "pt-BR"

    try:
        r = requests.get(url, params=params, timeout=10)
        return r.json()
    except:
        return {}


# =========================
# "MOTOR EMBUTIDO" (SIMULAÇÃO DO NODE)
# =========================
def torrent_motor(imdb):
    try:
        # aqui você pode trocar por API real depois
        url = f"https://example.com/streams?imdb={imdb}"
        r = requests.get(url, timeout=8)

        if r.status_code == 200:
            return r.json().get("streams", [])

    except:
        pass

    # fallback fake (pra nunca quebrar site)
    return [
        {"title": "1080p BluRay x264", "size": "1.4GB", "score": 10},
        {"title": "720p WEB-DL", "size": "800MB", "score": 8}
    ]


# =========================
# HOME
# =========================
@app.route("/")
def home():
    query = request.args.get("q")

    if query:
        filmes = tmdb("search/movie", {"query": query}).get("results", [])
        listas = [{"titulo": f"🔎 Resultados: {query}", "filmes": filmes}]
    else:
        listas = [
            {"titulo": "🔥 Populares", "filmes": tmdb("movie/popular").get("results", [])},
            {"titulo": "⭐ Top", "filmes": tmdb("movie/top_rated").get("results", [])},
            {"titulo": "🎬 Em breve", "filmes": tmdb("movie/upcoming").get("results", [])},
        ]

    return render_template("index.html", listas=listas, img=IMG)


# =========================
# DETALHES
# =========================
@app.route("/filme/<int:id>")
def filme(id):
    filme = tmdb(f"movie/{id}")

    imdb = filme.get("imdb_id")
    torrents = torrent_motor(imdb) if imdb else []

    torrents = sorted(torrents, key=lambda x: x.get("score", 0), reverse=True)

    return render_template(
        "detalhes.html",
        filme=filme,
        img=IMG,
        bg=BG,
        torrents=torrents
    )


# =========================
# RUN
# =========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
