import os
import re
import requests
import difflib
from flask import Flask, request, redirect

app = Flask(__name__)

M3U_URL = "https://github.com/StartStatic1/meus-apks/releases/download/V_backup/lista.m3u"
ARQUIVO_MANUAL = "manual.txt"

catalogo_filmes = {}

def limpar(nome):
    nome = str(nome).lower()
    # Tradução de algarismos para bater com a lista
    nome = re.sub(r'\bii\b', '2', nome).replace('parte ii', '2')
    nome = re.sub(r'\biii\b', '3', nome).replace('parte iii', '3')
    nome = re.sub(r'\biv\b', '4', nome)
    # Limpeza de lixo
    nome = re.sub(r'\b(parte|filme|dublado|legendado|fhd|4k|hdtv|sd|720p|1080p)\b', '', nome)
    nome = re.sub(r"[\[\]\(\):.\-]", " ", nome)
    return " ".join(nome.split()).strip()

def carregar_arquivos():
    print("⏳ Carregando catálogo...")
    try:
        r = requests.get(M3U_URL, stream=True, timeout=60)
        linhas = [l.decode('utf-8', errors='ignore') for l in r.iter_lines() if l]
        for i in range(len(linhas)):
            linha = linhas[i].strip()
            if linha.startswith("#EXTINF"):
                nome_limpo = limpar(linha.split(",")[-1].strip())
                if i + 1 < len(linhas):
                    link = linhas[i + 1].strip()
                    if "/movie/" in link:
                        catalogo_filmes[nome_limpo] = link
        print(f"✅ {len(catalogo_filmes)} Filmes carregados!")
    except Exception as e: print(f"❌ Erro: {e}")

    if os.path.exists(ARQUIVO_MANUAL):
        with open(ARQUIVO_MANUAL, "r", encoding="utf-8") as f:
            for linha in f:
                if "|" in linha:
                    n, l = linha.split("|", 1)
                    catalogo_filmes[limpar(n)] = l.strip()

carregar_arquivos()

def buscar_sniper(titulo_buscado):
    titulo_limpo = limpar(titulo_buscado)
    
    # 1. TENTA MATCH EXATO PRIMEIRO
    if titulo_limpo in catalogo_filmes:
        return catalogo_filmes[titulo_limpo]

    # Extrai o número do filme (Ex: o 2 de American Pie 2)
    num_busca = re.search(r'\b\d+\b', titulo_limpo)
    num_busca = num_busca.group() if num_busca else None

    melhor_link = None
    maior_score = 0.0

    for nome_cat, link in catalogo_filmes.items():
        # TRAVA DE SEGURANÇA: Se a busca tem número e o catálogo não, ou vice-versa, descarta.
        num_cat = re.search(r'\b\d+\b', nome_cat)
        num_cat = num_cat.group() if num_cat else None
        
        if num_busca != num_cat:
            continue

        # Calcula a similaridade (0.0 a 1.0)
        score = difflib.SequenceMatcher(None, titulo_limpo, nome_cat).ratio()
        
        # Só aceita se for muito parecido (acima de 75%)
        if score > maior_score and score > 0.75:
            maior_score = score
            melhor_link = link

    return melhor_link

@app.route("/buscar")
def buscar():
    titulo = request.args.get("titulo", "")
    link = buscar_sniper(titulo)
    if link:
        return redirect(link)
    return "Filme não encontrado na lista", 404

@app.route("/")
def index():
    return f"Motor Cine Mega Online: {len(catalogo_filmes)} filmes", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
