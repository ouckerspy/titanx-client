"""
TITAN X — Cliente FiveM
Empaquetar:
    pyinstaller --onefile --noconsole --name TitanXClient_FiveM ^
        --add-data "core;core" --add-data "config.py;." --add-data "client/eye.gif;." ^
        --paths . client/titanx_client.py
"""
import sys, os, json, time, threading, urllib.request, urllib.error

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tkinter as tk
from tkinter import font as tkfont
from PIL import Image, ImageTk

GAME_MODE = "FiveM"
ACCENT    = "#dc2626"
BG        = "#060606"
SURFACE   = "#0e0e0e"
WIN_W, WIN_H = 920, 580


def _gif_path():
    """Encuentra eye.gif tanto en desarrollo como en el .exe compilado."""
    if getattr(sys, "frozen", False):
        return os.path.join(sys._MEIPASS, "eye.gif")
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "eye.gif")


def _resolve_server():
    env = os.environ.get("TITANX_SERVER", "").strip()
    if env: return env.rstrip("/")
    base = os.path.dirname(sys.executable if getattr(sys, "frozen", False) else os.path.abspath(__file__))
    cfg = os.path.join(base, "server.txt")
    if os.path.exists(cfg):
        try:
            v = open(cfg).read().strip()
            if v: return v.rstrip("/")
        except: pass
    return "http://127.0.0.1:7890"

SERVER = _resolve_server()

def _http(method, url, payload=None, timeout=10):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                  headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


class GifLabel(tk.Label):
    """Label que reproduce un GIF animado en loop."""
    def __init__(self, parent, gif_path, scale=1.4, **kw):
        super().__init__(parent, bg=BG, bd=0, highlightthickness=0, **kw)
        self._frames = []
        self._delays = []
        self._idx    = 0
        self._job    = None
        self._load(gif_path, scale)

    def _load(self, path, scale):
        gif = Image.open(path)
        for i in range(gif.n_frames):
            gif.seek(i)
            delay = gif.info.get("duration", 40)
            frame = gif.convert("RGBA")
            if scale != 1:
                w = int(frame.width * scale)
                h = int(frame.height * scale)
                frame = frame.resize((w, h), Image.LANCZOS)
            self._frames.append(ImageTk.PhotoImage(frame))
            self._delays.append(max(20, delay))
        self._play()

    def _play(self):
        if not self._frames:
            return
        self.config(image=self._frames[self._idx])
        delay = self._delays[self._idx]
        self._idx = (self._idx + 1) % len(self._frames)
        self._job = self.after(delay, self._play)

    def stop(self):
        if self._job:
            self.after_cancel(self._job)


class TitanXApp:
    def __init__(self, root):
        self.root    = root
        self.running = False
        self.eta_total = 0
        self.t0 = None
        self._anim_job = None
        self._spinner_i = 0

        root.title("TITAN X")
        root.configure(bg=BG)
        root.geometry(f"{WIN_W}x{WIN_H}")
        root.resizable(False, False)
        try: root.iconbitmap(default="")
        except: pass

        self.f_title  = tkfont.Font(family="Segoe UI", size=30, weight="bold")
        self.f_sub    = tkfont.Font(family="Segoe UI", size=10)
        self.f_label  = tkfont.Font(family="Segoe UI", size=8, weight="bold")
        self.f_code   = tkfont.Font(family="Consolas", size=28, weight="bold")
        self.f_btn    = tkfont.Font(family="Segoe UI", size=12, weight="bold")
        self.f_status = tkfont.Font(family="Segoe UI", size=9)
        self.f_pct    = tkfont.Font(family="Segoe UI", size=40, weight="bold")
        self.f_eta    = tkfont.Font(family="Segoe UI", size=9)
        self.f_module = tkfont.Font(family="Segoe UI", size=9)

        self._build_idle()
        root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ─── Idle screen ───────────────────────────────────────────────
    def _build_idle(self):
        self.idle_frame = tk.Frame(self.root, bg=BG)
        self.idle_frame.place(x=0, y=0, width=WIN_W, height=WIN_H)

        # Left panel — eye + title
        left = tk.Frame(self.idle_frame, bg=BG, width=WIN_W // 2)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)

        inner = tk.Frame(left, bg=BG)
        inner.place(relx=0.5, rely=0.5, anchor="center")

        # GIF eye
        try:
            self._gif = GifLabel(inner, _gif_path(), scale=1.4)
            self._gif.pack(pady=(0, 16))
        except Exception as e:
            tk.Label(inner, text="👁", font=tkfont.Font(size=60), bg=BG).pack(pady=(0,16))

        tk.Label(inner, text="TITAN X", font=self.f_title, fg=ACCENT, bg=BG).pack()
        tk.Label(inner, text="Verificación forense de sistema",
                 font=self.f_sub, fg="#2a2a2a", bg=BG).pack(pady=(4, 0))

        # Right panel — form
        right = tk.Frame(self.idle_frame, bg=SURFACE)
        right.pack(side="right", fill="both", expand=True)

        form = tk.Frame(right, bg=SURFACE)
        form.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(form, text="CÓDIGO SS", font=self.f_label,
                 fg="#333", bg=SURFACE).pack(anchor="w", pady=(0, 6))

        self._ef = tk.Frame(form, bg="#141414",
                             highlightthickness=2, highlightbackground="#222")
        self._ef.pack(pady=(0, 8))
        self.code_var = tk.StringVar()
        self.entry = tk.Entry(
            self._ef, textvariable=self.code_var, font=self.f_code,
            justify="center", width=7, bg="#141414", fg="#fff",
            insertbackground="#fff", relief="flat", bd=10, highlightthickness=0,
        )
        self.entry.pack()
        self.entry.bind("<KeyRelease>", self._fmt)
        self.entry.bind("<Return>", lambda e: self._start())
        self.entry.bind("<FocusIn>",  lambda e: self._ef.config(highlightbackground=ACCENT))
        self.entry.bind("<FocusOut>", lambda e: self._ef.config(highlightbackground="#222"))

        self.status_lbl = tk.Label(form, text="Ingresá el código que te dio el staff",
                                    font=self.f_status, fg="#2a2a2a", bg=SURFACE)
        self.status_lbl.pack(pady=(2, 16))

        self.btn = tk.Button(
            form, text="INICIAR VERIFICACIÓN", font=self.f_btn,
            fg="#fff", bg=ACCENT, activebackground="#b91c1c", activeforeground="#fff",
            relief="flat", padx=50, pady=14, cursor="hand2", command=self._start, bd=0,
        )
        self.btn.pack()

        tk.Label(right, text="FiveM · 187 módulos forenses",
                 font=tkfont.Font(family="Segoe UI", size=8),
                 fg="#1a1a1a", bg=SURFACE).pack(side="bottom", pady=12)

    # ─── Scan screen ───────────────────────────────────────────────
    def _build_scan(self):
        self.scan_frame = tk.Frame(self.root, bg=BG)
        self.scan_frame.place(x=0, y=0, width=WIN_W, height=WIN_H)

        bar = tk.Frame(self.scan_frame, bg=SURFACE, height=52)
        bar.pack(fill="x"); bar.pack_propagate(False)
        tk.Label(bar, text="TITAN X",
                 font=tkfont.Font(family="Segoe UI", size=13, weight="bold"),
                 fg=ACCENT, bg=SURFACE).pack(side="left", padx=24, pady=14)
        self.status_top = tk.Label(bar, text="● ESCANEANDO",
                                    font=tkfont.Font(family="Segoe UI", size=9, weight="bold"),
                                    fg="#22c55e", bg=SURFACE)
        self.status_top.pack(side="right", padx=24)

        content = tk.Frame(self.scan_frame, bg=BG)
        content.pack(fill="both", expand=True)

        # Left: GIF
        left = tk.Frame(content, bg=BG, width=310)
        left.pack(side="left", fill="y"); left.pack_propagate(False)
        try:
            gif2 = GifLabel(left, _gif_path(), scale=1.4)
            gif2.place(relx=0.5, rely=0.5, anchor="center")
        except: pass

        # Right: progress
        right = tk.Frame(content, bg=SURFACE)
        right.pack(side="right", fill="both", expand=True)
        pa = tk.Frame(right, bg=SURFACE)
        pa.place(relx=0.5, rely=0.5, anchor="center")

        self.pct_lbl = tk.Label(pa, text="0%", font=self.f_pct, fg=ACCENT, bg=SURFACE)
        self.pct_lbl.pack()

        pb_bg = tk.Canvas(pa, width=340, height=5, bg="#1a1a1a", highlightthickness=0)
        pb_bg.pack(pady=(8, 4))
        self.pb_fill = pb_bg.create_rectangle(0, 0, 0, 5, fill=ACCENT, width=0)
        self._pb_bg = pb_bg

        self.module_lbl = tk.Label(pa, text="Iniciando módulos…",
                                    font=self.f_module, fg="#333", bg=SURFACE)
        self.module_lbl.pack(pady=(2, 22))

        tk.Label(pa, text="NO CIERRES ESTA VENTANA",
                 font=tkfont.Font(family="Segoe UI", size=10, weight="bold"),
                 fg="#fff", bg=SURFACE).pack()
        tk.Label(pa, text="El escaneo corre localmente. El resultado lo ve el staff.",
                 font=self.f_status, fg="#333", bg=SURFACE).pack(pady=(4, 18))

        self.spinner_lbl = tk.Label(pa, text="◐",
                                     font=tkfont.Font(family="Segoe UI", size=16),
                                     fg=ACCENT, bg=SURFACE)
        self.spinner_lbl.pack()
        self.distract_lbl = tk.Label(pa, text="", font=self.f_status, fg="#2a2a2a", bg=SURFACE)
        self.distract_lbl.pack(pady=(4, 0))
        self.eta_lbl = tk.Label(pa, text="", font=self.f_eta, fg="#2a2a2a", bg=SURFACE)
        self.eta_lbl.pack(pady=(4, 0))

        self._msgs = ["Analizando procesos activos…", "Revisando historial de ejecución…",
                      "Escaneando conexiones de red…", "Verificando firmas digitales…",
                      "Revisando DLLs cargadas…", "Analizando prefetch…",
                      "Verificando drivers del sistema…", "Examinando registro de Windows…"]
        self._mi = 0
        self._animate_scan()

    def _animate_scan(self):
        frames = ["◐", "◓", "◑", "◒"]
        self.spinner_lbl.config(text=frames[self._spinner_i % 4])
        self._spinner_i += 1
        if self._spinner_i % 20 == 0:
            self.distract_lbl.config(text=self._msgs[self._mi % len(self._msgs)])
            self._mi += 1
        self._anim_job = self.root.after(180, self._animate_scan)

    # ─── Helpers ───────────────────────────────────────────────────
    def _fmt(self, _=None):
        raw = "".join(c for c in self.code_var.get().upper() if c.isalnum())[:6]
        fmt = raw if len(raw) <= 3 else f"{raw[:3]}-{raw[3:]}"
        if fmt != self.code_var.get():
            self.code_var.set(fmt); self.entry.icursor(tk.END)

    def _on_close(self):
        if self.running: return
        self.root.destroy()

    def _start(self):
        if self.running: return
        code = self.code_var.get().strip().upper()
        if len(code) < 5:
            self.status_lbl.config(text="Ingresá el código completo (XXX-XXX).", fg=ACCENT); return
        self.status_lbl.config(text="Validando…", fg="#444")
        self.btn.config(state="disabled")
        threading.Thread(target=self._run, args=(code,), daemon=True).start()

    def _run(self, code):
        try:
            claim = _http("POST", f"{SERVER}/api/codes/{code}/claim",
                           {"client_label": os.environ.get("COMPUTERNAME", "PC"), "game_mode": GAME_MODE})
        except urllib.error.HTTPError as e:
            msg = ("Código inválido o ya usado." if e.code in (404, 409)
                   else "Código expirado." if e.code == 410 else f"Error ({e.code}).")
            self.root.after(0, lambda: self._fail(msg)); return
        except Exception:
            self.root.after(0, lambda: self._fail("No se pudo conectar al servidor.")); return

        self.eta_total = claim.get("eta_seconds", 900)
        gm = claim.get("game_mode", GAME_MODE)
        deep = claim.get("deep", False)
        self.root.after(0, self._enter_scan)
        self.t0 = time.time(); self.running = True
        try:
            from core.scanner import run_full_scan
            def on_p(pct, label, module_id="", current=0, total=0, category="", duration_ms=0):
                rem = max(0, self.eta_total - (time.time() - self.t0))
                try: _http("POST", f"{SERVER}/api/codes/{code}/progress",
                           {"progress": pct, "label": label, "step": module_id,
                            "current": current, "total": total, "category": category,
                            "duration_ms": duration_ms, "eta_seconds": int(rem)}, timeout=5)
                except: pass
                self.root.after(0, lambda p=pct, r=rem, l=label: self._upd(p, r, l))
            results = run_full_scan(gm, code, on_p, lambda *a: None, deep=deep, workers=1)
            _http("POST", f"{SERVER}/api/codes/{code}/complete",
                  {"results": results, "duration_s": round(time.time() - self.t0, 1)}, timeout=30)
            self.root.after(0, self._done)
        except Exception as ex:
            self.root.after(0, lambda: self._fail(str(ex)))
        finally:
            self.running = False

    def _enter_scan(self):
        self.idle_frame.place_forget()
        self._build_scan()

    def _upd(self, pct, rem, label=""):
        w = int(340 * max(0, min(1, pct / 100)))
        self._pb_bg.coords(self.pb_fill, 0, 0, w, 5)
        self.pct_lbl.config(text=f"{int(pct)}%")
        if label: self.module_lbl.config(text=label, fg="#444")
        m, s = divmod(int(rem), 60)
        self.eta_lbl.config(text=f"Tiempo restante: {m}m {s:02d}s" if rem > 5 else "Finalizando…")

    def _done(self):
        if self._anim_job: self.root.after_cancel(self._anim_job)
        self._pb_bg.coords(self.pb_fill, 0, 0, 340, 5)
        self.pct_lbl.config(text="100%")
        self.spinner_lbl.config(text="✓", fg="#22c55e",
                                 font=tkfont.Font(family="Segoe UI", size=18, weight="bold"))
        self.status_top.config(text="● COMPLETADO", fg="#22c55e")
        self.module_lbl.config(text="Escaneo completado.", fg="#22c55e")
        self.eta_lbl.config(text="Podés cerrar esta ventana.")
        self.distract_lbl.config(text="")
        self.root.protocol("WM_DELETE_WINDOW", self.root.destroy)

    def _fail(self, msg):
        if self._anim_job: self.root.after_cancel(self._anim_job)
        self.running = False
        try: self.scan_frame.place_forget()
        except: pass
        self.idle_frame.place(x=0, y=0, width=WIN_W, height=WIN_H)
        self.status_lbl.config(text=msg, fg=ACCENT)
        self.btn.config(state="normal")


if __name__ == "__main__":
    root = tk.Tk()
    TitanXApp(root)
    root.mainloop()
