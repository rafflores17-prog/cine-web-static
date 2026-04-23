from flask import Flask, render_template, request
import requests

app = Flask(__name__)

TMDB_API_KEY = "c90fb79a2f7d756a49bee848bce5f413"

IMG = "https://image.tmdb.org/t/p/w500"
BG = "https://image.tmdb.org/t/p/original"


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
# HOME (COM BUSCA REAL)
# =========================
@app.route("/")
def home():
    query = request.args.get("q")

    if query:
        filmes = tmdb("search/movie", {"query": query}).get("results", [])

        listas = [
            {"titulo": f"🔍 Resultados para '{query}'", "filmes": filmes}
        ]
    else:
        populares = tmdb("movie/popular").get("results", [])
        top = tmdb("movie/top_rated").get("results", [])
        up = tmdb("movie/upcoming").get("results", [])

        listas = [
            {"titulo": "🔥 Populares", "filmes": populares},
            {"titulo": "⭐ Mais Avaliados", "filmes": top},
            {"titulo": "🎬 Em Breve", "filmes": up},
        ]

    return render_template(
        "index.html",
        listas=listas,
        img=IMG
    )


# =========================
# DETALHES + NODE
# =========================
@app.route("/filme/<int:id>")
def filme(id):
    filme = tmdb(f"movie/{id}")

    imdb = filme.get("imdb_id")
    torrents = []

    if imdb:
        try:
            r = requests.get(
                f"http://127.0.0.1:3000/streams?imdb={imdb}",
                timeout=12
            )

            if r.status_code == 200:
                torrents = r.json().get("streams", [])

        except:
            torrents = []

    torrents = sorted(torrents, key=lambda x: x.get("score", 0), reverse=True)

    return render_template(
        "detalhes.html",
        filme=filme,
        img=IMG,
        bg=BG,
        torrents=torrents
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
