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

# ==========================================================
# 🚀 MOTOR APIBAY (O Maior do Mundo + Filtro de Segurança)
# ==========================================================
def buscar_torrents_apibay(titulo_br, titulo_original):
    """Busca no PirateBay filtrando apenas Vídeos/Filmes (Categoria 200+)"""
    
    def fazer_busca(query):
        url = f"https://apibay.org/q.php?q={urllib.parse.quote(query)}"
        try:
            return requests.get(url, timeout=8).json()
        except:
            return []

    # 1. Tenta achar Dublado primeiro
    resultados = fazer_busca(f"{titulo_br} dublado")
    
    # Se a API retornar vazio ou com id '0' (No results), tenta o nome original
    if not resultados or resultados[0].get('id') == '0':
        resultados = fazer_busca(titulo_original)
        
    torrents = []
    if resultados and resultados[0].get('id') != '0':
        for t in resultados:
            # FILTRO DE BLINDAGEM: Apenas categorias de Vídeo (Começam com 2)
            cat = str(t.get('category', '0'))
            if cat.startswith('2'): 
                nome = t.get('name', 'Sem nome')
                hash_str = t.get('info_hash', '')
                
                # Monta o magnet link original do PirateBay
                magnet = f"magnet:?xt=urn:btih:{hash_str}&dn={urllib.parse.quote(nome)}"
                
                # Calcula o tamanho de Bytes para GB ou MB
                try:
                    size_bytes = int(t.get('size', 0))
                    tamanho = f"{size_bytes / 1073741824:.2f} GB" if size_bytes > 1073741824 else f"{size_bytes / 1048576:.2f} MB"
                except:
                    tamanho = "N/A"

                torrents.append({
                    "nome": nome[:55] + "..." if len(nome) > 55 else nome,
                    "tamanho": tamanho,
                    "magnet": magnet
                })
            
            # Pára quando tiver 5 resultados válidos e limpos
            if len(torrents) >= 5:
                break
                
    return torrents

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
    
    titulo_br = filme.get('title', '')
    # Tenta pegar o nome em inglês para ter plano B, se não tiver, usa o BR mesmo
    titulo_original = filme.get('original_title', titulo_br)
    
    # Executa a busca blindada do PirateBay
    lista_torrents = buscar_torrents_apibay(titulo_br, titulo_original)
    
    titulo_exato = urllib.parse.quote(f'"{titulo_br}"')
    link_busca_online = f"https://www.google.com/search?q=assistir+{titulo_exato}+dublado+online+gratis+hd"
    
    titulo_limpo = urllib.parse.quote(titulo_br)
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
