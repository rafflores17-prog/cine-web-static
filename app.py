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
    return requests.get(f"{base}/{endpoint}", params=p).json()

def get_torrent(title):
    try:
        clean_title = "".join(c for c in title if c.isalnum() or c==' ')
        q = urllib.parse.quote(clean_title)
        url = f"https://yts.mx/api/v2/list_movies.json?query_term={q}&limit=1"
        res = requests.get(url, timeout=5).json()
        if res.get('data', {}).get('movie_count', 0) > 0:
            hash_code = res['data']['movies'][0]['torrents'][0]['hash']
            return f"magnet:?xt=urn:btih:{hash_code}&dn={q}"
    except: return None
    return None

@app.route('/')
def index():
    query = request.args.get('q')
    genero = request.args.get('genero')
    ano = request.args.get('ano')

    listas = []

    if query:
        filmes = get_tmdb_data("search/movie", {"query": query}).get('results', [])
        listas.append({"titulo": f"🔍 Resultados para: {query}", "filmes": filmes})
    elif genero:
        filmes = get_tmdb_data("discover/movie", {"with_genres": genero, "sort_by": "popularity.desc"}).get('results', [])
        listas.append({"titulo": "🎭 Filmes por Gênero", "filmes": filmes})
    elif ano:
        # Pega a década (ex: 1980 a 1989)
        filmes = get_tmdb_data("discover/movie", {"primary_release_date.gte": f"{ano}-01-01", "primary_release_date.lte": f"{int(ano)+9}-12-31", "sort_by": "popularity.desc"}).get('results', [])
        listas.append({"titulo": f"🎞️ Clássicos dos Anos {ano}", "filmes": filmes})
    else:
        # Home Padrão
        listas.append({"titulo": "🔥 Em Cartaz", "filmes": get_tmdb_data("movie/now_playing", {"region": "BR"}).get('results', [])[:12]})
        listas.append({"titulo": "🌟 Populares", "filmes": get_tmdb_data("movie/popular", {"region": "BR"}).get('results', [])[:12]})
        listas.append({"titulo": "👽 Ficção Científica", "filmes": get_tmdb_data("discover/movie", {"with_genres": "878"}).get('results', [])[:12]})

    return render_template("index.html", listas=listas, img_base=IMG_PATH)

@app.route('/filme/<int:filme_id>')
def detalhes_filme(filme_id):
    filme = get_tmdb_data(f"movie/{filme_id}")
    torrent_link = get_torrent(filme.get('title', ''))
    
    # Links de Smart Search
    q_online = urllib.parse.quote(f"assistir {filme.get('title')} dublado online")
    link_busca = f"https://duckduckgo.com/?q={q_online}"
    
    return render_template("detalhes.html", filme=filme, img_base=IMG_PATH, bg_base=BG_PATH, torrent=torrent_link, link_busca=link_busca)

if __name__ == "__main__":
    app.run()
