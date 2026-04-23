from flask import Flask, render_template, request
import requests
import urllib.parse
import unicodedata
import re

app = Flask(__name__)

# ================= SUA CHAVE ORIGINAL (DO SEU CÓDIGO) =================
TMDB_API_KEY = "c90fb79a2f7d756a49bee848bce5f413"

IMG_PATH = "https://image.tmdb.org/t/p/w500"
BG_PATH = "https://image.tmdb.org/t/p/original"

NODE_API = "http://localhost:3000/streams"

# ================= TMDB =================
def get_tmdb(endpoint, params={}):
    base = "https://api.themoviedb.org/3"

    p = {
        "api_key": TMDB_API_KEY,
        "language": "pt-BR",
        **params
    }

    try:
        r = requests.get(f"{base}/{endpoint}", params=p, timeout=10)
        return r.json()
    except:
        return {}

# ================= TRAILER =================
def get_trailer(movie_id):
    data = get_tmdb(f"movie/{movie_id}/videos")

    for v in data.get("results", []):
        if v.get("site") == "YouTube" and v.get("type") == "Trailer":
            return v.get("key")

    return None

# ================= LIMPEZA =================
def limpar(txt):
    txt = str(txt)
    txt = unicodedata.normalize('NFD', txt)
    txt = ''.join(c for c in txt if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^\w\s]', '', txt).lower()

# ================= HOME =================
@app.route("/")
def index():
    query = request.args.get("q")
    genero = request.args.get("genero")
    ano = request.args.get("ano")

    listas = []

    if query:
        filmes = get_tmdb("search/movie", {"query": query}).get("results", [])
        listas.append({"titulo": f"🔍 Resultados: {query}", "filmes": filmes})

    elif genero:
        filmes = get_tmdb("discover/movie", {"with_genres": genero}).get("results", [])
        listas.append({"titulo": "🎬 Gênero", "filmes": filmes})

    elif ano:
        filmes = get_tmdb("discover/movie", {
            "primary_release_date.gte": f"{ano}-01-01",
            "primary_release_date.lte": f"{int(ano)+1}-12-31"
        }).get("results", [])
        listas.append({"titulo": f"📼 Ano {ano}", "filmes": filmes})

    else:
        listas.append({
            "titulo": "🔥 Populares",
            "filmes": get_tmdb("movie/popular").get("results", [])[:15]
        })

    return render_template("index.html", listas=listas, img_base=IMG_PATH)

# ================= DETALHES =================
@app.route("/filme/<int:id>")
def detalhes(id):

    filme = get_tmdb(f"movie/{id}")

    titulo = filme.get("title", "")
    imdb = filme.get("imdb_id") or ""

    trailer = get_trailer(id)

    streams = []

    # ================= NODE ENGINE =================
    if imdb and titulo:
        try:
            r = requests.get(NODE_API, params={
                "imdb": imdb,
                "title": titulo
            }, timeout=10)

            data = r.json()
            streams = data.get("streams", [])

        except Exception as e:
            print("Erro Node:", e)
            streams = []

    return render_template(
        "detalhes.html",
        filme=filme,
        img_base=IMG_PATH,
        bg_base=BG_PATH,
        trailer=trailer,
        lista_torrents=streams
    )

if __name__ == "__main__":
    app.run(debug=True)
