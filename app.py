from flask import Flask, request, Response, stream_with_context, redirect
import requests
import sqlite3
import random
import os

app = Flask(__name__)

# 🚀 AGENTES VIP - Simulando Apps Reais para liberar o sinal
AGENTES_VIP = [
    "EPPIPROPLAYER/1.0.8 (Linux;Android 14) AndroidXMedia3/1.5.1",
    "purpleplayer/1.2.82",
    "Dalvik/2.1.0 (Linux; U; Android 14; 2312FPCA6G Build/UP1A.231005.007)",
    "VLC/3.0.4 LibVLC/3.0.4",
    "okhttp/4.12.0"
]

def ler_arquivo_txt_multi(caminho):
    """Lê o TXT e permite múltiplos links para o mesmo nome de filme"""
    acervo = {}
    if os.path.exists(caminho):
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                for linha in f:
                    if "|" in linha:
                        nome, url = linha.split("|", 1)
                        nome_limpo = nome.strip().lower()
                        if nome_limpo not in acervo:
                            acervo[nome_limpo] = []
                        acervo[nome_limpo].append(url.strip())
        except: pass
    return acervo

def executar_proxy(url_video):
    """ Proxy com Auto-Correção de Codec para evitar 'Só Áudio' """
    if "archive.org" in url_video.lower():
        return redirect(url_video, code=302)

    agente = random.choice(AGENTES_VIP)
    headers = {
        "User-Agent": agente,
        "Accept": "*/*",
        "Connection": "keep-alive",
        "Referer": "http://iptv.com"
    }
    
    range_header = request.headers.get('Range', None)
    if range_header: headers['Range'] = range_header

    try:
        # Aumentamos o timeout para servidores mais lentos como o sul26
        r = requests.get(url_video, headers=headers, stream=True, timeout=(10, 60), allow_redirects=True)
        
        def generate():
            # Chunk de 512kb para estabilizar o fluxo de vídeo no Chrome
            for chunk in r.iter_content(chunk_size=512 * 1024):
                if chunk: yield chunk
        
        resp_headers = {
            "Accept-Ranges": "bytes",
            "Access-Control-Allow-Origin": "*",
            # Forçamos video/mp4 para o Chrome ativar o motor de vídeo e não só o de áudio
            "Content-Type": "video/mp4",
            "Cache-Control": "public, max-age=3600"
        }
        
        if 'Content-Range' in r.headers: resp_headers['Content-Range'] = r.headers['Content-Range']
        if 'Content-Length' in r.headers: resp_headers['Content-Length'] = r.headers['Content-Length']
        
        return Response(stream_with_context(generate()), status=r.status_code, headers=resp_headers)
    except:
        return None # Indica que este link falhou

@app.route("/buscar")
def buscar():
    titulo = request.args.get("titulo")
    if not titulo: return "Título vazio", 400
    titulo_limpo = titulo.strip().lower()

    # 🥇 1º LUGAR: ACERVO GIGANTE (filmes_site.txt) com Multi-Link
    ACERVO = ler_arquivo_txt_multi("filmes_site.txt")
    if titulo_limpo in ACERVO:
        urls = ACERVO[titulo_limpo]
        # Tenta o Serv99 primeiro, se falhar ou soubermos que é ruim, ele tentaria o próximo
        # Aqui, vamos priorizar o link que NÃO seja o serv99 se for American Pie
        for u in urls:
            if "9100" in u or "9099" in u: # IDs do American Pie no Serv99 que você citou
                continue # Pula o que dá erro de áudio e vai pro próximo (Sul26)
            
            resultado = executar_proxy(u)
            if resultado: return resultado

    # 🥈 2º LUGAR: BANCO DE DADOS LOCAL
    try:
        if os.path.exists('filmes.db'):
            conn = sqlite3.connect('filmes.db')
            c = conn.cursor()
            c.execute("SELECT url FROM playlist WHERE nome LIKE ? LIMIT 1", (f"%{titulo_limpo}%",))
            res = c.fetchone()
            conn.close()
            if res:
                out = executar_proxy(res[0])
                if out: return out
    except: pass

    # 🥉 3º LUGAR: VIP BACKUP
    VIP = ler_arquivo_txt_multi("vips.txt")
    if titulo_limpo in VIP:
        out = executar_proxy(VIP[titulo_limpo][0])
        if out: return out

    return "Filme não encontrado ou servidores offline", 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
