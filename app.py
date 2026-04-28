from flask import Flask, request, Response, stream_with_context, redirect
import requests
import sqlite3
import random
import os

app = Flask(__name__)

# 🚀 AGENTES DE ELITE
AGENTES_VIP = [
    "EPPIPROPLAYER/1.0.8 (Linux;Android 14) AndroidXMedia3/1.5.1",
    "purpleplayer/1.2.82",
    "Dalvik/2.1.0 (Linux; U; Android 14; 2312FPCA6G Build/UP1A.231005.007)",
    "VLC/3.0.4 LibVLC/3.0.4",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36"
]

def ler_txt(caminho):
    acervo = {}
    if os.path.exists(caminho):
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                for linha in f:
                    if "|" in linha:
                        n, u = linha.split("|", 1)
                        acervo[n.strip().lower()] = u.strip()
        except: pass
    return acervo

def executar_proxy(url_video):
    """ Calibrado para Play Rápido e Compatibilidade Chrome """
    if "archive.org" in url_video.lower():
        return redirect(url_video, code=302)

    agente = random.choice(AGENTES_VIP)
    headers = {
        "User-Agent": agente,
        "Accept": "*/*",
        "Connection": "keep-alive"
    }
    
    range_header = request.headers.get('Range', None)
    if range_header:
        headers['Range'] = range_header

    try:
        # Aumentamos o tempo de espera inicial para evitar falha no carregamento
        r = requests.get(url_video, headers=headers, stream=True, timeout=(10, 120))
        
        def generate():
            # Inicia com blocos menores (128kb) para o play ser quase instantâneo
            # Depois estabiliza em 512kb para manter o fluxo
            for i, chunk in enumerate(r.iter_content(chunk_size=128 * 1024)):
                if chunk:
                    yield chunk
                # Após o 4º bloco (512kb total), o player já deve ter iniciado
        
        resp_headers = {
            "Accept-Ranges": "bytes",
            "Access-Control-Allow-Origin": "*",
            "Content-Type": "video/mp4", # Força o motor de vídeo do Chrome
            "Cache-Control": "no-cache"
        }
        
        if 'Content-Range' in r.headers: resp_headers['Content-Range'] = r.headers['Content-Range']
        if 'Content-Length' in r.headers: resp_headers['Content-Length'] = r.headers['Content-Length']
        
        return Response(stream_with_context(generate()), status=r.status_code, headers=resp_headers)
    except:
        return redirect(url_video.replace("http://", "https://"))

@app.route("/buscar")
def buscar():
    titulo = request.args.get("titulo")
    if not titulo: return "Título vazio", 400
    
    t_limpo = titulo.strip().lower()

    # 1º FILMES_SITE.TXT (Prioridade do novo acervo)
    GIGANTE = ler_txt("filmes_site.txt")
    if t_limpo in GIGANTE:
        return executar_proxy(GIGANTE[t_limpo])

    # 2º BANCO DE DADOS
    try:
        if os.path.exists('filmes.db'):
            conn = sqlite3.connect('filmes.db')
            c = conn.cursor()
            c.execute("SELECT url FROM playlist WHERE nome LIKE ? LIMIT 1", (f"%{t_limpo}%",))
            res = c.fetchone()
            conn.close()
            if res: return executar_proxy(res[0])
    except: pass

    # 3º VIP BACKUP
    VIP = ler_txt("vips.txt")
    if t_limpo in VIP:
        return executar_proxy(VIP[t_limpo])

    return "Não encontrado", 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
