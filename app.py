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
        return requests.get(url, params=params, timeout=10).json()
    except:
        return {}


# ======================
# HOME (ESTÁVEL)
# ======================
@app.route("/")
def home():
    query = request.args.get("q")

    if query:
        filmes = tmdb("search/movie", {"query": query}).get("results", [])
    else:
        filmes = tmdb("movie/popular").get("results", [])

    return render_template("index.html", filmes=filmes, img=IMG)


# ======================
# DETALHES (COM TRAILER)
# ======================
@app.route("/filme/<int:id>")
def filme(id):
    filme = tmdb(f"movie/{id}")

    videos = tmdb(f"movie/{id}/videos").get("results", [])
    trailer = None

    for v in videos:
        if v.get("type") == "Trailer" and v.get("site") == "YouTube":
            trailer = v.get("key")
            break

    return render_template(
        "detalhes.html",
        filme=filme,
        img=IMG,
        bg=BG,
        trailer=trailer
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
