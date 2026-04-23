from flask import Flask, render_template, request
import requests

app = Flask(__name__)

# =========================
# CONFIG TMDB
# =========================
TMDB_API_KEY = "c90fb79a2f7d756a49bee848bce5f413"

IMG = "https://image.tmdb.org/t/p/w500"
BG = "https://image.tmdb.org/t/p/original"


# =========================
# TMDB REQUEST SAFE
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
# HOME (INDEX)
# =========================
@app.route("/")
def home():
    populares = tmdb("movie/popular").get("results", [])
    top_rated = tmdb("movie/top_rated").get("results", [])
    upcoming = tmdb("movie/upcoming").get("results", [])

    listas = [
        {"titulo": "🔥 Populares", "filmes": populares},
        {"titulo": "⭐ Mais Bem Avaliados", "filmes": top_rated},
        {"titulo": "🎬 Em Breve", "filmes": upcoming},
    ]

    return render_template(
        "index.html",
        listas=listas,
        img=IMG
    )


# =========================
# DETALHES + NODE MOTOR
# =========================
@app.route("/filme/<int:id>")
def filme(id):
    filme = tmdb(f"movie/{id}")

    imdb = filme.get("imdb_id")

    torrents = []

    # =========================
    # CHAMA MOTOR NODE
    # =========================
    if imdb:
        try:
            url = f"http://127.0.0.1:3000/streams?imdb={imdb}"
            r = requests.get(url, timeout=12)

            if r.status_code == 200:
                data = r.json()
                torrents = data.get("streams", [])
        except Exception as e:
            print("Erro Node:", e)

    # =========================
    # ORDENA MELHOR PRIMEIRO
    # =========================
    try:
        torrents = sorted(
            torrents,
            key=lambda x: x.get("score", 0),
            reverse=True
        )
    except:
        pass

    return render_template(
        "detalhes.html",
        filme=filme,
        img=IMG,
        bg=BG,
        torrents=torrents
    )


# =========================
# RUN SERVER
# =========================
if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )
