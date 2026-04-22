from flask import Flask, render_template, request
import requests
import urllib.parse

app = Flask(__name__)

TMDB_API_KEY = "c90fb79a2f7d756a49bee848bce5f413"
IMG_PATH = "https://image.tmdb.org/t/p/w500"
BG_PATH = "https://image.tmdb.org/t/p/original"

def get_tmdb_data(endpoint, params={}):
    base = "https://api.themoviedb.org/3"
    p = {"api_key": TMDB_API_KEY, "language": "pt-BR", **params}
    try:
        return requests.get(f"{base}/{endpoint}", params=p, timeout=10).json()
    except:
        return {}

def get_trailer(filme_id):
    """Busca o código do trailer no YouTube via TMDB"""
    data = get_tmdb_data(f"movie/{filme_id}/videos")
    for video in data.get('results', []):
        if video.get('site') == 'YouTube' and video.get('type') == 'Trailer':
            return video.get('key')
    return None

@app.route('/')
def index():
    query = request.args.get('q')
    genero = request.args.get('genero')
    ano = request.args.get('ano')

    listas = []

    if query:
        filmes = get_tmdb_data("search/movie", {"query": query}).get('results', [])
        listas.append({"titulo": f"🔍 Resultados para: '{query}'", "filmes": filmes})
    elif genero:
        filmes = get_tmdb_data("discover/movie", {"with_genres": genero, "sort_by": "popularity.desc"}).get('results', [])
        listas.append({"titulo": "🎭 Filmes Encontrados", "filmes": filmes})
    elif ano:
        # Busca filmes da década (Ex: 1980 a 1989)
        filmes = get_tmdb_data("discover/movie", {"primary_release_date.gte": f"{ano}-01-01", "primary_release_date.lte": f"{int(ano)+9}-12-31", "sort_by": "popularity.desc"}).get('results', [])
        listas.append({"titulo": f"🎞️ Clássicos dos Anos {ano}", "filmes": filmes})
    else:
        # Home Padrão Bem Preenchida
        listas.append({"titulo": "🔥 Lançamentos", "filmes": get_tmdb_data("movie/now_playing", {"region": "BR"}).get('results', [])[:15]})
        listas.append({"titulo": "🌟 Mais Populares", "filmes": get_tmdb_data("movie/popular", {"region": "BR"}).get('results', [])[:15]})
        listas.append({"titulo": "👻 Terror e Suspense", "filmes": get_tmdb_data("discover/movie", {"with_genres": "27,53"}).get('results', [])[:15]})
        listas.append({"titulo": "💥 Ação e Aventura", "filmes": get_tmdb_data("discover/movie", {"with_genres": "28,12"}).get('results', [])[:15]})

    return render_template("index.html", listas=listas, img_base=IMG_PATH)

@app.route('/filme/<int:filme_id>')
def detalhes_filme(filme_id):
    filme = get_tmdb_data(f"movie/{filme_id}")
    trailer_key = get_trailer(filme_id)
    
    titulo = filme.get('title', '')
    
    # Gerador de Links Dinâmicos
    links = {
        "player_1": f"https://embed.warezcdn.net/filme/{filme_id}",
        "player_2": f"https://multiembed.mov/?video_id={filme_id}&tmdb=1",
        "torrent_br": f"https://duckduckgo.com/?q={urllib.parse.quote(titulo + ' torrent dublado 1080p')}",
        "piratebay": f"https://thepiratebay.org/search.php?q={urllib.parse.quote(titulo)}",
        "yts": f"https://yts.mx/browse-movies/{urllib.parse.quote(titulo)}/all/all/0/latest/0/all"
    }
    
    return render_template("detalhes.html", filme=filme, img_base=IMG_PATH, bg_base=BG_PATH, trailer=trailer_key, links=links)

if __name__ == "__main__":
    app.run()
