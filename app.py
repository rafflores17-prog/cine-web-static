import os
import re
import requests
import difflib # ✨ A Bilioteca de Inteligência Sniper!
from flask import Flask, request, redirect

app = Flask(__name__)

M3U_URL = "https://github.com/StartStatic1/meus-apks/releases/download/V_backup/lista.m3u" 
ARQUIVO_MANUAL = "manual.txt" 

# Agora usamos um catálogo ÚNICO para o manual não bloquear a M3U
catalogo_filmes = {}

def limpar(nome):
    nome = str(nome).lower()
    # Converte números romanos das franquias TMDB para bater com a M3U
    nome = nome.replace("parte ii", "2").replace("parte iii", "3").replace("parte iv", "4")
    # Limpa tags
    nome = re.sub(r"\[.*?\]", "", nome)
    nome = re.sub(r"\(.*?\)", "", nome)
    nome = nome.replace(".", " ").replace("-", " ").replace(":", " ")
    return " ".join(nome.split()).strip()

def carregar_arquivos():
    # 1. Carrega M3U da Nuvem
    print("⏳ Iniciando carga da lista M3U da Nuvem...")
    try:
        r = requests.get(M3U_URL, stream=True, timeout=60)
        linhas = [linha.decode('utf-8', errors='ignore') for linha in r.iter_lines() if linha]
                
        for i in range(len(linhas)):
            linha = linhas[i].strip()
            if linha.startswith("#EXTINF"):
                nome_sujo = linha.split(",")[-1].strip()
                nome_limpo = limpar(nome_sujo)

                if i + 1 < len(linhas):
                    link = linhas[i + 1].strip()
                    if "/movie/" in link and link.endswith(".mp4"):
                        catalogo_filmes[nome_limpo] = link
        print(f"✅ M3U: {len(catalogo_filmes)} filmes na memória!")
    except Exception as e:
        print(f"❌ ERRO ao baixar lista M3U: {e}")

    # 2. Carrega Manual (Mescla junto com a M3U, ganhando prioridade se o nome for igual)
    if os.path.exists(ARQUIVO_MANUAL):
        try:
            contador = 0
            with open(ARQUIVO_MANUAL, "r", encoding="utf-8", errors="ignore") as f:
                for linha in f:
                    if "|" in linha:
                        nome_sujo, link = linha.split("|", 1)
                        # Se já existir, o link manual substitui o da nuvem!
                        catalogo_filmes[limpar(nome_sujo)] = link.strip()
                        contador += 1
            print(f"✅ MANUAL: {contador} filmes injetados com sucesso!")
        except: pass

carregar_arquivos()

# 🎯 FUNÇÃO SNIPER
def buscar_sniper(titulo_buscado):
    # 1. Match Perfeito (Na Mosca)
    if titulo_buscado in catalogo_filmes:
        return catalogo_filmes[titulo_buscado], "Exato"

    melhor_link = None
    maior_score = 0.0

    # Pega os números do título (Ex: o "2" do American Pie 2)
    nums_busca = set(re.findall(r'\b\d+\b', titulo_buscado))

    # 2. Match por Similaridade Matemática
    for nome_cat, link in catalogo_filmes.items():
        if nome_cat in titulo_buscado or titulo_buscado in nome_cat:
            # Calcula o grau de semelhança entre os títulos (Ex: 80% igual)
            score = difflib.SequenceMatcher(None, titulo_buscado, nome_cat).ratio()
            
            # Pega os números do título que está no M3U
            nums_cat = set(re.findall(r'\b\d+\b', nome_cat))
            
            # 🚨 TRAVA DE FRANQUIA: Se um é o "2" e o outro não tem número, penaliza MUITO!
            if nums_busca and nums_cat and nums_busca != nums_cat:
                score -= 1.0 
            # 🚀 BÔNUS DE FRANQUIA: Se o número bateu, dá prioridade total!
            elif nums_busca and nums_busca == nums_cat:
                score += 1.0

            if score > maior_score:
                maior_score = score
                melhor_link = link

    # Só retorna se for uma busca válida
    if melhor_link and maior_score > 0.3:
        return melhor_link, f"Precisão {maior_score:.2f}"
        
    return None, None

@app.route("/buscar")
def buscar():
    titulo = request.args.get("titulo", "")
    titulo_limpo = limpar(titulo)
    
    if not titulo_limpo:
        return "Nenhum título", 400

    # Usa o Sniper pra achar o link correto
    link, tipo = buscar_sniper(titulo_limpo)
    if link:
        print(f"🎬 ENCONTRADO ({tipo}): {titulo_limpo}")
        return redirect(link)

    print(f"❌ NÃO LOCALIZADO: {titulo_limpo}")
    return "Filme não encontrado na lista.", 404

@app.route("/")
def index():
    return f"🎬 Motor Cine Mega Online! Total indexado: {len(catalogo_filmes)}", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
