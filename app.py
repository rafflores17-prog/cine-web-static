from flask import Flask, request, Response, stream_with_context, redirect
import requests
import sqlite3
import random
import os
import unicodedata
import re
import datetime

app = Flask(__name__)

# =========================
# CONFIG
# =========================

LOG_FILE = "logs_erros.txt"

# =========================
# AGENTES
# =========================

AGENTES_VIP = [
    "Mozilla/5.0",
    "okhttp/4.12.0",
    "VLC/3.0.4",
    "Dalvik/2.1.0"
]

# =========================
# SERVIDORES API
# =========================

SERVIDORES_API = [

    {
        "nome": "Srv1",
        "host": "http://servidor1:80",
        "user": "user",
        "pass": "pass"
    }

]

API_CACHE = {}

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
# EXTRAIR NUMERO
# =========================

def extrair_numero(texto):

    numeros = re.findall(
        r'\b\d+\b',
        texto
    )

    if numeros:
        return numeros[0]

    return None

# =========================
# LOG ERROS
# =========================

def registrar_log(titulo, url, erro):

    try:

        agora = datetime.datetime.now()

        linha = (
            f"\n{agora}\n"
            f"FILME: {titulo}\n"
            f"URL: {url}\n"
            f"ERRO: {erro}\n"
            "----------------------\n"
        )

        with open(
            LOG_FILE,
            "a",
            encoding="utf-8"
        ) as f:

            f.write(linha)

    except:
        pass

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

                    n, u = linha.split("|", 1)

                    acervo[
                        limpar_texto(n)
                    ] = u.strip()

    return acervo

print("Carregando listas...")

VIP_CACHE = ler_txt("vips.txt")

GIGANTE_CACHE = ler_txt("Filmes_site.txt")

print("Listas carregadas.")

# =========================
# BUSCA SEGURA
# =========================

def busca_segura(t_limpo, acervo):

    numero_busca = extrair_numero(
        t_limpo
    )

    for nome_db, url in acervo.items():

        if t_limpo == nome_db:
            return url

        if nome_db.startswith(
            t_limpo + " "
        ):
            return url

        if numero_busca:

            numero_nome = extrair_numero(
                nome_db
            )

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

def executar_proxy(url_video, titulo):

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

        if r.status_code >= 400:

            registrar_log(
                titulo,
                url_video,
                "HTTP erro"
            )

            return None

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

        return Response(

            stream_with_context(
                generate()
            ),

            status=r.status_code,

            headers=resp_headers
        )

    except Exception as e:

        registrar_log(
            titulo,
            url_video,
            str(e)
        )

        return None

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

        conn.close()

        if res:
            return res[0]

    except Exception as e:

        registrar_log(
            t_limpo,
            "DB",
            str(e)
        )

    return None

# =========================
# BUSCA API
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

        except Exception as e:

            registrar_log(
                t_limpo,
                "API",
                str(e)
            )

    return None

# =========================
# ROTA
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

    fontes = [

        busca_segura(
            t_limpo,
            VIP_CACHE
        ),

        buscar_nas_apis(
            t_limpo
        ),

        buscar_no_db(
            t_limpo
        ),

        busca_segura(
            t_limpo,
            GIGANTE_CACHE
        )

    ]

    for url in fontes:

        if url:

            resp = executar_proxy(
                url,
                titulo
            )

            if resp:
                return resp

    registrar_log(
        titulo,
        "nenhuma fonte",
        "Filme não encontrado"
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
