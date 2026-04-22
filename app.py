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
    data = get_tmdb_data(f"movie/{filme_id}/videos")
    for video in data.get('results', []):
        if video.get('site') == 'YouTube' and video.get('type') == 'Trailer':
            return video.get('key')
    return None

def buscar_torrents_api(titulo):
    """Consulta a API de Torrents que você encontrou para puxar os Magnets diretos"""
    try:
        # Busca focado em dublado/dual áudio
        query = urllib.parse.quote(f"{titulo} dublado")
        url = f"https://torrent-api-py-nx0x.onrender.com/api/v1/search?query={query}"
        
        # Faz a requisição para a API externa
        resposta = requests.get(url, timeout=8).json()
        
        # Se a API retornar uma lista, formatamos os resultados (limitado a 5)
        torrents = []
        if isinstance(resposta, list):
            for item in resposta[:5]:
                # Tenta capturar o magnet, name e size baseados em padrões de APIs
                magnet = item.get('magnet') or item.get('link')
                if magnet and magnet.startswith('magnet:?'):
                    torrents.append({
                        "nome": item.get('name', 'Torrent Encontrado')[:50] + "...", # Limita o nome pra não quebrar o layout
                        "tamanho": item.get('size', 'N/A'),
                        "magnet": magnet
                    })
        return torrents
    except Exception as e:
        print("Erro na API de Torrent:", e)
        return []

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
        filmes = get_tmdb_data("discover/movie", {"primary_release_date.gte": f"{ano}-01-01", "primary_release_date.lte": f"{int(ano)+9}-12-31", "sort_by": "popularity.desc"}).get('results', [])
        listas.append({"titulo": f"🎞️ Clássicos dos Anos {ano}", "filmes": filmes})
    else:
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
    
    # 1. Puxa a lista de torrents direto da API
    lista_torrents = buscar_torrents_api(titulo)
    
    # 2. Mantém a busca online poderosa que você gostou
    titulo_exato = urllib.parse.quote(f'"{titulo}"')
    link_busca_online = f"https://www.google.com/search?q=assistir+{titulo_exato}+dublado+online+gratis+hd"
    
    # 3. Busca de segurança caso a API caia (Usando tags agressivas como você pediu)
    titulo_limpo = urllib.parse.quote(titulo)
    busca_magnet = f"https://duckduckgo.com/?q={titulo_limpo}+torrent+dublado+1080p+dual+audio+mkv+download+magnet"
    
    return render_template("detalhes.html", 
                           filme=filme, 
                           img_base=IMG_PATH, 
                           bg_base=BG_PATH, 
                           trailer=trailer_key, 
                           busca_online=link_busca_online,
                           lista_torrents=lista_torrents,
                           busca_magnet=busca_magnet)

if __name__ == "__main__":
    app.run()
