from flask import Flask, render_template, request
import requests
import urllib.parse
import unicodedata
import re

app = Flask(__name__)

# 🔑 SUA API TMDB
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
# ⚡ API TORRENT + BLINDAGEM MÁXIMA ANTI-LIXO
# ==========================================================
def remover_acentos_e_pontuacao(txt):
    """Limpa o texto tirando acentos, vírgulas e pontos para a comparação ser perfeita"""
    txt = str(txt)
    # Tira os acentos (ex: Demônio vira Demonio)
    txt = ''.join(c for c in unicodedata.normalize('NFD', txt) if unicodedata.category(c) != 'Mn')
    # Tira pontuação e deixa tudo minúsculo
    return re.sub(r'[^\w\s]', '', txt).lower()

def buscar_torrents_api(titulo_br, titulo_original):
    try:
        base_url = "https://torrent-api-t1ml.onrender.com/streams"
        url = f"{base_url}?q={urllib.parse.quote(titulo_br)}"
        r = requests.get(url, timeout=15)
        data = r.json()

        resultados = []

        # 🛡️ CRIA AS PALAVRAS-CHAVE LIMPAS (Sem acentos)
        palavras = remover_acentos_e_pontuacao(titulo_br).split()
        if titulo_original:
            palavras += remover_acentos_e_pontuacao(titulo_original).split()
            
        # Pega só palavras grandes (ignora 'o', 'de', 'as')
        palavras_chave = [p for p in palavras if len(p) > 2]

        def processar_resultados(streams_data):
            for item in streams_data:
                nome_completo = item.get("title", "")
                # Limpa o nome do arquivo pirata também
                nome_lower = remover_acentos_e_pontuacao(nome_completo)

                if len(nome_completo) < 5:
                    continue

                # 🛡️ O SEGURANÇA DA BOATE: 
                # Se o nome do arquivo não tiver NENHUMA palavra do título, JOGA NO LIXO!
                valido = False
                for palavra in palavras_chave:
                    if palavra in nome_lower:
                        valido = True
                        break
                
                if not valido:
                    continue  # ADEUS KUNG FU PANDA E DEADPOOL!

                score = 0
                if any(x in nome_lower for x in ["dublado", "dual", "pt", "br", "portuguese"]):
                    score += 5
                if "1080p" in nome_lower:
                    score += 3
                elif "720p" in nome_lower:
                    score += 2

                resultados.append({
                    "nome": nome_completo,
                    "tamanho": item.get("size", "N/A"),
                    "magnet": item.get("magnet"),
                    "score": score
                })

        # 1. Processa a busca em Português
        processar_resultados(data.get("streams", []))

        # 2. PLANO B AUTOMÁTICO (Busca em Inglês se o BR vier vazio)
        if not resultados and titulo_original and titulo_br.lower() != titulo_original.lower():
            url_orig = f"{base_url}?q={urllib.parse.quote(titulo_original)}"
            r_orig = requests.get(url_orig, timeout=15)
            processar_resultados(r_orig.json().get("streams", []))

        # 🔁 Remove duplicados e ordena (Dublados no topo)
        vistos = set()
        unicos = []
        for t in resultados:
            if t["magnet"] not in vistos:
                vistos.add(t["magnet"])
                unicos.append(t)

        unicos.sort(key=lambda x: x["score"], reverse=True)
        return unicos[:10]

    except Exception as e:
        print("Erro API:", e)
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

    titulo_br = filme.get('title', '')
    titulo_original = filme.get('original_title', titulo_br)

    # ⚡ Busca Blindada e Inteligente (Passa os dois nomes)
    lista_torrents = buscar_torrents_api(titulo_br, titulo_original)

    titulo_exato = urllib.parse.quote(f'"{titulo_br}"')
    link_busca_online = f"https://www.google.com/search?q=assistir+{titulo_exato}+dublado+online+gratis+hd"

    titulo_limpo = urllib.parse.quote(titulo_br)
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

if __name__ == "__main__":
    app.run()
