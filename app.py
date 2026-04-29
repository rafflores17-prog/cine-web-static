from flask import Flask, request, Response, stream_with_context, redirect
import requests
import sqlite3
import random
import os
import unicodedata
import re

app = Flask(__name__)

# =========================
# AGENTES
# =========================

AGENTES_VIP = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "okhttp/4.12.0",
    "VLC/3.0.4 LibVLC/3.0.4",
    "Dalvik/2.1.0 (Linux; Android 14)",
]

# =========================
# SERVIDORES API
# =========================

SERVIDORES_API = [
    {
        "nome": "Mnba",
        "host": "http://mnba.shop:80",
        "user": "danicamara",
        "pass": "acg2010v",
    },
    {
        "nome": "Dnsrot",
        "host": "http://play.dnsrot.vip:80",
        "user": "sheilalima11",
        "pass": "s6dfkck1jlq",
    },
]

API_CACHE = {}

# =========================
# FRANQUIAS
# =========================

FRANQUIAS_DIRETO_API = [
    "american pie",
    "velozes e furiosos",
    "harry potter",
    "senhor dos aneis",
    "star wars",
    "matrix",
]

# =========================
# LIMPAR TEXTO
# =========================

def limpar_texto(texto):

    if not texto:
        return ""

    texto = ''.join(
        c for c in unicodedata.normalize(
            'NFD',
            str(texto)
        )
        if unicodedata.category(c) != 'Mn'
    )

    texto = re.sub(
        r'[^a-zA-Z0-9\s]',
        ' ',
        texto
    )

    return re.sub(
        r'\s+',
        ' ',
        texto
    ).strip().lower()

# =========================
# EXTRAIR NÚMERO
# =========================

def extrair_numero(texto):

    numeros = re.findall(r'\b\d+\b', texto)

    if numeros:
        return numeros[0]

    return None

# =========================
# CARREGAR TXT
# =========================

def ler_txt(caminho):

    acervo = {}

    if os.path.exists(caminho):

        with open(
            caminho,
            "r",
            encoding="utf-8"
        ) as f:

            for linha in f:

                if "|" in linha:

                    n, u = linha.split(
                        "|",
                        1
                    )

                    acervo[
                        limpar_texto(n)
                    ] = u.strip()

    return acervo

print("Carregando acervos...")

VIP_CACHE = ler_txt("vips.txt")

GIGANTE_CACHE = ler_txt("filmes_site.txt")

print("Acervos carregados.")

# =========================
# BUSCA SEGURA
# =========================

def busca_segura(t_limpo, acervo):

    numero_busca = extrair_numero(t_limpo)

    for nome_db, url in acervo.items():

        if t_limpo == nome_db:
            return url

        if nome_db.startswith(t_limpo + " "):
            return url

        if numero_busca:

            numero_nome = extrair_numero(nome_db)

            if (
                numero_nome
                and numero_nome == numero_busca
                and t_limpo.split()[0] in nome_db
            ):
                return url

    return None

# =========================
# PROXY
# =========================

def executar_proxy(url_video):

    if "archive.org" in url_video.lower():
        return redirect(url_video, code=302)

    agente = random.choice(
        AGENTES_VIP
    )

    headers = {
        "User-Agent": agente,
        "Connection": "keep-alive"
    }

    range_header = request.headers.get(
        "Range"
    )

    if range_header:
        headers["Range"] = range_header

    try:

        r = requests.get(
            url_video,
            headers=headers,
            stream=True,
            timeout=(10, 120),
            allow_redirects=True
        )

        content_type = r.headers.get(
            "Content-Type",
            "application/octet-stream"
        )

        def generate():

            for chunk in r.iter_content(
                chunk_size=1024 * 1024
            ):
                if chunk:
                    yield chunk

        resp_headers = {

            "Accept-Ranges": "bytes",

            "Access-Control-Allow-Origin": "*",

            "Content-Type": content_type,

            "Cache-Control": "no-cache",

            "X-Content-Type-Options": "nosniff"
        }

        if "Content-Range" in r.headers:

            resp_headers[
                "Content-Range"
            ] = r.headers[
                "Content-Range"
            ]

        if "Content-Length" in r.headers:

            resp_headers[
                "Content-Length"
            ] = r.headers[
                "Content-Length"
            ]

        return Response(
            stream_with_context(
                generate()
            ),
            status=r.status_code,
            headers=resp_headers
        )

    except Exception as e:

        print(
            "Erro proxy:",
            e
        )

        return redirect(
            url_video
        )

# =========================
# BUSCA NO DB
# =========================

def buscar_no_db(t_limpo):

    try:

        if not os.path.exists(
            "filmes.db"
        ):
            return None

        conn = sqlite3.connect(
            "filmes.db"
        )

        c = conn.cursor()

        c.execute(
            """
            SELECT url
            FROM filmes
            WHERE nome_busca = ?
            LIMIT 1
            """,
            (
                t_limpo,
            )
        )

        res = c.fetchone()

        if res:

            conn.close()

            return res[0]

        numero_busca = extrair_numero(
            t_limpo
        )

        if numero_busca:

            c.execute(
                """
                SELECT url, nome_busca
                FROM filmes
                WHERE nome_busca LIKE ?
                """,
                (
                    f"%{numero_busca}%",
                )
            )

            resultados = c.fetchall()

            for url, nome in resultados:

                numero_nome = extrair_numero(
                    nome
                )

                if numero_nome == numero_busca:

                    conn.close()

                    return url

        conn.close()

    except Exception as e:

        print(
            "Erro DB:",
            e
        )

    return None

# =========================
# BUSCA NAS APIs
# =========================

def buscar_nas_apis(t_limpo):

    numero_busca = extrair_numero(
        t_limpo
    )

    for srv in SERVIDORES_API:

        try:

            if srv["nome"] in API_CACHE:

                dados = API_CACHE[
                    srv["nome"]
                ]

            else:

                url_api = (
                    f"{srv['host']}/player_api.php"
                    f"?username={srv['user']}"
                    f"&password={srv['pass']}"
                    f"&action=get_vod_streams"
                )

                dados = requests.get(
                    url_api,
                    timeout=5
                ).json()

                API_CACHE[
                    srv["nome"]
                ] = dados

            # MATCH EXATO

            for item in dados:

                nome_api = limpar_texto(
                    item.get("name", "")
                )

                if t_limpo == nome_api:

                    return (
                        f"{srv['host']}/movie/"
                        f"{srv['user']}/"
                        f"{srv['pass']}/"
                        f"{item.get('stream_id')}.mp4"
                    )

            # MATCH POR NÚMERO

            if numero_busca:

                for item in dados:

                    nome_api = limpar_texto(
                        item.get("name", "")
                    )

                    numero_nome = extrair_numero(
                        nome_api
                    )

                    if (
                        numero_nome
                        and numero_nome == numero_busca
                        and t_limpo.split()[0] in nome_api
                    ):

                        return (
                            f"{srv['host']}/movie/"
                            f"{srv['user']}/"
                            f"{srv['pass']}/"
                            f"{item.get('stream_id')}.mp4"
                        )

        except Exception as e:

            print(
                "Erro API:",
                e
            )

    return None

# =========================
# ROTA PRINCIPAL
# =========================

@app.route("/buscar")

def buscar():

    titulo = request.args.get(
        "titulo"
    )

    if not titulo:

        return "Título vazio", 400

    t_limpo = limpar_texto(
        titulo
    )

    print(
        "Buscando:",
        t_limpo
    )

    # VIP

    url = busca_segura(
        t_limpo,
        VIP_CACHE
    )

    if url:

        print("VIP")

        return executar_proxy(
            url
        )

    # FRANQUIA

    is_franquia = any(
        f in t_limpo
        for f in FRANQUIAS_DIRETO_API
    )

    if is_franquia:

        url = buscar_nas_apis(
            t_limpo
        )

        if url:

            print("API franquia")

            return executar_proxy(
                url
            )

    # DB

    url = buscar_no_db(
        t_limpo
    )

    if url:

        print("DB")

        return executar_proxy(
            url
        )

    # API

    url = buscar_nas_apis(
        t_limpo
    )

    if url:

        print("API")

        return executar_proxy(
            url
        )

    # GIGANTE

    url = busca_segura(
        t_limpo,
        GIGANTE_CACHE
    )

    if url:

        print("GIGANTE")

        return executar_proxy(
            url
        )

    return "Filme não encontrado", 404

# =========================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=int(
            os.environ.get(
                "PORT",
                8000
            )
        )
    )
