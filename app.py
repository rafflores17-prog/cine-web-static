from flask import Flask, render_template, request, jsonify
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


DECADES = {
    "80": (1980, 1989),
    "90": (1990, 1999),
    "2000": (2000, 2009),
    "2010": (2010, 2019),
    "2020": (2020, 2030),
}


@app.route("/")
def home():
    filmes = tmdb("movie/popular").get("results", [])
    return render_template("index.html", filmes=filmes, img=IMG)


@app.route("/decada/<dec>")
def decada(dec):
    base = tmdb("movie/popular").get("results", []) + tmdb("movie/top_rated").get("results", [])

    if dec not in DECADES:
        return jsonify({"filmes": []})

    inicio, fim = DECADES[dec]

    filtrados = []

    for f in base:
        date = f.get("release_date")
        if date and date[:4].isdigit():
            ano = int(date[:4])
            if inicio <= ano <= fim:
                filtrados.append(f)

    # 🔥 Fallback obrigatório (NUNCA vazio)
    if not filtrados:
        filtrados = base

    # aleatório controlado
    selecionados = random.sample(filtrados, min(12, len(filtrados)))

    return jsonify({"filmes": selecionados})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
