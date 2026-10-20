from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import subprocess
import os
import urllib.request
import glob
import re

SERVER_URL = "https://tinycli.onrender.com/api/chat" 
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
        if self.path == "/sessions":
            self._set_headers()
            sessions = []
            if os.path.exists(SESSIONS_DIR):
                for f in glob.glob(os.path.join(SESSIONS_DIR, "*.json")):
                    sessions.append(os.path.basename(f).replace(".json", ""))
            self.wfile.write(json.dumps({"sessions": sessions}).encode())

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

        elif self.path.startswith("/history/"):
            self._set_headers()
            session_id = self.path.split("/")[-1]
            filepath = os.path.join(SESSIONS_DIR, f"{session_id}.json")
            if os.path.exists(filepath):
                with open(filepath, "r") as f:
                    self.wfile.write(f.read().encode())
            else:
                self.wfile.write(json.dumps({"messages": []}).encode())
                
        else:
            self._set_headers("text/html")
            try:
                with open(os.path.join(os.path.dirname(__file__), "index.html"), "r", encoding="utf-8") as f:
                    self.wfile.write(f.read().encode())
            except:
                self.wfile.write(b"<h1>Erro: index.html nao encontrado</h1>")

    def do_POST(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))

            if self.path == "/chat":
                prompt = data.get("prompt")
                model = data.get("model")
                session_id = data.get("session_id", "nova")
                self._set_headers()

                req_data = json.dumps({"messages": [{"role": "user", "content": prompt}], "model": model}).encode()
                req = urllib.request.Request(SERVER_URL, data=req_data, headers={'Content-Type': 'application/json'}, method="POST")
                
                try:
                    with urllib.request.urlopen(req) as response:
                        res_data = json.loads(response.read().decode())
                        reply = res_data["choices"][0]["message"]["content"]
                        
                        exec_command = None
                        
                        # Remove blocos JSON que a IA mandou para o utilizador não ver código sujo
                        if "```json" in reply: 
                            json_part = reply.split("```json")[1].split("```")[0]
                            reply = reply.replace(f"```json\n{json_part}\n```", "") # Limpa o JSON
                        elif "```" in reply:
                            json_part = reply.split("```")[1].split("```")[0]
                            try:
                                # Tenta ver se o bloco de código é um comando
                                action = json.loads(json_part.strip())
                                if action.get("tool") in ["run_command", "run_code"]:
                                    exec_command = action.get("command") or action.get("code")
                                    reply = "Pedi para executar o comando abaixo. Clica no botão para correr no Termux."
                            except json.JSONDecodeError:
                                pass # É só um bloco de código normal, deixa ficar

                        # Limpeza extra de separadores estranhos (===, ---) no texto
                        reply = re.sub(r'\n={3,}\n', '\n', reply)
                        reply = re.sub(r'\n-{3,}\n', '\n', reply)

                        self._save_session(session_id, prompt, reply)
                        self.wfile.write(json.dumps({"reply": reply, "exec_command": exec_command}).encode())

                except Exception as e:
                    self.wfile.write(json.dumps({"reply": f"Erro na IA: {e}"}).encode())
                    
            elif self.path == "/execute":
                cmd = data.get("command")
                self._set_headers()
                try:
                    output = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
                    result = output.stdout + output.stderr
                    if not result: result = "Comando executado com sucesso (sem saída)."
                    self.wfile.write(json.dumps({"output": result}).encode())
                except Exception as e:
                    self.wfile.write(json.dumps({"output": f"Erro: {e}"}).encode())
        except Exception as e:
            self._set_headers()
            self.wfile.write(json.dumps({"reply": f"Erro crítico: {e}", "exec_command": None}).encode())

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
    server = HTTPServer(('127.0.0.1', PORT), TinyWebServer)
    server.serve_forever()