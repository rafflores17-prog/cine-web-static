from flask import Flask, render_template, request
import requests
import random

app = Flask(__name__)

# CONFIGURAÇÕES (Use as mesmas que você já tem)
TMDB_API_KEY = "c90fb79a2f7d756a49bee848bce5f413"
TMDB_IMAGE_BASE_URL = "https://image.tmdb.org/t/p/w500"

def get_movies(endpoint):
    url = f"https://api.themoviedb.org/3/{endpoint}"
    params = {"api_key": TMDB_API_KEY, "language": "pt-BR", "region": "BR"}
    try:
        r = requests.get(url, params=params)
        return r.json().get('results', [])
    except:
        return []

@app.route('/')
def index():
    # Puxa 3 listas diferentes para o site não ficar vazio
    cartaz = get_movies("movie/now_playing")[:6]
    populares = get_movies("movie/popular")[:6]
    series = get_movies("tv/popular")[:6]
    
    return render_template("index.html", 
                           cartaz=cartaz, 
                           populares=populares, 
                           series=series,
                           img_base=TMDB_IMAGE_BASE_URL)

if __name__ == "__main__":
    app.run(debug=True)
