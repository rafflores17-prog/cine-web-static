from flask import Flask, render_template
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


@app.route("/")
def home():
    filmes = tmdb("movie/popular").get("results", [])
    return render_template("index.html", filmes=filmes, img=IMG)


@app.route("/filme/<int:id>")
def filme(id):
    filme = tmdb(f"movie/{id}")

    imdb = filme.get("imdb_id")

    streams = []

    if imdb:
        try:
            r = requests.get(
                f"http://127.0.0.1:3000/streams?imdb={imdb}",
                timeout=10
            )
            streams = r.json().get("streams", [])
        except:
            streams = []

    return render_template(
        "detalhes.html",
        filme=filme,
        img=IMG,
        bg=BG,
        torrents=streams
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
