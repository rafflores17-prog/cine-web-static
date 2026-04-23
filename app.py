from flask import Flask, render_template, request
import requests

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


# 🎬 HOME REFORMULADA
@app.route("/")
def home():
    query = request.args.get("q")
    genre = request.args.get("genre")

    if query:
        filmes = tmdb("search/movie", {"query": query}).get("results", [])
        return render_template("index.html", img=IMG, filmes=filmes, modo="search")

    # 🔥 EM ALTA
    em_alta = tmdb("movie/popular").get("results", [])

    # 🎬 EM CARTAZ
    em_cartaz = tmdb("movie/now_playing").get("results", [])

    # 📅 ESTREIAS (PRÓXIMOS FILMES)
    upcoming = tmdb("movie/upcoming").get("results", [])

    # 🎭 FILTRO POR GÊNERO (opcional simples)
    if genre:
        em_alta = [f for f in em_alta if genre in str(f.get("genre_ids"))]

    return render_template(
        "index.html",
        img=IMG,
        em_alta=em_alta,
        em_cartaz=em_cartaz,
        estreias=upcoming,
        modo="home"
    )


# 🎬 DETALHES (simples e estável)
@app.route("/filme/<int:id>")
def filme(id):
    filme = tmdb(f"movie/{id}")
    return render_template("detalhes.html", filme=filme, img=IMG)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
