# 本機接收器：在 127.0.0.1:8765 接收 Chrome 送來的報告全文，存到 reports/。
# 用法：python tools\receive_server.py   （存完一批後自動在 10 分鐘閒置時結束，也可直接 Ctrl+C）
# 瀏覽器端：fetch('http://127.0.0.1:8765/save?name=2026-10-01_Thu.txt', {method:'POST', body:text})
import http.server, os, re, threading, time, urllib.parse

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "reports")
last = [time.time()]

class H(http.server.BaseHTTPRequestHandler):
    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", self.headers.get("Origin") or "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "content-type")
        self.send_header("Access-Control-Allow-Private-Network", "true")

    def do_OPTIONS(self):
        self.send_response(204); self._cors(); self.end_headers()

    def do_POST(self):
        last[0] = time.time()
        q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        name = q.get("name", [""])[0]
        if not re.fullmatch(r"\d{4}-\d\d-\d\d_[A-Z][a-z]{2}\.txt", name):
            self.send_response(400); self._cors(); self.end_headers(); return
        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        with open(os.path.join(ROOT, name), "wb") as f:
            f.write(body)
        self.send_response(200); self._cors(); self.end_headers()
        self.wfile.write(f"saved {name} {len(body)}".encode())
        print("saved", name, len(body), flush=True)

srv = http.server.HTTPServer(("127.0.0.1", 8765), H)
def idle():
    while time.time() - last[0] < 600: time.sleep(5)
    srv.shutdown()
threading.Thread(target=idle, daemon=True).start()
print("listening 127.0.0.1:8765", flush=True)
srv.serve_forever()
