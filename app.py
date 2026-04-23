from flask import Flask, render_template, request
import requests
import urllib.parse

app = Flask(__name__)

TMDB_API_KEY = "c90fb79a2f7d756a49bee848bce5f413"

IMG_PATH = "https://image.tmdb.org/t/p/w500"
BG_PATH = "https://image.tmdb.org/t/p/original"

# ==========================================================
# TMDB
# ==========================================================
def get_tmdb_data(endpoint, params={}):
    base = "https://api.themoviedb.org/3"
    p = {"api_key": TMDB_API_KEY, "language": "pt-BR", **params}
    try:
        return requests.get(f"{base}/{endpoint}", params=p, timeout=10).json()
    except:
        return {}

def get_trailer(filme_id):
    data = get_tmdb_data(f"movie/{filme_id}/videos")
    for video in data.get('results', []):
        if video.get('site') == 'YouTube' and video.get('type') == 'Trailer':
            return video.get('key')
    return None

# ==========================================================
# FILTRO
# ==========================================================
def filtro(nome, titulo_ref):
    nome = nome.lower()

    lixo = ["app", "software", "crack", "android", "game", "setup"]
    if any(x in nome for x in lixo):
        return False

    # garante que tem relação com o filme
    palavras = titulo_ref.lower().split()
    return any(p in nome for p in palavras)

# ==========================================================
# BUSCA INTELIGENTE
# ==========================================================
def buscar_torrents_api(titulo, titulo_original, ano):
    try:
        buscas = [
            f"{titulo_original} {ano} 1080p",
            f"{titulo_original} {ano} BluRay",
            f"{titulo_original} {ano}",
            f"{titulo} {ano}"
        ]

        torrents = []

        for busca in buscas:
            url = f"https://torrent-api-t1ml.onrender.com/streams?q={urllib.parse.quote(busca)}"
            r = requests.get(url, timeout=15)

            if r.status_code != 200:
                continue

            data = r.json()

            for item in data.get("streams", []):
                nome = item.get("title", "")

                if not filtro(nome, titulo_original):
                    continue

                torrents.append({
                    "nome": nome[:70],
                    "tamanho": item.get("size", "N/A"),
                    "magnet": item.get("magnet"),
                    "seeders": item.get("seeders", 0)
                })

        torrents.sort(key=lambda x: x["seeders"], reverse=True)

        # remove duplicados
        vistos = set()
        final = []

        for t in torrents:
            if t["nome"] not in vistos:
                vistos.add(t["nome"])
                final.append(t)

        return final[:12]

    except Exception as e:
        print("Erro API:", e)
        return []

# ==========================================================
# ROTAS
# ==========================================================
@app.route('/')
def index():
    query = request.args.get('q')
    listas = []

    if query:
        filmes = get_tmdb_data("search/movie", {"query": query}).get('results', [])
        listas.append({"titulo": f"🔍 {query}", "filmes": filmes})

    else:
        listas.append({
            "titulo": "🔥 Lançamentos",
            "filmes": get_tmdb_data("movie/now_playing", {"region": "BR"}).get('results', [])[:15]
        })
        listas.append({
            "titulo": "🌟 Populares",
            "filmes": get_tmdb_data("movie/popular").get('results', [])[:15]
        })

    return render_template("index.html", listas=listas, img_base=IMG_PATH)

# ==========================================================
@app.route('/filme/<int:filme_id>')
def detalhes_filme(filme_id):
    filme = get_tmdb_data(f"movie/{filme_id}")
    trailer = get_trailer(filme_id)

    titulo = filme.get('title', '')
    titulo_original = filme.get('original_title', titulo)
    ano = filme.get('release_date', '')[:4]

    torrents = buscar_torrents_api(titulo, titulo_original, ano)

    return render_template(
        "detalhes.html",
        filme=filme,
        img_base=IMG_PATH,
        bg_base=BG_PATH,
        trailer=trailer,
        lista_torrents=torrents
    )

# ==========================================================
if __name__ == "__main__":
    app.run(debug=True)
