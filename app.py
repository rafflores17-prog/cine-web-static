import os
import re
import requests
import difflib
from flask import Flask, request, redirect

app = Flask(__name__)

# LINKS DAS LISTAS
LISTAS_M3U = [
    "https://github.com/StartStatic1/meus-apks/releases/download/V_backup/lista.m3u",
    "https://github.com/StartStatic1/meus-apks/releases/download/V_BACKUP2/lista2.m3u"
]
ARQUIVO_MANUAL = "manual.txt"
catalogo_filmes = {}

# User-Agent para o servidor não bloquear a conexão
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def limpar(nome):
    nome = str(nome).lower()
    nome = re.sub(r'\bii\b', '2', nome).replace('parte ii', '2')
    nome = re.sub(r'\biii\b', '3', nome).replace('parte iii', '3')
    nome = re.sub(r'\b(fhd|4k|dublado|legendado|disney|pixar|marvel)\b', '', nome)
    nome = re.sub(r"[\[\]\(\):.\-!]", " ", nome)
    return " ".join(nome.split()).strip()

def carregar_tudo():
    global catalogo_filmes
    catalogo_filmes = {}
    
    # 1. CARREGA O MANUAL PRIMEIRO (Para ele ser a regra número 1)
    if os.path.exists(ARQUIVO_MANUAL):
        try:
            with open(ARQUIVO_MANUAL, "r", encoding="utf-8", errors="ignore") as f:
                for linha in f:
                    if "|" in linha:
                        partes = linha.split("|")
                        nome_manual = limpar(partes[0].strip())
                        link_manual = partes[1].strip()
                        catalogo_filmes[nome_manual] = link_manual
            print(f"✅ Manual carregado!")
        except: pass

    # 2. CARREGA AS LISTAS (Sem sobrescrever o que já está no manual)
    for url in LISTAS_M3U:
        try:
            r = requests.get(url, headers=HEADERS, stream=True, timeout=60)
            linhas = [l.decode('utf-8', errors='ignore') for l in r.iter_lines() if l]
            for i in range(len(linhas)):
                linha = linhas[i].strip()
                if linha.startswith("#EXTINF"):
                    nome_limpo = limpar(linha.split(",")[-1].strip())
                    if i + 1 < len(linhas):
                        link = linhas[i + 1].strip()
                        if "/movie/" in link and nome_limpo not in catalogo_filmes:
                            catalogo_filmes[nome_limpo] = link
        except: continue
    print(f"✅ Total no motor: {len(catalogo_filmes)} filmes.")

carregar_tudo()

def buscar_sniper(titulo_buscado):
    titulo_limpo = limpar(titulo_buscado)
    
    # 1. Tenta achar direto no manual/lista
    if titulo_limpo in catalogo_filmes:
        return catalogo_filmes[titulo_limpo]

    # 2. Lógica de busca inteligente (Sniper)
    num_busca = re.search(r'\d+', titulo_limpo)
    num_busca = num_busca.group() if num_busca else None
    melhor_link, maior_score = None, 0.0

    for nome_cat, link in catalogo_filmes.items():
        num_cat = re.search(r'\d+', nome_cat)
        num_cat = num_cat.group() if num_cat else None
        if num_busca != num_cat: continue

        score = difflib.SequenceMatcher(None, titulo_limpo, nome_cat).ratio()
        if titulo_limpo in nome_cat: score += 0.2
        if score > maior_score and score > 0.45:
            maior_score, melhor_link = score, link

    return melhor_link

@app.route("/buscar")
def buscar():
    titulo = request.args.get("titulo", "")
    link = buscar_sniper(titulo)
    if link:
        print(f"🎬 PLAY: {titulo}")
        # Redireciona direto para o link do servidor serv99
        return redirect(link)
    return "Não encontrado", 404

@app.route("/")
def index():
    return f"Motor Ativo: {len(catalogo_filmes)} filmes", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
