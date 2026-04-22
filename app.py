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
# 🕷️ RASPADOR SEGURO 1337X (BLOQUEADO NA CATEGORIA FILMES)
# ==========================================================
def buscar_torrents_1377x_seguro(titulo):
    """Raspa o site 1377x mas com um cadeado na categoria 'Movies'"""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"}
    
    def fazer_busca(query):
        # O Segredo: O URL usa /category-search/ e termina em /Movies/1/
        url_busca = f"https://www.1377x.to/category-search/{urllib.parse.quote(query)}/Movies/1/"
        try:
            r = requests.get(url_busca, headers=headers, timeout=8)
            soup = BeautifulSoup(r.text, 'html.parser')
            torrents = []
            
            for tr in soup.select("table tbody tr")[:4]:
                links = tr.select("td.name a")
                if len(links) >= 2:
                    nome = links[1].text
                    link_detalhe = "https://www.1377x.to" + links[1]['href']
                    tamanho_bruto = tr.select_one("td.size").text
                    tamanho = tamanho_bruto.split("B")[0] + "B" if "B" in tamanho_bruto else "N/A"
                    
                    # Entra na página do ficheiro para puxar o Magnet Link
                    r_det = requests.get(link_detalhe, headers=headers, timeout=5)
                    soup_det = BeautifulSoup(r_det.text, 'html.parser')
                    magnet_tag = soup_det.select_one('a[href^="magnet:?xt="]')
                    
                    if magnet_tag:
                        torrents.append({
                            "nome": nome[:55] + "..." if len(nome) > 55 else nome, 
                            "tamanho": tamanho,
                            "magnet": magnet_tag['href']
                        })
            return torrents
        except Exception as e:
            print("Erro no Raspador:", e)
            return []

    # 1. Tentativa principal: Procura por cópias dubladas no Brasil
    resultados = fazer_busca(f"{titulo} dublado")
    
    # 2. Resgate 1: Tenta procurar por "dual" áudio
    if not resultados:
        resultados = fazer_busca(f"{titulo} dual")
        
    # 3. Resgate final: Se não houver dublado, traz o filme original (inglês)
    if not resultados:
        resultados = fazer_busca(titulo)
        
    return resultados

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
    
    # Executa o SEU raspador blindado
    lista_torrents = buscar_torrents_1377x_seguro(titulo)
    
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
