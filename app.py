from flask import Flask, render_template, request
import requests
import urllib.parse
import unicodedata
import re

app = Flask(__name__)

TMDB_API_KEY = "c90fb79a2f7d756a49bee848bce5f413"

IMG_PATH = "https://image.tmdb.org/t/p/w500"
BG_PATH = "https://image.tmdb.org/t/p/original"

# ================= TMDB =================
def get_tmdb(endpoint, params={}):
    base = "https://api.themoviedb.org/3"
    p = {"api_key": TMDB_API_KEY, "language": "pt-BR", **params}

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

# ================= TORRENT API =================
def buscar_torrents_api(br, orig, imdb):
    try:
        url = "https://torrent-api-t1ml.onrender.com/streams"

        params = {
            "br": br,
            "orig": orig,
            "imdb": imdb
        }

        r = requests.get(url, params=params, timeout=20)

        data = r.json()

        streams = data.get("streams", [])

        resultados = []

        palavras = limpar(br).split()[:3]

        for item in streams:
            nome = item.get("title", "")
            nome_low = limpar(nome)

            # 🔥 FILTRO MAIS LEVE (IMPORTANTE)
            if len(nome_low) < 5:
                continue

            # só bloqueia lixo real
            if any(x in nome_low for x in ["apk", "android", "software", "crack"]):
                continue

            # 🔥 validação mínima (NÃO destrói resultados)
            if not any(p in nome_low for p in palavras):
                continue

            score = 0

            if "dublado" in nome_low or "dual" in nome_low:
                score += 5

            if "1080p" in nome_low:
                score += 4
            elif "720p" in nome_low:
                score += 2

            resultados.append({
                "nome": nome,
                "tamanho": item.get("size", "N/A"),
                "magnet": item.get("magnet"),
                "score": score
            })

        return resultados[:20]

    except Exception as e:
        print("Erro API:", e)
        return []

# ================= ROTAS =================
@app.route('/')
def index():
    query = request.args.get('q')
    genero = request.args.get('genero')
    ano = request.args.get('ano')

    listas = []

    if query:
        filmes = get_tmdb("search/movie", {"query": query}).get("results", [])
        listas.append({"titulo": f"🔍 {query}", "filmes": filmes})

    elif genero:
        filmes = get_tmdb("discover/movie", {"with_genres": genero}).get("results", [])
        listas.append({"titulo": "🎬 Gênero", "filmes": filmes})

    elif ano:
        filmes = get_tmdb("discover/movie", {
            "primary_release_date.gte": f"{ano}-01-01",
            "primary_release_date.lte": f"{int(ano)+1}-12-31"
        }).get("results", [])

        listas.append({"titulo": f"📼 {ano}", "filmes": filmes})

    else:
        listas.append({"titulo": "🔥 Popular", "filmes": get_tmdb("movie/popular").get("results", [])[:15]})

    return render_template("index.html", listas=listas, img_base=IMG_PATH)

# ================= DETALHES =================
@app.route('/filme/<int:id>')
def detalhes(id):

    filme = get_tmdb(f"movie/{id}")
    trailer = get_trailer(id)

    titulo = filme.get("title", "")
    original = filme.get("original_title", titulo)
    imdb = filme.get("imdb_id") or ""

    torrents = buscar_torrents_api(titulo, original, imdb)

    return render_template(
        "detalhes.html",
        filme=filme,
        img_base=IMG_PATH,
        bg_base=BG_PATH,
        trailer=trailer,
        lista_torrents=torrents
    )

if __name__ == "__main__":
    app.run(debug=True)
