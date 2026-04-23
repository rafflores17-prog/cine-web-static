from flask import Flask, render_template, request
import requests
import urllib.parse
import unicodedata
import re

app = Flask(__name__)

TMDB_API_KEY = "SUA_CHAVE_AQUI"

IMG = "https://image.tmdb.org/t/p/w500"
BG = "https://image.tmdb.org/t/p/original"

NODE_API = "http://localhost:3000/streams"

# ================= TMDB =================
def tmdb(endpoint, params={}):
    base = "https://api.themoviedb.org/3"
    p = {"api_key": TMDB_API_KEY, "language": "pt-BR", **params}
    try:
        return requests.get(f"{base}/{endpoint}", params=p, timeout=10).json()
    except:
        return {}

# ================= TRAILER =================
def trailer(id):
    data = tmdb(f"movie/{id}/videos")
    for v in data.get("results", []):
        if v.get("site") == "YouTube" and v.get("type") == "Trailer":
            return v.get("key")
    return None

# ================= LIMPEZA =================
def clean(txt):
    txt = str(txt)
    txt = unicodedata.normalize("NFD", txt)
    txt = ''.join(c for c in txt if unicodedata.category(c) != "Mn")
    return re.sub(r"[^\w\s]", "", txt).lower()

# ================= HOME =================
@app.route("/")
def home():
    q = request.args.get("q")

    listas = []

    if q:
        filmes = tmdb("search/movie", {"query": q}).get("results", [])
        listas.append({"titulo": f"🔍 {q}", "filmes": filmes})
    else:
        listas.append({
            "titulo": "🔥 Populares",
            "filmes": tmdb("movie/popular").get("results", [])[:15]
        })

    return render_template("index.html", listas=listas, img=IMG)

# ================= DETALHES =================
@app.route("/filme/<int:id>")
def filme(id):

    movie = tmdb(f"movie/{id}")

    title = movie.get("title")
    imdb = movie.get("imdb_id")

    yt = trailer(id)

    streams = []

    # 🔥 CHAMA NODE ENGINE
    if imdb:
        try:
            r = requests.get(NODE_API, params={
                "imdb": imdb,
                "title": title
            }, timeout=10)

            streams = r.json().get("streams", [])

        except:
            streams = []

    return render_template(
        "detalhes.html",
        filme=movie,
        img=IMG,
        bg=BG,
        trailer=yt,
        streams=streams
    )

if __name__ == "__main__":
    app.run(debug=True)
