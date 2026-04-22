from flask import Flask, render_template, request
import requests
import urllib.parse

app = Flask(__name__)

TMDB_API_KEY = "c90fb79a2f7d756a49bee848bce5f413"
IMG_PATH = "https://image.tmdb.org/t/p/w500"
BG_PATH = "https://image.tmdb.org/t/p/original"

# Trackers públicos ultra-rápidos (Baseados na sua análise!)
TRACKERS = (
    "&tr=udp://tracker.openbittorrent.com:80/announce"
    "&tr=udp://tracker.opentrackr.org:1337/announce"
    "&tr=udp://tracker.coppersurfer.tk:6969/announce"
    "&tr=udp://p4p.arenabg.com:1337/announce"
)

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
# 🚀 MOTOR TORRENTIO (O Motor do Stremio - Focado em DUAL/PT-BR)
# ==========================================================
def buscar_torrents_stremio(imdb_id, titulo):
    if not imdb_id:
        return []
        
    try:
        # A API do Torrentio raspa todos os indexadores do mundo pelo ID do IMDB
        url = f"https://torrentio.strem.fun/stream/movie/{imdb_id}.json"
        resposta = requests.get(url, timeout=8).json()
        streams = resposta.get('streams', [])
        
        torrents_br = []
        torrents_originais = []
        titulo_encode = urllib.parse.quote(titulo)
        
        for s in streams:
            info_hash = s.get('infoHash')
            if not info_hash:
                continue
                
            # O nome do arquivo e os detalhes vêm misturados no título
            title_completo = s.get('title', '')
            nome_fonte = s.get('name', 'Torrent')
            
            # Formata o nome para ficar bonito no layout
            partes = title_completo.split('\n')
            nome_limpo = partes[0][:50] + "..." if len(partes[0]) > 50 else partes[0]
            detalhes = partes[1] if len(partes) > 1 else "Tamanho não informado"
            
            # Monta o magnet link com os trackers que você descobriu
            magnet = f"magnet:?xt=urn:btih:{info_hash}&dn={titulo_encode}{TRACKERS}"
            
            item = {
                "nome": f"[{nome_fonte}] {nome_limpo}",
                "tamanho": detalhes.replace('👤', 'Seeds:').replace('💾', '| Tamanho:'),
                "magnet": magnet
            }
            
            # Filtra separando o que é do Brasil e o que é Gringo
            if 'dublado' in title_completo.lower() or 'dual' in title_completo.lower() or 'pt-br' in title_completo.lower():
                torrents_br.append(item)
            else:
                torrents_originais.append(item)

        # Retorna primeiro os Brasileiros (se tiver). Se não, manda os originais.
        resultados = torrents_br[:5] if torrents_br else torrents_originais[:5]
        return resultados

    except Exception as e:
        print("Erro no Torrentio:", e)
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
    imdb_id = filme.get('imdb_id', '')
    
    # Executa a nova busca do Torrentio
    lista_torrents = buscar_torrents_stremio(imdb_id, titulo)
    
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
