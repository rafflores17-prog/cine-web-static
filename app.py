import requests
import re
import time

# ================================
# CONFIG
# ================================

CACHE_LISTAS = {}
CACHE_TEMPO = 300  # 5 minutos

TIMEOUT = 8

# ================================
# SERVIDORES
# ================================

SERVIDORES = [

    # ================= M3U =================

    {
        "nome": "Falcon",
        "tipo": "m3u",
        "url": "http://falcon12.top:80/get.php?username=175473583&password=643238922&type=m3u_plus&output=ts"
    },

    {
        "nome": "Dark 1",
        "tipo": "m3u",
        "url": "http://d4rk.info:80/get.php?username=GLedsoonn777&password=PErtilee444&type=m3u_plus&output=ts"
    },

    {
        "nome": "Dark 2",
        "tipo": "m3u",
        "url": "http://d4rk.info:80/get.php?username=21998570202&password=Asd7920&type=m3u_plus&output=ts"
    },

    # ================= API =================

    {
        "nome": "Techon",
        "tipo": "api",
        "host": "http://techon.one:80",
        "user": "",
        "pass": ""
    },

    {
        "nome": "Serv99",
        "tipo": "api",
        "host": "http://serv99.xyz:8880",
        "user": "261491762",
        "pass": "2516895925"
    },

    {
        "nome": "Stmax",
        "tipo": "api",
        "host": "http://stmax.top:80",
        "user": "",
        "pass": ""
    },

    # ================= FALLBACK FINAL =================

    {
        "nome": "Koquwz",
        "tipo": "api",
        "host": "http://koquwz.com:80",
        "user": "",
        "pass": ""
    }

]

# ================================
# FUNÇÕES
# ================================

def limpar_texto(txt):

    if not txt:
        return ""

    return re.sub(
        r'[^\w\s]',
        '',
        txt
    ).lower().strip()


# ================================
# CARREGAR M3U COM CACHE
# ================================

def carregar_lista_m3u(url):

    agora = time.time()

    if url in CACHE_LISTAS:

        dados = CACHE_LISTAS[url]

        if agora - dados["tempo"] < CACHE_TEMPO:

            return dados["lista"]

    try:

        r = requests.get(
            url,
            timeout=TIMEOUT
        )

        if r.status_code != 200:
            return []

        linhas = r.text.splitlines()

        lista = []
        nome = None

        for linha in linhas:

            if linha.startswith("#EXTINF"):

                nome = linha.split(",")[-1]

            elif linha.startswith("http"):

                lista.append({

                    "nome": nome,
                    "url": linha

                })

        CACHE_LISTAS[url] = {

            "tempo": agora,
            "lista": lista

        }

        print("Lista carregada:", url)

        return lista

    except Exception as e:

        print("Erro lista:", url)

        return []


# ================================
# BUSCAR VIA API
# ================================

def buscar_api(srv, titulo_busca):

    try:

        url_api = (

            f"{srv['host']}/player_api.php"
            f"?username={srv['user']}"
            f"&password={srv['pass']}"
            f"&action=get_vod_streams"

        )

        r = requests.get(
            url_api,
            timeout=TIMEOUT
        )

        if r.status_code != 200:
            return None

        lista = r.json()

        for item in lista:

            nome = limpar_texto(

                item.get("name")

            )

            if titulo_busca in nome:

                video_url = (

                    f"{srv['host']}/movie/"
                    f"{srv['user']}/"
                    f"{srv['pass']}/"
                    f"{item.get('stream_id')}.mp4"

                )

                print(
                    "Encontrado em:",
                    srv["nome"]
                )

                return "/proxy?url=" + video_url

    except Exception:

        print(
            "Erro API:",
            srv["nome"]
        )

    return None


# ================================
# BUSCAR FILME COM FALLBACK
# ================================

def buscar_filme_fallback(titulo):

    titulo_busca = limpar_texto(titulo)

    for srv in SERVIDORES:

        print(
            "Tentando:",
            srv["nome"]
        )

        # ================= M3U =================

        if srv["tipo"] == "m3u":

            lista = carregar_lista_m3u(

                srv["url"]

            )

            for item in lista:

                nome = limpar_texto(

                    item["nome"]

                )

                if titulo_busca in nome:

                    print(
                        "Encontrado em:",
                        srv["nome"]
                    )

                    return "/proxy?url=" + item["url"]

        # ================= API =================

        elif srv["tipo"] == "api":

            resultado = buscar_api(

                srv,
                titulo_busca

            )

            if resultado:

                return resultado

    print("Filme não encontrado")

    return None
