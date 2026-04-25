import os
import time
import requests
from flask import Flask, jsonify, request
from bs4 import BeautifulSoup
from threading import Lock

app = Flask(__name__)

# ==============================
# CONFIG
# ==============================

TIMEOUT = 10
CACHE_TTL = 300  # 5 minutos
RETRIES = 2

# ==============================
# SERVIDORES (fallback)
# ==============================

SERVIDORES = [

    # MELHOR
    {
        "nome": "Serv99",
        "tipo": "api",
        "host": "http://serv99.xyz:8880",
        "user": "261491762",
        "pass": "2516895925"
    },

    {
        "nome": "Falcon",
        "tipo": "m3u",
        "url": "http://falcon12.top:80/get.php?username=175473583&password=643238922&type=m3u_plus&output=ts"
    },

    {
        "nome": "Dark1",
        "tipo": "m3u",
        "url": "http://d4rk.info:80/get.php?username=GLedsoonn777&password=PErtilee444&type=m3u_plus&output=ts"
    },

    {
        "nome": "Dark2",
        "tipo": "m3u",
        "url": "http://d4rk.info:80/get.php?username=21998570202&password=Asd7920&type=m3u_plus&output=ts"
    },

    {
        "nome": "Techon",
        "tipo": "api",
        "host": "http://techon.one:80",
        "user": "",
        "pass": ""
    },

    {
        "nome": "Stmax",
        "tipo": "api",
        "host": "http://stmax.top:80",
        "user": "",
        "pass": ""
    }

]

# ==============================
# CACHE SIMPLES (memória)
# ==============================

cache = {}
cache_lock = Lock()


def get_cache(key):

    with cache_lock:

        if key in cache:

            data, timestamp = cache[key]

            if time.time() - timestamp < CACHE_TTL:
                return data

            del cache[key]

    return None


def set_cache(key, data):

    with cache_lock:
        cache[key] = (data, time.time())


# ==============================
# REQUEST COM RETRY
# ==============================

def fetch_url(url):

    for _ in range(RETRIES):

        try:

            response = requests.get(
                url,
                timeout=TIMEOUT,
                headers={
                    "User-Agent": "Mozilla/5.0"
                }
            )

            if response.status_code == 200:
                return response.text

        except Exception:
            pass

    return None


# ==============================
# BUSCA COM FALLBACK
# ==============================

def buscar_filme(nome):

    cache_key = f"busca:{nome}"

    cached = get_cache(cache_key)

    if cached:
        return cached

    for servidor in SERVIDORES:

        try:

            print("Tentando:", servidor["nome"])

            if servidor["tipo"] == "api":

                if not servidor["user"]:
                    continue

                url = (
                    f"{servidor['host']}/player_api.php"
                    f"?username={servidor['user']}"
                    f"&password={servidor['pass']}"
                    f"&action=get_vod_streams"
                )

                data = fetch_url(url)

                if not data:
                    continue

                if nome.lower() in data.lower():

                    set_cache(cache_key, data)

                    return data

            elif servidor["tipo"] == "m3u":

                data = fetch_url(servidor["url"])

                if not data:
                    continue

                if nome.lower() in data.lower():

                    set_cache(cache_key, data)

                    return data

        except Exception as e:

            print("Erro servidor:", e)

            continue

    return None


# ==============================
# ROTAS
# ==============================

@app.route("/")
def home():

    return jsonify({
        "status": "online",
        "cache": len(cache),
        "servidores": len(SERVIDORES)
    })


@app.route("/buscar")
def buscar():

    nome = request.args.get("nome")

    if not nome:
        return jsonify({
            "erro": "Informe ?nome=filme"
        }), 400

    resultado = buscar_filme(nome)

    if resultado:

        return jsonify({
            "status": "ok",
            "fonte": "fallback",
            "tamanho": len(resultado)
        })

    return jsonify({
        "status": "nao_encontrado"
    })


@app.route("/health")
def health():

    return "OK", 200


# ==============================
# START (Koyeb / Render / Railway)
# ==============================

if __name__ == "__main__":

    PORT = int(os.environ.get("PORT", 8000))

    app.run(
        host="0.0.0.0",
        port=PORT,
        threaded=True
    )
