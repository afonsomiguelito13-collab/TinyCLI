from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import subprocess
import os
import urllib.request
import glob

# --- CONFIGURAÇÕES ---
SERVER_URL = "https://tinycli.onrender.com/api/chat"  # O teu servidor na nuvem
SESSIONS_DIR = os.path.expanduser("~/.local/share/.tinycli_sessions")
USAGE_FILE = os.path.expanduser("~/.local/share/.tinycli_usage.json")
PORT = 8080

class TinyWebServer(BaseHTTPRequestHandler):
    def _set_headers(self, content_type="application/json"):
        self.send_response(200)
        self.send_header('Content-Type', content_type)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_OPTIONS(self):
        self._set_headers()

    def do_GET(self):
        # 1. Listar Sessões
        if self.path == "/sessions":
            self._set_headers()
            sessions = []
            if os.path.exists(SESSIONS_DIR):
                for f in glob.glob(os.path.join(SESSIONS_DIR, "*.json")):
                    sessions.append(os.path.basename(f).replace(".json", ""))
            self.wfile.write(json.dumps({"sessions": sessions}).encode())

        # 2. Ler o Usage Real (do ficheiro .json no Termux)
        elif self.path == "/usage":
            self._set_headers()
            tokens = 0
            if os.path.exists(USAGE_FILE):
                try:
                    with open(USAGE_FILE, "r") as f:
                        data = json.load(f)
                        tokens = data.get("tokens_usados", 0)
                except: pass
            self.wfile.write(json.dumps({"tokens": tokens}).encode())

        # 3. Carregar Histórico
        elif self.path.startswith("/history/"):
            self._set_headers()
            session_id = self.path.split("/")[-1]
            filepath = os.path.join(SESSIONS_DIR, f"{session_id}.json")
            if os.path.exists(filepath):
                with open(filepath, "r") as f:
                    self.wfile.write(f.read().encode())
            else:
                self.wfile.write(json.dumps({"messages": []}).encode())
                
        # 4. Servir o index.html (quando acedes pelo browser)
        else:
            self._set_headers("text/html")
            try:
                with open("index.html", "r", encoding="utf-8") as f:
                    self.wfile.write(f.read().encode())
            except:
                self.wfile.write(b"<h1>Erro: index.html nao encontrado na mesma pasta</h1>")

    def do_POST(self):
        if self.path == "/chat":
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            prompt = data.get("prompt")
            model = data.get("model")
            session_id = data.get("session_id", "nova")

            self._set_headers()

            # Manda para o teu servidor no Render
            req_data = json.dumps({"messages": [{"role": "user", "content": prompt}], "model": model}).encode()
            req = urllib.request.Request(SERVER_URL, data=req_data, headers={'Content-Type': 'application/json'}, method="POST")
            
            try:
                with urllib.request.urlopen(req) as response:
                    res_data = json.loads(response.read().decode())
                    reply = res_data["choices"][0]["message"]["content"]
                    
                    # Limpa markdown de json se houver
                    if "```json" in reply: reply = reply.split("```json")[1].split("```")[0]
                    elif "```" in reply: reply = reply.split("```")[1].split("```")[0]
                        
                    try:
                        action = json.loads(reply.strip())
                        if action.get("tool") == "run_command" or action.get("tool") == "run_code":
                            cmd = action.get("command") or action.get("code")
                            # Executa no Termux
                            output = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                            final_reply = f"**Executado:** `{cmd}`\n\n**Saída:**\n```bash\n{output.stdout}{output.stderr}\n```"
                            
                            self._save_session(session_id, prompt, final_reply)
                            self.wfile.write(json.dumps({"reply": final_reply}).encode())
                            return
                    except json.JSONDecodeError:
                        pass # É texto normal

                    self._save_session(session_id, prompt, reply)
                    self.wfile.write(json.dumps({"reply": reply}).encode())

            except Exception as e:
                self.wfile.write(json.dumps({"reply": f"Erro no servidor: {e}"}).encode())

    def _save_session(self, session_id, user_msg, bot_msg):
        os.makedirs(SESSIONS_DIR, exist_ok=True)
        filepath = os.path.join(SESSIONS_DIR, f"{session_id}.json")
        messages = []
        if os.path.exists(filepath):
            with open(filepath, "r") as f:
                messages = json.load(f)
        
        messages.append({"role": "user", "content": user_msg})
        messages.append({"role": "assistant", "content": bot_msg})
        
        with open(filepath, "w") as f:
            json.dump(messages, f)

if __name__ == "__main__":
    print(f"🦁 TinyCLI Web Server a correr em http://localhost:{PORT}")
    print("Mantém esta janela aberta no Termux.")
    server = HTTPServer(('127.0.0.1', PORT), TinyWebServer)
    server.serve_forever()