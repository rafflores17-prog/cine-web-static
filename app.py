from flask import Flask, render_template, request
import requests

app = Flask(__name__)

TMDB_API_KEY = "c90fb79a2f7d756a49bee848bce5f413"
IMG_PATH = "https://image.tmdb.org/t/p/w500"
BG_PATH = "https://image.tmdb.org/t/p/original"

def get_tmdb_data(endpoint, params={}):
    base = "https://api.themoviedb.org/3"
    p = {"api_key": TMDB_API_KEY, "language": "pt-BR", **params}
    return requests.get(f"{base}/{endpoint}", params=p).json()

@app.route('/')
def index():
    query = request.args.get('q')
    if query:
        # Se pesquisou algo, mostra só os resultados
        filmes = get_tmdb_data("search/movie", {"query": query}).get('results', [])
        return render_template("index.html", pesquisa=filmes, query=query, img_base=IMG_PATH)
    
    # Se não pesquisou, mostra a Home estilo Netflix
    cartaz = get_tmdb_data("movie/now_playing", {"region": "BR"}).get('results', [])[:10]
    populares = get_tmdb_data("movie/popular", {"region": "BR"}).get('results', [])[:10]
    series = get_tmdb_data("tv/popular").get('results', [])[:10]
    
    return render_template("index.html", cartaz=cartaz, populares=populares, series=series, img_base=IMG_PATH)

@app.route('/filme/<int:filme_id>')
def detalhes_filme(filme_id):
    # Puxa os detalhes completos do filme específico
    filme = get_tmdb_data(f"movie/{filme_id}")
    return render_template("detalhes.html", filme=filme, img_base=IMG_PATH, bg_base=BG_PATH)

if __name__ == "__main__":
    app.run()
