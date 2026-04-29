import os
import random
import requests
import unicodedata
import re
import time
from flask import Flask, request, Response, stream_with_context, redirect

app = Flask(__name__)

# --- OS 2 QUERIDINHOS (DADOS REVISADOS) ---
FONTES = {
    "1": {"host": "http://serv99.xyz:8880", "user": "1764371", "pass": "2419902"},
    "2": {"host": "http://nxpanelxr51.info", "user": "sandroalvares2", "pass": "T9er2T"}
}

# 🧠 CACHE GLOBAL: Armazena links encontrados para não repetir a busca na API
# Estrutura: { "nome_filme_fonte": (tempo_da_busca, link_do_video) }
cache_links = {}

def limpar_busca(txt):
    if not txt: return ""
    # Remove ano entre parênteses: (2026), (1999)
    txt = re.sub(r'\(\d{4}\)', '', str(txt))
    # Remove acentos
    txt = ''.join(c for c in unicodedata.normalize('NFD', txt) if unicodedata.category(c) != 'Mn')
    # Deixa apenas letras e números (remove !, :, -, etc)
    return re.sub(r'[^a-z0-9]', '', txt.lower())

@app.route("/play")
def play():
    titulo = request.args.get("titulo")
    fonte_id = request.args.get("fonte", "1")
    
    if not titulo: return "Vazio", 400
    
    alvo = limpar_busca(titulo)
    chave_cache = f"{alvo}_{fonte_id}"
    
    # 🛑 BLOQUEIO DE REPETIÇÃO (CACHE):
    # Se o MX Player ou DPlayer pedirem o mesmo filme em menos de 5 min,
    # o motor responde instantaneamente sem usar a CPU para buscar na API.
    if chave_cache in cache_links:
        timestamp, link_salvo = cache_links[chave_cache]
        if time.time() - timestamp < 300: # Cache de 5 minutos
            print(f"⚡ [CACHE HIT] Entregando link direto: {alvo}")
            return redirect(link_salvo)

    srv = FONTES.get(fonte_id)
    if not srv: return "Fonte OFF", 404

    print(f"🔍 [BUSCA REAL] Indo na API para: {alvo} (Fonte {fonte_id})")

    try:
        # Busca na API XTREAM
        url_api = f"{srv['host']}/player_api.php?username={srv['user']}&password={srv['pass']}&action=get_vod_streams"
        r = requests.get(url_api, timeout=(3, 7)) # Timeout curto para não travar o worker
        dados = r.json()
        
        for item in dados:
            nome_api = limpar_busca(item.get('name', ''))
            # Compara se os nomes "batem" mesmo com variações
            if alvo in nome_api or nome_api in alvo:
                v_url = f"{srv['host']}/movie/{srv['user']}/{srv['pass']}/{item.get('stream_id')}.mp4"
                
                # ✅ SALVA NO CACHE: Na próxima vez, o motor não trabalha
                cache_links[chave_cache] = (time.time(), v_url)
                
                print(f"✅ [SUCESSO] Achou: {item.get('name')}")
                return redirect(v_url)
                
    except Exception as e:
        print(f"❌ [ERRO API] Fonte {fonte_id}: {e}")
    
    return f"Nao achou {alvo} na fonte {fonte_id}", 404

@app.route("/")
def index():
    # Limpa o cache se ele ficar muito grande (segurança de RAM)
    if len(cache_links) > 200: cache_links.clear()
    return "Cine Mega v48 - Motor de Cache Ativo"

if __name__ == "__main__":
    # threaded=True é essencial para o Flask lidar com os loops do MX Player
    app.run(host="0.0.0.0", port=8000, threaded=True)
