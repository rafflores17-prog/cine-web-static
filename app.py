from flask import Flask, render_template, request
import requests
import random

app = Flask(__name__)

TMDB_API_KEY = "c90fb79a2f7d756a49bee848bce5f413"

IMG = "https://image.tmdb.org/t/p/w500"


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


# 🎬 MAPA DAS DÉCADAS
DECADES = {
    "80": (1980, 1989),
    "90": (1990, 1999),
    "2000": (2000, 2009),
    "2010": (2010, 2019),
    "2020": (2020, 2026),
}


@app.route("/")
def home():
    query = request.args.get("q")

    if query:
        filmes = tmdb("search/movie", {"query": query}).get("results", [])
        return render_template("index.html", img=IMG, filmes=filmes, modo="search")

    populares = tmdb("movie/popular").get("results", [])
    return render_template("index.html", img=IMG, filmes=populares, modo="home")


# 🎲 API INTERNA DAS DÉCADAS
@app.route("/decada/<dec>")
def decada(dec):
    filmes_base = tmdb("movie/popular").get("results", []) + tmdb("movie/top_rated").get("results", [])

    if dec not in DECADES:
        return {"erro": "decada invalida"}

    inicio, fim = DECADES[dec]

    filtrados = [
        m for m in filmes_base
        if m.get("release_date")
        and m["release_date"][:4].isdigit()
        and inicio <= int(m["release_date"][:4]) <= fim
    ]

    # evita vazio
    if not filtrados:
        filtrados = filmes_base

    return {"filmes": random.sample(filtrados, min(12, len(filtrados)))}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
