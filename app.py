from flask import Flask, render_template, request
import requests
import random
from datetime import datetime

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


@app.route("/")
def home():
    query = request.args.get("q")

    if query:
        filmes = tmdb("search/movie", {"query": query}).get("results", [])
        listas = [{"titulo": f"🔎 Resultados: {query}", "filmes": filmes}]
    else:
        populares = tmdb("movie/popular").get("results", [])
        top = tmdb("movie/top_rated").get("results", [])
        upcoming_raw = tmdb("movie/upcoming").get("results", [])

        hoje = str(datetime.today().date())

        # 🎬 ESTREIAS REAIS
        estreias = [
            m for m in upcoming_raw
            if m.get("release_date") and m["release_date"] >= hoje
        ]

        # 🎲 SURPRESA
        surpresa = random.sample(populares, min(10, len(populares)))

        # 📅 VIAGEM NO TEMPO (1980 → HOJE)
        todos = populares + top

        por_ano = {}

        for m in todos:
            if m.get("release_date"):
                ano = m["release_date"][:4]

                if ano.isdigit():
                    ano = int(ano)

                    if 1980 <= ano <= datetime.today().year:
                        por_ano.setdefault(ano, []).append(m)

        viagem = []
        for ano in sorted(por_ano.keys()):
            viagem.append({
                "titulo": f"📅 Ano {ano}",
                "filmes": por_ano[ano][:10]
            })

        listas = [
            {"titulo": "🔥 Populares", "filmes": populares},
            {"titulo": "🎬 Estreias Confirmadas", "filmes": estreias},
            {"titulo": "🎲 Surpresa do Dia", "filmes": surpresa},
        ] + viagem

    return render_template("index.html", listas=listas, img=IMG)


@app.route("/filme/<int:id>")
def filme(id):
    filme = tmdb(f"movie/{id}")

    videos = tmdb(f"movie/{id}/videos").get("results", [])
    trailer = None

    for v in videos:
        if v["type"] == "Trailer" and v["site"] == "YouTube":
            trailer = v["key"]
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
