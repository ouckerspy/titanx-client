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

GAME_MODE   = "FiveM"
APP_VERSION = "2.6.0"
ACCENT    = "#dc2626"
ACCENT2   = "#8b5cf6"
BG        = "#060606"
SURFACE   = "#0d0d0d"
SURFACE2  = "#111111"
WIN_W, WIN_H = 980, 620
VERCEL_URL  = "https://titanx-landing.vercel.app"


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

        self.f_title  = tkfont.Font(family="Segoe UI", size=34, weight="bold")
        self.f_sub    = tkfont.Font(family="Segoe UI", size=10)
        self.f_label  = tkfont.Font(family="Segoe UI", size=8, weight="bold")
        self.f_code   = tkfont.Font(family="Consolas", size=30, weight="bold")
        self.f_btn    = tkfont.Font(family="Segoe UI", size=13, weight="bold")
        self.f_status = tkfont.Font(family="Segoe UI", size=9)
        self.f_pct    = tkfont.Font(family="Segoe UI", size=46, weight="bold")
        self.f_eta    = tkfont.Font(family="Segoe UI", size=9)
        self.f_module = tkfont.Font(family="Consolas", size=9)
        self.f_tag    = tkfont.Font(family="Segoe UI", size=8, weight="bold")

        self._build_idle()
        root.protocol("WM_DELETE_WINDOW", self._on_close)
        threading.Thread(target=self._check_update, daemon=True).start()

    # ─── Auto-update check ─────────────────────────────────────────
    def _check_update(self):
        try:
            req = urllib.request.Request(
                f"{VERCEL_URL}/version.json",
                headers={"User-Agent": "TitanXClient/2.5.0"}
            )
            with urllib.request.urlopen(req, timeout=5) as r:
                data = json.loads(r.read())
            latest = data.get("fivem", APP_VERSION)
            if latest != APP_VERSION:
                self.root.after(0, lambda v=latest: self._show_update_banner(v))
        except Exception:
            pass

    def _show_update_banner(self, new_version):
        banner = tk.Frame(self.idle_frame, bg="#1a0a0a",
                          highlightthickness=1, highlightbackground=ACCENT)
        banner.place(relx=0, rely=0, relwidth=1, height=46)
        tk.Label(banner, text=f"⬆  Nueva versión disponible: v{new_version}",
                 font=tkfont.Font(family="Segoe UI", size=10, weight="bold"),
                 fg="#fca5a5", bg="#1a0a0a").pack(side="left", padx=16)
        def _open_dl():
            import webbrowser
            webbrowser.open(f"{VERCEL_URL}/downloads/TitanXClient_FiveM.exe")
        tk.Button(banner, text="Descargar actualización", font=tkfont.Font(family="Segoe UI", size=9, weight="bold"),
                  fg="#fff", bg=ACCENT, activebackground="#b91c1c", activeforeground="#fff",
                  relief="flat", padx=14, pady=6, cursor="hand2", bd=0, command=_open_dl
                  ).pack(side="right", padx=16, pady=8)

    # ─── Idle screen ───────────────────────────────────────────────
    def _build_idle(self):
        self.idle_frame = tk.Frame(self.root, bg=BG)
        self.idle_frame.place(x=0, y=0, width=WIN_W, height=WIN_H)

        # Top accent line
        tk.Frame(self.idle_frame, bg=ACCENT, height=2).pack(fill="x")

        # Left panel — eye + title
        left = tk.Frame(self.idle_frame, bg=BG, width=WIN_W // 2)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)

        inner = tk.Frame(left, bg=BG)
        inner.place(relx=0.5, rely=0.5, anchor="center")

        # Version badge
        badge = tk.Frame(inner, bg="#1a0000")
        badge.pack(pady=(0, 14))
        tk.Label(badge, text=f"  TITAN X  v{APP_VERSION}  ", font=self.f_tag,
                 fg=ACCENT, bg="#1a0000").pack(padx=8, pady=4)

        # GIF eye — bigger
        try:
            self._gif = GifLabel(inner, _gif_path(), scale=2.2)
            self._gif.pack(pady=(0, 18))
        except Exception:
            tk.Label(inner, text="👁", font=tkfont.Font(size=80), bg=BG).pack(pady=(0, 18))

        tk.Label(inner, text="TITAN X", font=self.f_title, fg=ACCENT, bg=BG).pack()
        tk.Label(inner, text="Sistema de verificación forense avanzada",
                 font=self.f_sub, fg="#2a2a2a", bg=BG).pack(pady=(5, 0))

        # Stats row
        stats_row = tk.Frame(inner, bg=BG)
        stats_row.pack(pady=(18, 0))
        for label, val in [("MÓDULOS", "199"), ("JUEGO", "FiveM"), ("MODO", "Forense")]:
            col = tk.Frame(stats_row, bg="#0d0d0d", padx=12, pady=6)
            col.pack(side="left", padx=4)
            tk.Label(col, text=val, font=tkfont.Font(family="Segoe UI", size=11, weight="bold"),
                     fg="#fff", bg="#0d0d0d").pack()
            tk.Label(col, text=label, font=tkfont.Font(family="Segoe UI", size=7, weight="bold"),
                     fg="#2a2a2a", bg="#0d0d0d").pack()

        # Right panel — form
        right = tk.Frame(self.idle_frame, bg=SURFACE)
        right.pack(side="right", fill="both", expand=True)

        # Right top accent
        tk.Frame(right, bg="#1a1a1a", height=1).pack(fill="x")

        form = tk.Frame(right, bg=SURFACE)
        form.place(relx=0.5, rely=0.48, anchor="center")

        tk.Label(form, text="CÓDIGO DE ESCANEO SS", font=self.f_label,
                 fg="#444", bg=SURFACE).pack(anchor="w", pady=(0, 8))

        self._ef = tk.Frame(form, bg="#0a0a0a",
                             highlightthickness=2, highlightbackground="#1a1a1a")
        self._ef.pack(pady=(0, 10))
        self.code_var = tk.StringVar()
        self.entry = tk.Entry(
            self._ef, textvariable=self.code_var, font=self.f_code,
            justify="center", width=7, bg="#0a0a0a", fg="#fff",
            insertbackground=ACCENT, relief="flat", bd=12, highlightthickness=0,
        )
        self.entry.pack()
        self.entry.bind("<KeyRelease>", self._fmt)
        self.entry.bind("<Return>", lambda e: self._start())
        self.entry.bind("<FocusIn>",  lambda e: self._ef.config(highlightbackground=ACCENT))
        self.entry.bind("<FocusOut>", lambda e: self._ef.config(highlightbackground="#1a1a1a"))

        self.status_lbl = tk.Label(form, text="Ingresá el código que te dio el staff",
                                    font=self.f_status, fg="#2a2a2a", bg=SURFACE)
        self.status_lbl.pack(pady=(2, 18))

        self.btn = tk.Button(
            form, text="⚡  INICIAR VERIFICACIÓN", font=self.f_btn,
            fg="#fff", bg=ACCENT, activebackground="#b91c1c", activeforeground="#fff",
            relief="flat", padx=50, pady=16, cursor="hand2", command=self._start, bd=0,
        )
        self.btn.pack()

        # Info note
        tk.Label(form, text="El escaneo corre localmente. Solo el staff ve el resultado.",
                 font=tkfont.Font(family="Segoe UI", size=8),
                 fg="#1a1a1a", bg=SURFACE).pack(pady=(14, 0))

        # Bottom bar
        bot = tk.Frame(right, bg="#0a0a0a", height=30)
        bot.pack(side="bottom", fill="x"); bot.pack_propagate(False)
        tk.Label(bot, text=f"FiveM · 199 módulos forenses · v{APP_VERSION}",
                 font=tkfont.Font(family="Segoe UI", size=8),
                 fg="#1f1f1f", bg="#0a0a0a").pack(side="left", padx=14, pady=7)
        tk.Label(bot, text="titanx-landing.vercel.app",
                 font=tkfont.Font(family="Segoe UI", size=8),
                 fg="#1f1f1f", bg="#0a0a0a").pack(side="right", padx=14, pady=7)

    # ─── Scan screen ───────────────────────────────────────────────
    def _build_scan(self):
        self.scan_frame = tk.Frame(self.root, bg=BG)
        self.scan_frame.place(x=0, y=0, width=WIN_W, height=WIN_H)

        # Top accent line
        tk.Frame(self.scan_frame, bg=ACCENT, height=2).pack(fill="x")

        bar = tk.Frame(self.scan_frame, bg="#0a0a0a", height=48)
        bar.pack(fill="x"); bar.pack_propagate(False)
        tk.Label(bar, text="TITAN X",
                 font=tkfont.Font(family="Segoe UI", size=13, weight="bold"),
                 fg=ACCENT, bg="#0a0a0a").pack(side="left", padx=22, pady=12)
        tk.Label(bar, text=f"v{APP_VERSION}",
                 font=tkfont.Font(family="Segoe UI", size=9),
                 fg="#222", bg="#0a0a0a").pack(side="left", pady=12)
        self.status_top = tk.Label(bar, text="● ESCANEANDO",
                                    font=tkfont.Font(family="Segoe UI", size=9, weight="bold"),
                                    fg="#22c55e", bg="#0a0a0a")
        self.status_top.pack(side="right", padx=22)

        content = tk.Frame(self.scan_frame, bg=BG)
        content.pack(fill="both", expand=True)

        # Left: BIG GIF centered
        left = tk.Frame(content, bg=BG, width=360)
        left.pack(side="left", fill="y"); left.pack_propagate(False)
        try:
            gif2 = GifLabel(left, _gif_path(), scale=2.0)
            gif2.place(relx=0.5, rely=0.5, anchor="center")
        except Exception:
            pass

        # Right: progress
        right = tk.Frame(content, bg=SURFACE)
        right.pack(side="right", fill="both", expand=True)
        pa = tk.Frame(right, bg=SURFACE)
        pa.place(relx=0.5, rely=0.5, anchor="center")

        # Module counter badge
        self.module_counter_lbl = tk.Label(pa, text="0 / 199 módulos",
                 font=tkfont.Font(family="Segoe UI", size=8, weight="bold"),
                 fg="#222", bg=SURFACE)
        self.module_counter_lbl.pack(pady=(0, 6))

        self.pct_lbl = tk.Label(pa, text="0%", font=self.f_pct, fg=ACCENT, bg=SURFACE)
        self.pct_lbl.pack()

        # Thick progress bar
        pb_bg = tk.Canvas(pa, width=360, height=8, bg="#111", highlightthickness=0)
        pb_bg.pack(pady=(10, 6))
        self.pb_fill = pb_bg.create_rectangle(0, 0, 0, 8, fill=ACCENT, width=0)
        self._pb_bg = pb_bg

        self.module_lbl = tk.Label(pa, text="Iniciando módulos…",
                                    font=self.f_module, fg="#2a2a2a", bg=SURFACE,
                                    wraplength=340, justify="center")
        self.module_lbl.pack(pady=(2, 18))

        # Category tag
        self.cat_lbl = tk.Label(pa, text="",
                 font=tkfont.Font(family="Segoe UI", size=8, weight="bold"),
                 fg=ACCENT2, bg=SURFACE)
        self.cat_lbl.pack(pady=(0, 14))

        tk.Label(pa, text="⚠  NO CIERRES ESTA VENTANA",
                 font=tkfont.Font(family="Segoe UI", size=10, weight="bold"),
                 fg="#fff", bg=SURFACE).pack()
        tk.Label(pa, text="El análisis forense corre localmente. Solo el staff ve el resultado.",
                 font=self.f_status, fg="#222", bg=SURFACE).pack(pady=(5, 20))

        self.spinner_lbl = tk.Label(pa, text="◐",
                                     font=tkfont.Font(family="Segoe UI", size=18),
                                     fg=ACCENT, bg=SURFACE)
        self.spinner_lbl.pack()
        self.distract_lbl = tk.Label(pa, text="", font=self.f_module, fg="#222", bg=SURFACE,
                                      wraplength=340, justify="center")
        self.distract_lbl.pack(pady=(5, 0))
        self.eta_lbl = tk.Label(pa, text="", font=self.f_eta, fg="#1a1a1a", bg=SURFACE)
        self.eta_lbl.pack(pady=(4, 0))

        self._msgs = [
            "Analizando procesos activos en memoria…",
            "Revisando historial de ejecución de Windows…",
            "Escaneando conexiones de red activas…",
            "Verificando firmas digitales de módulos…",
            "Revisando DLLs cargadas en procesos del juego…",
            "Analizando prefetch y caché de ejecución…",
            "Verificando drivers y kernel modules…",
            "Examinando claves de registro de autorun…",
            "Escaneando mutexes de cheats conocidos…",
            "Revisando named pipes sospechosos…",
            "Analizando historial de PowerShell…",
            "Verificando archivo hosts y reglas de firewall…",
            "Buscando ventanas ocultas de cheats…",
            "Revisando extensiones de navegador…",
            "Analizando journal de USN del sistema de archivos…",
        ]
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
                self.root.after(0, lambda p=pct, r=rem, l=label, cat=category, d=current, t=total: self._upd(p, r, l, cat, d, t))
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

    def _upd(self, pct, rem, label="", category="", done=0, total=0):
        w = int(360 * max(0, min(1, pct / 100)))
        self._pb_bg.coords(self.pb_fill, 0, 0, w, 8)
        self.pct_lbl.config(text=f"{int(pct)}%")
        if label:
            self.module_lbl.config(text=label, fg="#444")
        if category:
            self.cat_lbl.config(text=f"[ {category.upper()} ]")
        if total:
            self.module_counter_lbl.config(text=f"{done} / {total} módulos", fg="#333")
        m, s = divmod(int(rem), 60)
        self.eta_lbl.config(text=f"Tiempo restante: {m}m {s:02d}s" if rem > 5 else "Finalizando…")

    def _done(self):
        if self._anim_job: self.root.after_cancel(self._anim_job)
        self._pb_bg.coords(self.pb_fill, 0, 0, 360, 8)
        self.pct_lbl.config(text="100%")
        self.spinner_lbl.config(text="✓", fg="#22c55e",
                                 font=tkfont.Font(family="Segoe UI", size=22, weight="bold"))
        self.status_top.config(text="● COMPLETADO", fg="#22c55e")
        self.module_lbl.config(text="Análisis forense completo.", fg="#22c55e")
        self.cat_lbl.config(text="")
        self.module_counter_lbl.config(text="")
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
