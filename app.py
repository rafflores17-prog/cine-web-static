import os
import re
import requests
import difflib
from flask import Flask, request, redirect

app = Flask(__name__)

M3U_URL = "https://github.com/StartStatic1/meus-apks/releases/download/V_backup/lista.m3u"
ARQUIVO_MANUAL = "manual.txt"

catalogo_filmes = {}

# 🔥 LIMPEZA FORTE (PADRÃO ÚNICO)
def limpar(nome):
    nome = str(nome).lower()

    # remove coisas inúteis
    nome = re.sub(r'\b(dublado|legendado|hd|fullhd|1080p|720p)\b', '', nome)

    # remove símbolos
    nome = re.sub(r"\[.*?\]", "", nome)
    nome = re.sub(r"\(.*?\)", "", nome)

    # troca separadores
    nome = nome.replace(".", " ").replace("-", " ").replace(":", " ")

    # remove "parte"
    nome = re.sub(r'\bparte\b', '', nome)

    # romanos → números
    romanos = {
        " ii ": " 2 ",
        " iii ": " 3 ",
        " iv ": " 4 ",
        " v ": " 5 ",
        " vi ": " 6 "
    }
    for k, v in romanos.items():
        nome = nome.replace(k, v)

    # remove espaços duplicados
    return " ".join(nome.split()).strip()


# 🔥 CARREGA M3U
def carregar_arquivos():
    print("⏳ Carregando M3U...")

    try:
        r = requests.get(M3U_URL, timeout=60)
        linhas = r.text.splitlines()

        for i in range(len(linhas)):
            if linhas[i].startswith("#EXTINF"):
                nome_sujo = linhas[i].split(",")[-1].strip()
                nome_limpo = limpar(nome_sujo)

                if i + 1 < len(linhas):
                    link = linhas[i + 1].strip()

                    if "/movie/" in link and link.endswith(".mp4"):
                        catalogo_filmes[nome_limpo] = link

        print(f"✅ {len(catalogo_filmes)} filmes carregados!")

    except Exception as e:
        print("❌ ERRO M3U:", e)

    # manual (override)
    if os.path.exists(ARQUIVO_MANUAL):
        try:
            with open(ARQUIVO_MANUAL, "r", encoding="utf-8") as f:
                for linha in f:
                    if "|" in linha:
                        nome, link = linha.split("|", 1)
                        catalogo_filmes[limpar(nome)] = link.strip()
        except:
            pass


carregar_arquivos()


# 🚀 BUSCA NOVA (INTELIGENTE)
def buscar_sniper(titulo_buscado):
    melhor_link = None
    melhor_score = 0.0

    palavras_busca = set(titulo_buscado.split())
    nums_busca = set(re.findall(r'\d+', titulo_buscado))

    for nome_cat, link in catalogo_filmes.items():
        palavras_cat = set(nome_cat.split())
        nums_cat = set(re.findall(r'\d+', nome_cat))

        # ❌ trava erro de franquia
        if nums_busca and nums_cat and nums_busca != nums_cat:
            continue

        # 🔥 match por palavras (ESSENCIAL)
        inter = palavras_busca.intersection(palavras_cat)
        score_palavra = len(inter) / max(len(palavras_busca), 1)

        # 🔥 similaridade geral
        score_texto = difflib.SequenceMatcher(None, titulo_buscado, nome_cat).ratio()

        # 🔥 score final (peso maior palavras)
        score = (score_palavra * 0.75) + (score_texto * 0.25)

        # bônus se contém tudo
        if palavras_busca.issubset(palavras_cat):
            score += 0.2

        if score > melhor_score:
            melhor_score = score
            melhor_link = link

    # 🔥 limite mínimo (evita filme errado)
    if melhor_score >= 0.6:
        return melhor_link, f"Score {melhor_score:.2f}"

    return None, None


@app.route("/buscar")
def buscar():
    titulo = request.args.get("titulo", "")
    titulo_limpo = limpar(titulo)

    if not titulo_limpo:
        return "Erro: vazio", 400

    link, tipo = buscar_sniper(titulo_limpo)

    if link:
        print(f"🎬 OK ({tipo}): {titulo_limpo}")
        return redirect(link)

    print(f"❌ NÃO ENCONTRADO: {titulo_limpo}")
    return "Filme não encontrado", 404


@app.route("/")
def index():
    return f"🎬 Cine Mega Motor OK | Total: {len(catalogo_filmes)}"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
