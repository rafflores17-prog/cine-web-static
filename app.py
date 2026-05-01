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
    nome = re.sub(r'\bii\b', '2', nome).replace('parte ii', '2')
    nome = re.sub(r'\biii\b', '3', nome).replace('parte iii', '3')
    nome = re.sub(r'\biv\b', '4', nome)
    nome = re.sub(r'\b(19|20)\d{2}\b', '', nome) # Remove ano
    nome = re.sub(r"[\[\]\(\):.\-]", " ", nome)
    return " ".join(nome.split()).strip()

def carregar_arquivos():
    print("⏳ Carregando 19k filmes na RAM...")
    try:
        r = requests.get(M3U_URL, stream=True, timeout=60)
        linhas = [l.decode('utf-8', errors='ignore') for l in r.iter_lines() if l]
        for i in range(len(linhas)):
            linha = linhas[i].strip()
            if linha.startswith("#EXTINF"):
                nome_sujo = linha.split(",")[-1].strip()
                nome_limpo = limpar(nome_sujo)
                if i + 1 < len(linhas):
                    link = linhas[i + 1].strip()
                    if "/movie/" in link:
                        catalogo_filmes[nome_limpo] = link
        print(f"✅ Catálogo Pronto!")
    except Exception as e: print(f"❌ Erro: {e}")

    if os.path.exists(ARQUIVO_MANUAL):
        with open(ARQUIVO_MANUAL, "r", encoding="utf-8", errors="ignore") as f:
            for linha in f:
                if "|" in linha:
                    n, l = linha.split("|", 1)
                    catalogo_filmes[limpar(n)] = l.strip()

carregar_arquivos()

def buscar_sniper(titulo_buscado):
    titulo_limpo = limpar(titulo_buscado)
    
    # 1. Prioridade Máxima: Nome Idêntico
    if titulo_limpo in catalogo_filmes:
        return catalogo_filmes[titulo_limpo]

    num_busca = re.search(r'\d+', titulo_limpo)
    num_busca = num_busca.group() if num_busca else None

    melhor_link = None
    maior_score = 0.0

    for nome_cat, link in catalogo_filmes.items():
        num_cat = re.search(r'\d+', nome_cat)
        num_cat = num_cat.group() if num_cat else None
        
        # Se os números (franquia) não batem, pula
        if num_busca != num_cat:
            continue

        # Calcula similaridade
        score = difflib.SequenceMatcher(None, titulo_limpo, nome_cat).ratio()
        
        # 🚨 TRAVA DE PRECISÃO: Se a diferença de tamanho for muito grande, ignora.
        # Evita que "Som da Morte" ache "Som da Morte: O Documentário da Disney"
        dif_tamanho = abs(len(titulo_limpo) - len(nome_cat))
        if len(titulo_limpo) < 20 and dif_tamanho > 10:
            score -= 0.4 

        if score > maior_score and score > 0.6:
            maior_score = score
            melhor_link = link

    return melhor_link

@app.route("/buscar")
def buscar():
    titulo = request.args.get("titulo", "")
    link = buscar_sniper(titulo)
    if link:
        print(f"🎬 SUCESSO: {titulo}")
        return redirect(link)
    print(f"❌ NÃO LOCALIZADO: {titulo}")
    return "Não encontrado", 404

@app.route("/")
def index():
    return f"Motor Ativo: {len(catalogo_filmes)} filmes", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
