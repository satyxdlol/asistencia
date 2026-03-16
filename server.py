import json, os, datetime, zoneinfo
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse

TZ_AR = zoneinfo.ZoneInfo("America/Argentina/Buenos_Aires")

DATA_FILE = "data.json"

# ── Datos ──────────────────────────────────────────
def leer():
    if not os.path.exists(DATA_FILE):
        return {"alumnos": []}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def guardar(d):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)

# ── Handler ────────────────────────────────────────
class Handler(SimpleHTTPRequestHandler):

    def log_message(self, fmt, *args):
        pass

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_GET(self):
        p = urlparse(self.path).path

        if p == "/api/alumnos":
            self._json(200, leer()["alumnos"])
            return

        # Sirve archivos estáticos (profesor.html, alumno.html)
        if p == "/" or p == "":
            self.path = "/profesor.html"
        super().do_GET()

    def do_POST(self):
        length  = int(self.headers.get("Content-Length", 0))
        body    = self.rfile.read(length)
        p       = urlparse(self.path).path

        try:
            payload = json.loads(body)
        except Exception:
            self._json(400, {"error": "JSON inválido"})
            return

        # Registrar asistencia (alumno)
        if p == "/api/registrar":
            dni      = str(payload.get("dni", "")).strip()
            apellido = payload.get("apellido", "").strip().lower()
            nombre   = payload.get("nombre",   "").strip().lower()

            if not dni or not apellido or not nombre:
                self._json(400, {"error": "Faltan datos"}); return

            datos = leer()
            idx   = next((i for i, a in enumerate(datos["alumnos"]) if a["dni"] == dni), None)

            if idx is None:
                self._json(404, {"error": "DNI no encontrado en la lista."}); return

            a     = datos["alumnos"][idx]
            ap_ok = a["apellido"].lower() in apellido or apellido in a["apellido"].lower()
            nm_ok = a["nombre"].lower()   in nombre   or nombre   in a["nombre"].lower()

            if not ap_ok or not nm_ok:
                self._json(403, {"error": "Los datos no coinciden con el registro."}); return

            if a.get("presente"):
                self._json(409, {"error": f"{a['apellido']}, {a['nombre']} — ya registraste tu asistencia."}); return

            hora = datetime.datetime.now(TZ_AR).strftime("%H:%M")
            datos["alumnos"][idx]["presente"] = True
            datos["alumnos"][idx]["hora"]     = hora
            guardar(datos)
            self._json(200, {"ok": True, "apellido": a["apellido"], "nombre": a["nombre"], "hora": hora})
            return

        # Guardar lista de alumnos (profesor)
        if p == "/api/guardar":
            datos = leer()
            datos["alumnos"] = payload.get("alumnos", [])
            guardar(datos)
            self._json(200, {"ok": True}); return

        # Resetear asistencia
        if p == "/api/resetear":
            datos = leer()
            for a in datos["alumnos"]:
                a["presente"] = False
                a["hora"]     = None
            guardar(datos)
            self._json(200, {"ok": True}); return

        self._json(404, {"error": "Ruta no encontrada"})

    def _json(self, code, data):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self._cors()
        self.send_header("Content-Type",   "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin",  "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

# ── Main ───────────────────────────────────────────
if __name__ == "__main__":
    # Railway usa la variable PORT
    PORT = int(os.environ.get("PORT", 8080))

    # Inicializa datos si no existen
    if not os.path.exists(DATA_FILE):
        guardar({"alumnos": [
            {"apellido": "González",  "nombre": "María Belén",    "dni": "40123456", "presente": False, "hora": None},
            {"apellido": "Rodríguez", "nombre": "Lucas Ezequiel",  "dni": "41234567", "presente": False, "hora": None},
            {"apellido": "Martínez",  "nombre": "Sofía Valentina", "dni": "39876543", "presente": False, "hora": None},
            {"apellido": "López",     "nombre": "Tomás Agustín",   "dni": "42001122", "presente": False, "hora": None},
            {"apellido": "Pérez",     "nombre": "Camila Rocío",    "dni": "43112233", "presente": False, "hora": None},
        ]})

    server = HTTPServer(("0.0.0.0", PORT), Handler)
    print(f"Servidor corriendo en puerto {PORT}")
    server.serve_forever()
