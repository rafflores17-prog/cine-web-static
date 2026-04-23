from flask import Flask, render_template, request
import requests
import urllib.parse
import unicodedata
import re

app = Flask(__name__)

TMDB_API_KEY = "c90fb79a2f7d756a49bee848bce5f413"
IMG_PATH = "https://image.tmdb.org/t/p/w500"
BG_PATH = "https://image.tmdb.org/t/p/original"

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

def remover_acentos_e_pontuacao(txt):
    txt = str(txt)
    txt = ''.join(c for c in unicodedata.normalize('NFD', txt) if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^\w\s]', '', txt).lower()

# ==========================================================
# ⚡ SCRIPT UNIVERSAL (BYPASS DE IMDB)
# ==========================================================
def buscar_torrents_api(titulo_br, titulo_original, imdb_id):
    try:
        base_url = "https://torrent-api-t1ml.onrender.com/streams"
        
        # 🔥 COMUNICAÇÃO CORRIGIDA: Agora o Python manda o "br" e o "orig" para o Node.js
        url = f"{base_url}?br={urllib.parse.quote(titulo_br)}&orig={urllib.parse.quote(titulo_original)}&imdb={imdb_id}"
        r = requests.get(url, timeout=15)
        data = r.json()

        resultados = []

        palavras_br = [p for p in remover_acentos_e_pontuacao(titulo_br).split() if len(p) > 1][:2]
        palavras_orig = [p for p in remover_acentos_e_pontuacao(titulo_original).split() if len(p) > 1][:2]

        def processar_resultados(streams_data):
            for item in streams_data:
                nome_completo = item.get("title", "")
                nome_lower = remover_acentos_e_pontuacao(nome_completo)

                if len(nome_completo) < 5:
                    continue

                # 🛡️ VIA EXPRESSA (BYPASS): 
                # Se veio do Brazuca ou do Torrentio, é porque achou pelo IMDB. 
                # O IMDB NUNCA ERRA! Deixa passar direto sem checar as palavras!
                is_trusted = "brazuca" in nome_lower or "torrentio" in nome_lower

                valido_br = all(p in nome_lower for p in palavras_br) if palavras_br else False
                valido_orig = all(p in nome_lower for p in palavras_orig) if palavras_orig else False
                
                # Se NÃO for confiável (ex: PirateBay), aí sim a gente checa as palavras
                if not is_trusted and not (valido_br or valido_orig):
                    continue

                score = 0
                is_br = False
                
                if any(x in nome_lower for x in ["dublado", "dual", "ptbr", "portuguese", "brazuca"]):
                    score += 5
                    is_br = True
                
                qualidade = "HD 📺"
                if "2160p" in nome_lower or "4k" in nome_lower:
                    qualidade = "4K 🌟"
                    score += 4
                elif "1080p" in nome_lower:
                    qualidade = "1080p 📺"
                    score += 3
                elif "720p" in nome_lower:
                    qualidade = "720p 📱"
                    score += 2

                idioma_tag = "🇧🇷 Dublado/Dual" if is_br else "🌐 Original"

                resultados.append({
                    "nome": nome_completo,
                    "tamanho": item.get('size', 'N/A'),
                    "qualidade": qualidade,
                    "idioma": idioma_tag,
                    "magnet": item.get("magnet"),
                    "score": score
                })

        processar_resultados(data.get("streams", []))

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
    titulo_original = filme.get('original_title', titulo_br)
    imdb_id = filme.get('imdb_id') or ""

    # Chama a API enviando tudo!
    lista_torrents = buscar_torrents_api(titulo_br, titulo_original, imdb_id)
    
    titulo_exato = urllib.parse.quote(f'"{titulo_br}"')
    link_busca_online = f"https://www.google.com/search?q=assistir+{titulo_exato}+dublado+online+gratis+hd"
    titulo_limpo = urllib.parse.quote(titulo_br)
    busca_magnet = f"https://duckduckgo.com/?q={titulo_limpo}+torrent+dublado+1080p+dual+audio"

    return render_template("detalhes.html", filme=filme, img_base=IMG_PATH, bg_base=BG_PATH, trailer=trailer_key, busca_online=link_busca_online, lista_torrents=lista_torrents, busca_magnet=busca_magnet)

if __name__ == "__main__":
    app.run()
