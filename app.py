import os
import re
import requests
import difflib
from flask import Flask, request, redirect

app = Flask(__name__)

# LINKS DAS SUAS DUAS LISTAS
LISTAS_M3U = [
    "https://github.com/StartStatic1/meus-apks/releases/download/V_backup/lista.m3u",
    "https://github.com/StartStatic1/meus-apks/releases/download/V_BACKUP2/lista2.m3u"
]

ARQUIVO_MANUAL = "manual.txt"
catalogo_filmes = {}

def limpar(nome):
    nome = str(nome).lower()
    # Converte numeração romana
    nome = re.sub(r'\bii\b', '2', nome).replace('parte ii', '2')
    nome = re.sub(r'\biii\b', '3', nome).replace('parte iii', '3')
    # Remove lixo e marcas d'água comuns em listas
    nome = re.sub(r'\b(walt disney|disney|pixar|marvel|apresenta|coleção|fhd|4k|dublado|legendado)\b', '', nome)
    nome = re.sub(r"[\[\]\(\):.\-]", " ", nome)
    return " ".join(nome.split()).strip()

def carregar_tudo():
    global catalogo_filmes
    catalogo_filmes = {}
    print("⏳ Iniciando carregamento das listas...")

    for url in LISTAS_M3U:
        try:
            r = requests.get(url, stream=True, timeout=60)
            linhas = [l.decode('utf-8', errors='ignore') for l in r.iter_lines() if l]
            for i in range(len(linhas)):
                linha = linhas[i].strip()
                if linha.startswith("#EXTINF"):
                    nome_limpo = limpar(linha.split(",")[-1].strip())
                    if i + 1 < len(linhas):
                        link = linhas[i + 1].strip()
                        if "/movie/" in link:
                            # A lista 2 pode sobrescrever a 1 se tiver o mesmo nome
                            catalogo_filmes[nome_limpo] = link
            print(f"✅ Lista carregada: {url}")
        except Exception as e:
            print(f"❌ Erro ao baixar lista: {e}")

    # 🚨 O MANUAL SEMPRE MANDA: Ele sobrescreve qualquer lista se houver conflito
    if os.path.exists(ARQUIVO_MANUAL):
        try:
            with open(ARQUIVO_MANUAL, "r", encoding="utf-8", errors="ignore") as f:
                for linha in f:
                    if "|" in linha:
                        n, l = linha.split("|", 1)
                        catalogo_filmes[limpar(n)] = l.strip()
            print("✅ Backup manual (manual.txt) aplicado!")
        except:
            print("⚠️ Erro ao ler manual.txt")

carregar_tudo()

def buscar_sniper(titulo_buscado):
    titulo_limpo = limpar(titulo_buscado)
    
    # 1. Tenta achar o nome exato primeiro
    if titulo_limpo in catalogo_filmes:
        return catalogo_filmes[titulo_limpo]

    num_busca = re.search(r'\d+', titulo_limpo)
    num_busca = num_busca.group() if num_busca else None
    
    melhor_link = None
    maior_score = 0.0

    for nome_cat, link in catalogo_filmes.items():
        # Trava de Franquia (Numeração)
        num_cat = re.search(r'\d+', nome_cat)
        num_cat = num_cat.group() if num_cat else None
        if num_busca != num_cat:
            continue

        score = difflib.SequenceMatcher(None, titulo_limpo, nome_cat).ratio()
        
        # Rigidez para nomes curtos
        limite = 0.85 if len(titulo_limpo) < 15 else 0.70
        
        if score > maior_score and score >= limite:
            maior_score = score
            melhor_link = link

    return melhor_link

@app.route("/buscar")
def buscar():
    titulo = request.args.get("titulo", "")
    link = buscar_sniper(titulo)
    if link:
        print(f"🎬 PLAY: {titulo}")
        return redirect(link)
    
    print(f"❌ NÃO ENCONTRADO: {titulo}")
    return "Filme não encontrado", 404

@app.route("/")
def index():
    return f"Motor Cine Mega Online: {len(catalogo_filmes)} filmes em 2 listas + manual.", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
