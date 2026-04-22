from flask import Flask, render_template, request
from bs4 import BeautifulSoup
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

# ==========================================================
# 🕷️ SEU PRÓPRIO SCRAPER DE TORRENT (O "MOTOR DE BUSCA")
# ==========================================================
def buscar_torrents_1377x(titulo):
    """Raspa o site 1377x para encontrar magnets diretos"""
    try:
        # Pesquisa com foco em dublado/dual áudio
        query = urllib.parse.quote(f"{titulo} dublado")
        url_busca = f"https://www.1377x.to/search/{query}/1/"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"}
        
        # 1. Faz a busca inicial
        r = requests.get(url_busca, headers=headers, timeout=8)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        torrents = []
        # Pega apenas os 4 primeiros resultados para o site não demorar muito a carregar
        for tr in soup.select("table tbody tr")[:4]:
            links = tr.select("td.name a")
            if len(links) >= 2:
                nome = links[1].text
                link_detalhe = "https://www.1377x.to" + links[1]['href']
                
                # Pega o tamanho do arquivo limpando as tags em volta
                tamanho_bruto = tr.select_one("td.size").text
                tamanho = tamanho_bruto.split("B")[0] + "B" if "B" in tamanho_bruto else "N/A"
                
                # 2. Entra na página do torrent para roubar o Magnet Link
                r_det = requests.get(link_detalhe, headers=headers, timeout=5)
                soup_det = BeautifulSoup(r_det.text, 'html.parser')
                magnet_tag = soup_det.select_one('a[href^="magnet:?xt="]')
                
                if magnet_tag:
                    torrents.append({
                        "nome": nome[:50] + "...", 
                        "tamanho": tamanho,
                        "magnet": magnet_tag['href']
                    })
                    
        return torrents
    except Exception as e:
        print("Erro no Raspador:", e)
        return []

# ==========================================================
# ROTAS DO SITE
# ==========================================================
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
    
    # Executa o SEU raspador
    lista_torrents = buscar_torrents_1377x(titulo)
    
    titulo_exato = urllib.parse.quote(f'"{titulo}"')
    link_busca_online = f"https://www.google.com/search?q=assistir+{titulo_exato}+dublado+online+gratis+hd"
    
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
