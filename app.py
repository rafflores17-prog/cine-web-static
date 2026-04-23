from flask import Flask, render_template, request
import requests
import urllib.parse
import unicodedata
import re

app = Flask(__name__)

TMDB_API_KEY = "c90fb79a2f7d756a49bee848bce5f413"
IMG_PATH = "https://image.tmdb.org/t/p/w500"
BG_PATH = "https://image.tmdb.org/t/p/original"

# ================= TMDB =================
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

# ================= UTILS =================
def limpar(txt):
    txt = str(txt)
    txt = ''.join(c for c in unicodedata.normalize('NFD', txt) if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^\w\s]', '', txt).lower()

# ==========================================================
# 🚀 BUSCA DE TORRENTS (VERSÃO FINAL)
# ==========================================================
def buscar_torrents_api(titulo_br, titulo_original, imdb_id, ano=""):
    try:
        base_url = "https://torrent-api-t1ml.onrender.com/streams"

        url = f"{base_url}?br={urllib.parse.quote(titulo_br)}&orig={urllib.parse.quote(titulo_original)}&imdb={imdb_id}&year={ano}"

        r = requests.get(url, timeout=15)
        data = r.json()

        resultados = []

        palavras = list(set(
            limpar(titulo_br).split()[:2] +
            limpar(titulo_original).split()[:2]
        ))

        for item in data.get("streams", []):
            nome = item.get("title", "")
            nome_lower = limpar(nome)

            if len(nome) < 5:
                continue

            # 🚫 ANTI LIXO FORTE
            blacklist = [
                "apk","android","windows","linux","mac","crack",
                "software","game","setup","tool","plugin","iso","repack",
                "adobe","photoshop","office"
            ]
            if any(b in nome_lower for b in blacklist):
                continue

            # 🔥 MATCH FLEXÍVEL
            match = any(p in nome_lower for p in palavras)

            is_brazuca = "brazuca" in nome_lower
            is_torrentio = "torrentio" in nome_lower

            score = 0
            is_br = False

            if is_brazuca:
                score += 100
                is_br = True
            elif is_torrentio:
                score += 70

            if match:
                score += 20

            if any(x in nome_lower for x in ["dublado","dual","ptbr","portuguese"]):
                score += 20
                is_br = True

            # qualidade
            qualidade = "SD"
            if "2160p" in nome_lower or "4k" in nome_lower:
                qualidade = "4K"
                score += 5
            elif "1080p" in nome_lower:
                qualidade = "1080p"
                score += 4
            elif "720p" in nome_lower:
                qualidade = "720p"
                score += 3

            resultados.append({
                "nome": nome,
                "tamanho": item.get("size", "N/A"),
                "qualidade": qualidade,
                "idioma": "🇧🇷 Dublado" if is_br else "🌐 Original",
                "magnet": item.get("magnet"),
                "score": score
            })

        # remove duplicados
        vistos = set()
        unicos = []
        for t in resultados:
            if t["magnet"] not in vistos:
                vistos.add(t["magnet"])
                unicos.append(t)

        unicos.sort(key=lambda x: x["score"], reverse=True)

        return unicos[:20]

    except Exception as e:
        print("Erro API:", e)
        return []

# ================= ROTAS =================
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
        filmes = get_tmdb_data("discover/movie", {"with_genres": genero}).get('results', [])
        listas.append({"titulo": "🎭 Filmes Encontrados", "filmes": filmes})

    elif ano:
        filmes = get_tmdb_data("discover/movie", {
            "primary_release_date.gte": f"{ano}-01-01",
            "primary_release_date.lte": f"{int(ano)+9}-12-31"
        }).get('results', [])
        listas.append({"titulo": f"🎞️ Clássicos dos Anos {ano}", "filmes": filmes})

    else:
        listas.append({"titulo": "🔥 Lançamentos", "filmes": get_tmdb_data("movie/now_playing").get('results', [])[:15]})
        listas.append({"titulo": "🌟 Populares", "filmes": get_tmdb_data("movie/popular").get('results', [])[:15]})
        listas.append({"titulo": "👻 Terror", "filmes": get_tmdb_data("discover/movie", {"with_genres": "27"}).get('results', [])[:15]})

    return render_template("index.html", listas=listas, img_base=IMG_PATH)

@app.route('/filme/<int:filme_id>')
def detalhes_filme(filme_id):
    filme = get_tmdb_data(f"movie/{filme_id}")
    trailer_key = get_trailer(filme_id)

    titulo_br = filme.get('title', '')
    titulo_original = filme.get('original_title', titulo_br)
    imdb_id = filme.get('imdb_id') or ""
    ano = filme.get("release_date", "")[:4]

    lista_torrents = buscar_torrents_api(titulo_br, titulo_original, imdb_id, ano)

    # 🔥 FALLBACK AUTOMÁTICO
    if not lista_torrents:
        lista_torrents = buscar_torrents_api(titulo_original, titulo_original, imdb_id, ano)

    titulo_exato = urllib.parse.quote(f'"{titulo_br}"')
    link_busca_online = f"https://www.google.com/search?q=assistir+{titulo_exato}+dublado"
    titulo_limpo = urllib.parse.quote(titulo_br)
    busca_magnet = f"https://duckduckgo.com/?q={titulo_limpo}+torrent+dublado"

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

if __name__ == "__main__":
    app.run(debug=True)
