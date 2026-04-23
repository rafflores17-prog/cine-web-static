from flask import Flask, render_template, request
import requests
import urllib.parse

app = Flask(__name__)

# 🔑 SUA API TMDB (MANTIDA)
TMDB_API_KEY = "c90fb79a2f7d756a49bee848bce5f413"

IMG_PATH = "https://image.tmdb.org/t/p/w500"
BG_PATH = "https://image.tmdb.org/t/p/original"

# ==========================================================
# 🎬 TMDB
# ==========================================================
def get_tmdb_data(endpoint, params={}):
    base = "https://api.themoviedb.org/3"
    p = {"api_key": TMDB_API_KEY, "language": "pt-BR", **params}
    try:
        return requests.get(f"{base}/{endpoint}", params=p, timeout=8).json()
    except:
        return {}

def get_trailer(filme_id):
    data = get_tmdb_data(f"movie/{filme_id}/videos")
    for video in data.get('results', []):
        if video.get('site') == 'YouTube' and video.get('type') == 'Trailer':
            return video.get('key')
    return None

# ==========================================================
# ⚡ API TORRENT OTIMIZADA (CONECTADA AO SEU NODE.JS)
# ==========================================================
def buscar_torrents_api(titulo):
    try:
        base_url = "https://torrent-api-t1ml.onrender.com/streams"

        # 🔥 SOMENTE O TÍTULO (Removido o ano para não enlouquecer o 1377x)
        url = f"{base_url}?q={urllib.parse.quote(titulo)}"
        
        # Aumentei o timeout para 15s para garantir que sua API Node tenha tempo de responder
        r = requests.get(url, timeout=15)
        data = r.json()

        resultados = []

        for item in data.get("streams", []):
            nome_completo = item.get("title", "")
            nome_lower = nome_completo.lower()

            # 🚫 filtro básico (remove lixo extremo)
            if len(nome_completo) < 5:
                continue

            score = 0

            # 🇧🇷 prioridade (sem bloquear)
            if any(x in nome_lower for x in ["dublado", "dual", "pt", "br"]):
                score += 5

            # 🎬 qualidade
            if "1080p" in nome_lower:
                score += 3
            elif "720p" in nome_lower:
                score += 2

            resultados.append({
                # 🔥 Sem o limite de caracteres para o nome ficar completo
                "nome": nome_completo,
                "tamanho": item.get("size", "N/A"),
                "magnet": item.get("magnet"),
                "score": score
            })

        # 🔁 remover duplicados
        vistos = set()
        unicos = []
        for t in resultados:
            if t["magnet"] not in vistos:
                vistos.add(t["magnet"])
                unicos.append(t)

        # 🔥 ordenar melhores
        unicos.sort(key=lambda x: x["score"], reverse=True)

        return unicos[:10]

    except Exception as e:
        print("Erro API:", e)
        return []

# ==========================================================
# ROTAS
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
        filmes = get_tmdb_data("discover/movie", {
            "with_genres": genero,
            "sort_by": "popularity.desc"
        }).get('results', [])
        listas.append({"titulo": "🎭 Filmes Encontrados", "filmes": filmes})

    elif ano:
        filmes = get_tmdb_data("discover/movie", {
            "primary_release_date.gte": f"{ano}-01-01",
            "primary_release_date.lte": f"{int(ano)+9}-12-31",
            "sort_by": "popularity.desc"
        }).get('results', [])
        listas.append({"titulo": f"🎞️ Clássicos dos Anos {ano}", "filmes": filmes})

    else:
        listas.append({
            "titulo": "🔥 Lançamentos",
            "filmes": get_tmdb_data("movie/now_playing", {"region": "BR"}).get('results', [])[:15]
        })
        listas.append({
            "titulo": "🌟 Mais Populares",
            "filmes": get_tmdb_data("movie/popular", {"region": "BR"}).get('results', [])[:15]
        })
        listas.append({
            "titulo": "👻 Terror e Suspense",
            "filmes": get_tmdb_data("discover/movie", {"with_genres": "27,53"}).get('results', [])[:15]
        })
        listas.append({
            "titulo": "💥 Ação e Aventura",
            "filmes": get_tmdb_data("discover/movie", {"with_genres": "28,12"}).get('results', [])[:15]
        })

    return render_template("index.html", listas=listas, img_base=IMG_PATH)

# ==========================================================
@app.route('/filme/<int:filme_id>')
def detalhes_filme(filme_id):
    filme = get_tmdb_data(f"movie/{filme_id}")
    trailer_key = get_trailer(filme_id)

    titulo = filme.get('title', '')
    
    # ⚡ Busca rápida na SUA API (Apenas com o Titulo)
    lista_torrents = buscar_torrents_api(titulo)

    titulo_exato = urllib.parse.quote(f'"{titulo}"')
    link_busca_online = f"https://www.google.com/search?q=assistir+{titulo_exato}+dublado+online+gratis+hd"

    titulo_limpo = urllib.parse.quote(titulo)
    busca_magnet = f"https://duckduckgo.com/?q={titulo_limpo}+torrent+dublado+1080p"

    return render_template(
        "detalhes.html",
        filme=filme,
        img_base=IMG_PATH,
        bg_base=BG_PATH,
        trailer=trailer_key,
        busca_online=link_busca_online,
        lista_torrents=lista_torrents,
        busca_magnet=busca_magnet
    )

# ==========================================================
if __name__ == "__main__":
    app.run()
