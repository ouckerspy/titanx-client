"""
TITAN X — Cliente FiveM
Empaquetar:
    pyinstaller --onefile --noconsole --uac-admin --name TitanXClient_FiveM ^
        --add-data "core;core" --add-data "config.py;." --add-data "client/eye.gif;." ^
        --paths . client/titanx_client.py
"""
import sys, os, io, json, time, threading, urllib.request, urllib.error

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tkinter as tk
from tkinter import font as tkfont
from PIL import Image, ImageTk, ImageDraw, ImageFilter

GAME_MODE   = "FiveM"
APP_VERSION = "2.8.1"

# ─── Paleta base del proyecto (no modificar) ────────────────────────────────
ACCENT   = "#dc2626"
ACCENT2  = "#8b5cf6"
BG       = "#060606"
SURFACE  = "#0d0d0d"
SURFACE2 = "#111111"

# ─── Tonos derivados: dan profundidad sin caer en neon/glow ────────────────
ACCENT_HOVER = "#ef4444"
ACCENT_PRESS = "#b91c1c"
ACCENT_SOFT  = "#210a0a"
ACCENT_LINE  = "#3a1414"
CARD_BG      = "#0f0f0f"
CARD_BORDER  = "#1c1414"
LINE         = "#171717"
LINE_SOFT    = "#1f1f1f"
TXT_PRIMARY   = "#f4f4f4"
TXT_SECONDARY = "#8f8f8f"
TXT_MUTED     = "#565656"
TXT_FAINT     = "#2c2c2c"
GREEN         = "#22c55e"

WIN_W, WIN_H  = 1040, 660
VERCEL_URL    = "https://titanxanticheat.xyz"
TOTAL_MODULES = 201


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


# ─── Helpers de dibujo: esquinas redondeadas + iconografia vectorial ───────
def round_rect_points(x1, y1, x2, y2, r):
    """Puntos de un rectangulo con esquinas redondeadas, listos para
    canvas.create_polygon(..., smooth=True)."""
    r = max(0, min(r, abs(x2 - x1) / 2, abs(y2 - y1) / 2))
    return [
        x1 + r, y1,
        x2 - r, y1,
        x2, y1,
        x2, y1 + r,
        x2, y2 - r,
        x2, y2,
        x2 - r, y2,
        x1 + r, y2,
        x1, y2,
        x1, y2 - r,
        x1, y1 + r,
        x1, y1,
    ]


def draw_round_rect(canvas, x1, y1, x2, y2, r=12, **kw):
    """Dibuja un rectangulo con esquinas redondeadas y devuelve su item id."""
    kw.setdefault("smooth", True)
    kw.setdefault("splinesteps", 20)
    return canvas.create_polygon(round_rect_points(x1, y1, x2, y2, r), **kw)


def update_round_rect(canvas, item_id, x1, y1, x2, y2, r):
    """Actualiza un rectangulo redondeado ya existente (misma cantidad de puntos)."""
    canvas.coords(item_id, *round_rect_points(x1, y1, x2, y2, r))


# ─── Helpers de glow/neon: tkinter Canvas no soporta blur nativo, asi que ──
# lo simulamos rasterizando un halo con PIL (ImageDraw + GaussianBlur) y
# pegandolo como PhotoImage. Se usa para halos SUTILES (alpha bajo, blur
# moderado), nunca para saturar la UI.
def hex_to_rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def lighten_hex(h, amt=0.25):
    """Aclara un color hex hacia blanco en la proporcion `amt` (0-1)."""
    r, g, b = hex_to_rgb(h)
    r = int(r + (255 - r) * amt); g = int(g + (255 - g) * amt); b = int(b + (255 - b) * amt)
    return f"#{r:02x}{g:02x}{b:02x}"


def make_glow_image(width, height, color_hex, blur=18, alpha=150, radius=None, shape="rect"):
    """Genera un halo de luz suave como PhotoImage RGBA (transparente afuera
    del halo). `shape` puede ser 'rect' (rounded_rectangle) o 'ellipse'."""
    width, height = max(2, int(width)), max(2, int(height))
    rgb = hex_to_rgb(color_hex)
    img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    pad = blur
    x1, y1, x2, y2 = pad, pad, width - pad, height - pad
    if x2 <= x1: x1, x2 = width / 2.0 - 1, width / 2.0 + 1
    if y2 <= y1: y1, y2 = height / 2.0 - 1, height / 2.0 + 1
    if shape == "ellipse":
        draw.ellipse([x1, y1, x2, y2], fill=rgb + (alpha,))
    else:
        r = radius if radius is not None else max(6, (min(width, height) - 2 * pad) // 3)
        r = max(1, min(r, (x2 - x1) / 2, (y2 - y1) / 2))
        draw.rounded_rectangle([x1, y1, x2, y2], radius=r, fill=rgb + (alpha,))
    img = img.filter(ImageFilter.GaussianBlur(blur))
    return ImageTk.PhotoImage(img)


def make_gradient(width, height, color1_hex, color2_hex, horizontal=True):
    """Gradiente PIL entre dos colores (renderizado como imagen 2x1/1x2 y
    escalado — mucho mas rapido que iterar pixel por pixel)."""
    rgb1, rgb2 = hex_to_rgb(color1_hex), hex_to_rgb(color2_hex)
    if horizontal:
        base = Image.new("RGB", (2, 1))
        base.putpixel((0, 0), rgb1); base.putpixel((1, 0), rgb2)
    else:
        base = Image.new("RGB", (1, 2))
        base.putpixel((0, 0), rgb1); base.putpixel((0, 1), rgb2)
    return base.resize((max(1, int(width)), max(1, int(height))), Image.BILINEAR)


def make_gradient_round_image(width, height, color1_hex, color2_hex, radius=12,
                               horizontal=True):
    """Rectangulo redondeado con relleno degrade, devuelto como PhotoImage RGBA."""
    width, height = max(2, int(width)), max(2, int(height))
    grad = make_gradient(width, height, color1_hex, color2_hex, horizontal).convert("RGBA")
    mask = Image.new("L", (width, height), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, width - 1, height - 1],
                                            radius=radius, fill=255)
    grad.putalpha(mask)
    return ImageTk.PhotoImage(grad)


def draw_icon(canvas, kind, cx, cy, size=16, color=ACCENT, width=1.6):
    """Dibuja un glifo vectorial simple centrado en (cx, cy)."""
    half = size / 2.0

    def pt(fx, fy):
        return (cx - half + fx * size, cy - half + fy * size)

    if kind == "bolt":
        pts = []
        for fx, fy in [(0.58, 0.0), (0.16, 0.58), (0.44, 0.58),
                        (0.34, 1.0), (0.86, 0.4), (0.52, 0.4)]:
            pts.extend(pt(fx, fy))
        canvas.create_polygon(pts, fill=color, outline="")

    elif kind == "shield":
        pts = []
        for fx, fy in [(0.5, 0.02), (0.88, 0.2), (0.88, 0.55),
                        (0.5, 0.98), (0.12, 0.55), (0.12, 0.2)]:
            pts.extend(pt(fx, fy))
        canvas.create_polygon(pts, outline=color, fill="", width=width,
                               joinstyle="round", smooth=True)

    elif kind == "shield-check":
        draw_icon(canvas, "shield", cx, cy, size, color, width)
        x1, y1 = pt(0.30, 0.48); x2, y2 = pt(0.45, 0.64); x3, y3 = pt(0.72, 0.32)
        canvas.create_line(x1, y1, x2, y2, x3, y3, fill=color, width=width,
                            capstyle="round", joinstyle="round")

    elif kind == "eye-off":
        x1, y1 = pt(0.05, 0.5); x2, y2 = pt(0.5, 0.2); x3, y3 = pt(0.95, 0.5); x4, y4 = pt(0.5, 0.8)
        canvas.create_polygon(x1, y1, x2, y2, x3, y3, x4, y4, outline=color,
                               fill="", width=width, smooth=True)
        r = size * 0.09
        canvas.create_oval(cx - r, cy - r, cx + r, cy + r, fill=color, outline="")
        lx1, ly1 = pt(0.06, 0.88); lx2, ly2 = pt(0.94, 0.12)
        canvas.create_line(lx1, ly1, lx2, ly2, fill=color, width=width + 0.4, capstyle="round")

    elif kind == "eye":
        x1, y1 = pt(0.02, 0.5); x2, y2 = pt(0.5, 0.1); x3, y3 = pt(0.98, 0.5); x4, y4 = pt(0.5, 0.9)
        canvas.create_polygon(x1, y1, x2, y2, x3, y3, x4, y4, outline=color,
                               fill="", width=width, smooth=True)
        r = size * 0.17
        canvas.create_oval(cx - r, cy - r, cx + r, cy + r, outline=color, width=width)
        r2 = size * 0.065
        canvas.create_oval(cx - r2, cy - r2, cx + r2, cy + r2, fill=color, outline="")

    elif kind == "check":
        x1, y1 = pt(0.14, 0.52); x2, y2 = pt(0.4, 0.78); x3, y3 = pt(0.88, 0.18)
        canvas.create_line(x1, y1, x2, y2, x3, y3, fill=color, width=width + 0.8,
                            capstyle="round", joinstyle="round")

    elif kind == "alert":
        x1, y1 = pt(0.5, 0.04); x2, y2 = pt(0.97, 0.92); x3, y3 = pt(0.03, 0.92)
        canvas.create_polygon(x1, y1, x2, y2, x3, y3, outline=color, fill="",
                               width=width, joinstyle="round")
        _, ly1 = pt(0.5, 0.36)
        _, ly2 = pt(0.5, 0.64)
        canvas.create_line(cx, ly1, cx, ly2, fill=color, width=width + 0.4, capstyle="round")
        r = max(1.0, size * 0.045)
        dx, dy = pt(0.5, 0.78)
        canvas.create_oval(dx - r, dy - r, dx + r, dy + r, fill=color, outline="")

    elif kind == "dot":
        canvas.create_oval(cx - half * 0.7, cy - half * 0.7, cx + half * 0.7, cy + half * 0.7,
                            fill=color, outline="")

    elif kind == "arrow-up":
        pts = []
        for fx, fy in [(0.5, 0.05), (0.85, 0.42), (0.62, 0.42),
                        (0.62, 0.95), (0.38, 0.95), (0.38, 0.42), (0.15, 0.42)]:
            pts.extend(pt(fx, fy))
        canvas.create_polygon(pts, fill=color, outline="")


def make_icon(parent, kind, size=16, color=ACCENT, bg=SURFACE, width=1.6):
    """Crea un Canvas chico con un icono vectorial ya dibujado adentro."""
    c = tk.Canvas(parent, width=size, height=size, bg=bg, highlightthickness=0, bd=0)
    draw_icon(c, kind, size / 2, size / 2, size, color, width)
    return c


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


class RoundButton(tk.Canvas):
    """Boton con esquinas redondeadas dibujado en Canvas, con hover/press
    reales (no el activebackground tosco de tk.Button)."""
    def __init__(self, parent, text, command=None, width=340, height=58, radius=14,
                 bg=SURFACE, fill=ACCENT, hover=ACCENT_HOVER, press=ACCENT_PRESS,
                 disabled_fill="#241010", fg="#ffffff", disabled_fg="#7a4a4a",
                 font=None, icon=None):
        super().__init__(parent, width=width, height=height, bg=bg,
                          highlightthickness=0, bd=0, cursor="hand2")
        self._bw, self._h, self._r = width, height, radius
        self._command = command
        self._fill, self._hover, self._press = fill, hover, press
        self._disabled_fill, self._fg, self._disabled_fg = disabled_fill, fg, disabled_fg
        self._font = font or tkfont.Font(family="Segoe UI", size=13, weight="bold")
        self._text = text
        self._icon = icon
        self._state = "normal"

        # Relleno degrade (mas claro arriba, color base abajo) precalculado
        # por estado — se guarda una referencia persistente en self._grad_cache
        # para evitar que el garbage collector se lleve los PhotoImage.
        self._grad_cache = {}
        for c in (fill, hover, press):
            self._grad_cache[c] = make_gradient_round_image(
                width, height, lighten_hex(c, 0.24), c, radius=radius, horizontal=False)

        self._render(self._fill)

        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)

    def _render(self, color):
        self.delete("all")
        grad = self._grad_cache.get(color)
        if grad is not None:
            self.create_image(self._bw / 2, self._h / 2, image=grad)
        else:
            draw_round_rect(self, 1, 1, self._bw - 1, self._h - 1, self._r, fill=color, outline="")
        fg = self._fg if self._state == "normal" else self._disabled_fg
        text_id = self.create_text(0, self._h / 2, text=self._text, font=self._font,
                                    fill=fg, anchor="w")
        bbox = self.bbox(text_id)
        text_w = (bbox[2] - bbox[0]) if bbox else 0
        icon_size, gap = 18, 10
        total_w = (icon_size + gap + text_w) if self._icon else text_w
        start_x = max(8, (self._bw - total_w) / 2)
        if self._icon:
            draw_icon(self, self._icon, start_x + icon_size / 2, self._h / 2, icon_size, fg, 2.0)
            self.coords(text_id, start_x + icon_size + gap, self._h / 2)
        else:
            self.coords(text_id, start_x, self._h / 2)

    def _on_enter(self, _e):
        if self._state == "normal": self._render(self._hover)

    def _on_leave(self, _e):
        if self._state == "normal": self._render(self._fill)

    def _on_press(self, _e):
        if self._state == "normal": self._render(self._press)

    def _on_release(self, _e):
        if self._state != "normal": return
        self._render(self._hover)
        if self._command: self._command()

    def config(self, **kw):
        changed = False
        if "state" in kw:
            self._state = kw.pop("state")
            changed = True
        if "text" in kw:
            self._text = kw.pop("text")
            changed = True
        if changed:
            self._render(self._fill if self._state == "normal" else self._disabled_fill)
        if kw:
            super().config(**kw)
    configure = config


class Spinner(tk.Canvas):
    """Indicador de progreso circular: arco animado en canvas (reemplaza
    el caracter unicode rotando)."""
    def __init__(self, parent, size=36, color=ACCENT, bg=SURFACE, width=3):
        super().__init__(parent, width=size, height=size, bg=bg, highlightthickness=0, bd=0)
        self._size, self._color, self._width = size, color, width
        self._angle = 0
        self._extent = 120
        self._job = None
        self._running = False
        self._arc = None
        self._draw()

    def _draw(self):
        self.delete("all")
        pad = self._width + 1
        self._arc = self.create_arc(
            pad, pad, self._size - pad, self._size - pad,
            start=self._angle, extent=self._extent,
            style="arc", outline=self._color, width=self._width,
        )

    def start(self):
        if self._running: return
        self._running = True
        self._draw()
        self._tick()

    def _tick(self):
        if not self._running: return
        self._angle = (self._angle - 10) % 360
        self.itemconfigure(self._arc, start=self._angle)
        self._job = self.after(45, self._tick)

    def stop(self):
        self._running = False
        if self._job:
            self.after_cancel(self._job)
            self._job = None

    def show_check(self):
        self.stop()
        self.delete("all")
        draw_icon(self, "check", self._size / 2, self._size / 2, self._size * 0.8, GREEN, 3.0)

    def config(self, **kw):
        # Shim de compatibilidad: absorbe opciones estilo Label (text/fg/font)
        # que pudiera enviarle codigo legado, sin romper la app.
        native = {k: v for k, v in kw.items() if k not in ("text", "fg", "font")}
        if native:
            super().config(**native)
    configure = config


class TitanXApp:
    def __init__(self, root):
        self.root    = root
        self.running = False
        self.eta_total = 0
        self.t0 = None
        self._anim_job = None
        self._spinner_i = 0
        self._glow_refs = []   # referencias persistentes a PhotoImage de glow (evita GC)
        self._pb_glow_ref = None

        root.title("TITAN X")
        root.configure(bg=BG)
        root.geometry(f"{WIN_W}x{WIN_H}")
        root.resizable(False, False)
        try: root.iconbitmap(default="")
        except: pass

        self.f_title    = tkfont.Font(family="Segoe UI", size=34, weight="bold")
        self.f_sub      = tkfont.Font(family="Segoe UI", size=10)
        self.f_label    = tkfont.Font(family="Segoe UI", size=8, weight="bold")
        self.f_code     = tkfont.Font(family="Consolas", size=30, weight="bold")
        self.f_btn      = tkfont.Font(family="Segoe UI", size=13, weight="bold")
        self.f_status   = tkfont.Font(family="Segoe UI", size=9)
        self.f_pct      = tkfont.Font(family="Segoe UI", size=46, weight="bold")
        self.f_eta      = tkfont.Font(family="Segoe UI", size=9)
        self.f_module   = tkfont.Font(family="Consolas", size=9)
        self.f_tag      = tkfont.Font(family="Segoe UI", size=8, weight="bold")
        self.f_feat     = tkfont.Font(family="Segoe UI", size=8)
        self.f_stat_val = tkfont.Font(family="Segoe UI", size=12, weight="bold")
        self.f_stat_lbl = tkfont.Font(family="Segoe UI", size=7, weight="bold")
        self.f_cat      = tkfont.Font(family="Segoe UI", size=9)
        self.f_cat_bold = tkfont.Font(family="Segoe UI", size=9, weight="bold")

        self._build_idle()
        root.protocol("WM_DELETE_WINDOW", self._on_close)
        threading.Thread(target=self._check_update, daemon=True).start()

    # ─── Auto-update check ──────────────────────────────────────────────
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
        banner = tk.Frame(self.idle_frame, bg=ACCENT_SOFT,
                           highlightthickness=1, highlightbackground=ACCENT)
        banner.place(relx=0, rely=0, relwidth=1, height=46)

        left = tk.Frame(banner, bg=ACCENT_SOFT)
        left.pack(side="left", padx=16)
        make_icon(left, "arrow-up", size=14, color="#fca5a5", bg=ACCENT_SOFT).pack(side="left", padx=(0, 8))
        tk.Label(left, text=f"Nueva versión disponible: v{new_version}",
                 font=tkfont.Font(family="Segoe UI", size=10, weight="bold"),
                 fg="#fca5a5", bg=ACCENT_SOFT).pack(side="left")

        def _open_dl():
            import webbrowser
            webbrowser.open(f"{VERCEL_URL}/downloads/TitanXClient_FiveM.exe")

        dl_btn = tk.Button(banner, text="Descargar actualización",
                            font=tkfont.Font(family="Segoe UI", size=9, weight="bold"),
                            fg="#fff", bg=ACCENT, activebackground=ACCENT_PRESS, activeforeground="#fff",
                            relief="flat", padx=14, pady=6, cursor="hand2", bd=0, command=_open_dl)
        dl_btn.pack(side="right", padx=16, pady=8)
        dl_btn.bind("<Enter>", lambda e: dl_btn.config(bg=ACCENT_HOVER))
        dl_btn.bind("<Leave>", lambda e: dl_btn.config(bg=ACCENT))

    # ─── Fabricas de widgets tipo tarjeta ───────────────────────────────
    def _make_badge(self, parent, text):
        tw = self.f_tag.measure(text)
        w, h = tw + 34, 30
        pad = 22
        cw, ch = w + 2 * pad, h + 2 * pad
        c = tk.Canvas(parent, width=cw, height=ch, bg=BG, highlightthickness=0, bd=0)
        glow_img = make_glow_image(cw, ch, ACCENT, blur=pad, alpha=210, radius=h / 2)
        self._glow_refs.append(glow_img)
        c.create_image(cw / 2, ch / 2, image=glow_img)
        pill_img = make_gradient_round_image(w, h, ACCENT_PRESS, ACCENT_HOVER,
                                              radius=h / 2, horizontal=True)
        self._glow_refs.append(pill_img)
        c.create_image(cw / 2, ch / 2, image=pill_img)
        c.create_text(cw / 2, ch / 2, text=text, font=self.f_tag, fill="#ffffff")
        return c

    def _make_stat_card(self, parent, value, label, width=108, height=62):
        c = tk.Canvas(parent, width=width, height=height, bg=BG, highlightthickness=0, bd=0)
        draw_round_rect(c, 0, 0, width - 1, height - 1, 10, fill=CARD_BG, outline=CARD_BORDER, width=1)
        # Glow sutil detras del borde superior de acento (queda "encendido" en
        # la propia superficie de la tarjeta, sin salirse del card).
        glow_w, glow_h = width - 20, 26
        glow_img = make_glow_image(glow_w, glow_h, ACCENT, blur=13, alpha=200, radius=glow_h / 2)
        self._glow_refs.append(glow_img)
        c.create_image(width / 2, 4, image=glow_img)
        c.create_line(16, 2, width - 16, 2, fill=ACCENT, width=2, capstyle="round")
        c.create_text(width / 2, height * 0.42, text=value, font=self.f_stat_val, fill=TXT_PRIMARY)
        c.create_text(width / 2, height * 0.76, text=label, font=self.f_stat_lbl, fill=TXT_MUTED)
        return c

    # ─── Idle screen ─────────────────────────────────────────────────────
    def _build_idle(self):
        self.idle_frame = tk.Frame(self.root, bg=BG)
        self.idle_frame.place(x=0, y=0, width=WIN_W, height=WIN_H)

        tk.Frame(self.idle_frame, bg=ACCENT, height=2).pack(fill="x")

        body = tk.Frame(self.idle_frame, bg=BG)
        body.pack(fill="both", expand=True)

        # Left panel — eye + title
        left = tk.Frame(body, bg=BG, width=WIN_W // 2)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)

        tk.Frame(body, bg=LINE, width=1).pack(side="left", fill="y")

        inner = tk.Frame(left, bg=BG)
        inner.place(relx=0.5, rely=0.5, anchor="center")

        self._make_badge(inner, f"TITAN X  ·  v{APP_VERSION}").pack(pady=(0, 16))

        try:
            self._gif = GifLabel(inner, _gif_path(), scale=1.1)
            self._gif.pack(pady=(0, 18))
            eye_widget = self._gif
        except Exception:
            eye_widget = make_icon(inner, "eye", size=110, color=ACCENT, bg=BG)
            eye_widget.pack(pady=(0, 18))

        # Blob de luz ambiental grande y muy difuminado, ubicado justo detras
        # del ojo (da atmosfera sutil sin saturar). Se posiciona con la
        # geometria real del widget del ojo ya empacado, y se baja (lower)
        # para quedar detras de el en el stacking order.
        inner.update_idletasks()
        eye_w = eye_widget.winfo_width() or eye_widget.winfo_reqwidth()
        eye_h = eye_widget.winfo_height() or eye_widget.winfo_reqheight()
        eye_cx = eye_widget.winfo_x() + eye_w / 2
        eye_cy = eye_widget.winfo_y() + eye_h / 2
        blob_w = max(60, int(eye_w * 1.2))
        blob_h = max(60, int(eye_h * 1.2))
        ambient_img = make_glow_image(blob_w, blob_h, ACCENT, blur=50, alpha=150, shape="ellipse")
        self._glow_refs.append(ambient_img)
        ambient = tk.Canvas(inner, width=blob_w, height=blob_h, bg=BG, highlightthickness=0, bd=0)
        ambient.create_image(blob_w / 2, blob_h / 2, image=ambient_img)
        ambient.place(x=eye_cx, y=eye_cy, anchor="center")
        # OJO: Canvas.lower() esta sobrecargado para items del canvas (alias
        # de tag_lower), NO para el stacking order del widget. Hay que llamar
        # explicitamente al lower() base (tk.Misc/Widget) para bajar el
        # propio canvas de glow detras del widget del ojo.
        tk.Widget.lower(ambient, eye_widget)

        title_txt = "TITAN X"
        title_w = self.f_title.measure(title_txt) + 90
        title_h = self.f_title.metrics("linespace") + 50
        title_wrap = tk.Canvas(inner, width=title_w, height=title_h, bg=BG,
                                highlightthickness=0, bd=0)
        title_wrap.pack()
        title_glow_img = make_glow_image(title_w, title_h, ACCENT, blur=26,
                                          alpha=200, shape="ellipse")
        self._glow_refs.append(title_glow_img)
        title_wrap.create_image(title_w / 2, title_h / 2, image=title_glow_img)
        title_wrap.create_text(title_w / 2, title_h / 2, text=title_txt,
                                font=self.f_title, fill="#ffffff")

        tk.Label(inner, text="Sistema de verificación forense avanzada",
                 font=self.f_sub, fg=TXT_FAINT, bg=BG).pack(pady=(5, 0))

        stats_row = tk.Frame(inner, bg=BG)
        stats_row.pack(pady=(20, 0))
        for label, val in [("MÓDULOS", str(TOTAL_MODULES)), ("JUEGO", "FiveM"), ("MODO", "Forense")]:
            self._make_stat_card(stats_row, val, label).pack(side="left", padx=5)

        # Right panel — form
        right = tk.Frame(body, bg=SURFACE)
        right.pack(side="right", fill="both", expand=True)

        tk.Frame(right, bg=LINE_SOFT, height=1).pack(fill="x")

        form = tk.Frame(right, bg=SURFACE)
        form.place(relx=0.5, rely=0.46, anchor="center")

        tk.Label(form, text="CÓDIGO DE ESCANEO SS", font=self.f_label,
                 fg=TXT_MUTED, bg=SURFACE).pack(anchor="w", pady=(0, 8))

        code_w, code_h = 220, 82
        code_pad = 16
        cw_total, ch_total = code_w + 2 * code_pad, code_h + 2 * code_pad
        code_wrap = tk.Canvas(form, width=cw_total, height=ch_total, bg=SURFACE,
                               highlightthickness=0, bd=0)
        code_wrap.pack(pady=(0, 10))

        # Glow que aparece solo cuando el input tiene foco (oculto por defecto).
        code_glow_img = make_glow_image(cw_total, ch_total, ACCENT, blur=code_pad,
                                         alpha=210, radius=16)
        self._glow_refs.append(code_glow_img)
        self._code_glow_item = code_wrap.create_image(cw_total / 2, ch_total / 2, image=code_glow_img)
        code_wrap.itemconfigure(self._code_glow_item, state="hidden")

        code_card = tk.Canvas(code_wrap, width=code_w, height=code_h, bg=SURFACE,
                               highlightthickness=0, bd=0)
        code_wrap.create_window(cw_total / 2, ch_total / 2, window=code_card)
        self._code_rect = draw_round_rect(code_card, 1, 1, code_w - 1, code_h - 1, 14,
                                           fill="#0a0a0a", outline=LINE_SOFT, width=2)
        self.code_var = tk.StringVar()
        self.entry = tk.Entry(
            code_card, textvariable=self.code_var, font=self.f_code,
            justify="center", width=7, bg="#0a0a0a", fg=TXT_PRIMARY,
            insertbackground=ACCENT, relief="flat", bd=0, highlightthickness=0,
        )
        code_card.create_window(code_w / 2, code_h / 2, window=self.entry)

        def _code_focus_in(_e):
            code_card.itemconfig(self._code_rect, outline=ACCENT)
            code_wrap.itemconfigure(self._code_glow_item, state="normal")

        def _code_focus_out(_e):
            code_card.itemconfig(self._code_rect, outline=LINE_SOFT)
            code_wrap.itemconfigure(self._code_glow_item, state="hidden")

        self.entry.bind("<KeyRelease>", self._fmt)
        self.entry.bind("<Return>", lambda e: self._start())
        self.entry.bind("<FocusIn>",  _code_focus_in)
        self.entry.bind("<FocusOut>", _code_focus_out)

        self.status_lbl = tk.Label(form, text="Ingresá el código que te dio el staff",
                                    font=self.f_status, fg=TXT_FAINT, bg=SURFACE)
        self.status_lbl.pack(pady=(2, 18))

        btn_w, btn_h, btn_pad = 340, 58, 14
        bw_total, bh_total = btn_w + 2 * btn_pad, btn_h + 2 * btn_pad
        btn_wrap = tk.Canvas(form, width=bw_total, height=bh_total, bg=SURFACE,
                              highlightthickness=0, bd=0)
        btn_wrap.pack()
        btn_glow_img = make_glow_image(bw_total, bh_total, ACCENT, blur=btn_pad + 8,
                                        alpha=220, radius=16)
        self._glow_refs.append(btn_glow_img)
        btn_wrap.create_image(bw_total / 2, bh_total / 2, image=btn_glow_img)

        self.btn = RoundButton(
            btn_wrap, text="INICIAR VERIFICACIÓN", command=self._start,
            width=btn_w, height=btn_h, radius=16, bg=SURFACE,
            fill=ACCENT, hover=ACCENT_HOVER, press=ACCENT_PRESS,
            font=self.f_btn, icon="bolt",
        )
        btn_wrap.create_window(bw_total / 2, bh_total / 2, window=self.btn)

        # Footer de features — reemplaza la unica linea gris por 3 items con icono
        feat_row = tk.Frame(form, bg=SURFACE)
        feat_row.pack(pady=(22, 0))
        features = [
            ("shield",       "Análisis 100% local"),
            ("eye-off",      "Sin telemetría de\nterceros"),
            ("shield-check", "Resultado solo\nvisible al staff"),
        ]
        for icon, txt in features:
            item = tk.Frame(feat_row, bg=SURFACE)
            item.pack(side="left", padx=12)
            make_icon(item, icon, size=15, color=TXT_SECONDARY, bg=SURFACE).pack(pady=(0, 4))
            tk.Label(item, text=txt, font=self.f_feat, fg=TXT_MUTED, bg=SURFACE,
                     justify="center").pack()

        # Bottom bar
        bot = tk.Frame(right, bg="#0a0a0a", height=30)
        bot.pack(side="bottom", fill="x"); bot.pack_propagate(False)
        tk.Label(bot, text=f"FiveM · {TOTAL_MODULES} módulos forenses · v{APP_VERSION}",
                 font=tkfont.Font(family="Segoe UI", size=8),
                 fg=TXT_FAINT, bg="#0a0a0a").pack(side="left", padx=14, pady=7)
        tk.Label(bot, text="titanxanticheat.xyz",
                 font=tkfont.Font(family="Segoe UI", size=8),
                 fg=TXT_FAINT, bg="#0a0a0a").pack(side="right", padx=14, pady=7)

    # ─── Scan screen ─────────────────────────────────────────────────────
    def _build_scan(self):
        self.scan_frame = tk.Frame(self.root, bg=BG)
        self.scan_frame.place(x=0, y=0, width=WIN_W, height=WIN_H)

        tk.Frame(self.scan_frame, bg=ACCENT, height=2).pack(fill="x")

        bar = tk.Frame(self.scan_frame, bg="#0a0a0a", height=48)
        bar.pack(fill="x"); bar.pack_propagate(False)
        tk.Label(bar, text="TITAN X",
                 font=tkfont.Font(family="Segoe UI", size=13, weight="bold"),
                 fg=ACCENT, bg="#0a0a0a").pack(side="left", padx=22, pady=12)
        tk.Label(bar, text=f"v{APP_VERSION}",
                 font=tkfont.Font(family="Segoe UI", size=9),
                 fg=TXT_FAINT, bg="#0a0a0a").pack(side="left", pady=12)

        status_wrap = tk.Frame(bar, bg="#0a0a0a")
        status_wrap.pack(side="right", padx=22)
        self._status_dot = tk.Canvas(status_wrap, width=10, height=10, bg="#0a0a0a",
                                      highlightthickness=0, bd=0)
        self._status_dot.pack(side="left", padx=(0, 6))
        self._status_dot_id = self._status_dot.create_oval(1, 1, 9, 9, fill=GREEN, outline="")
        self.status_top = tk.Label(status_wrap, text="ESCANEANDO",
                                    font=tkfont.Font(family="Segoe UI", size=9, weight="bold"),
                                    fg=GREEN, bg="#0a0a0a")
        self.status_top.pack(side="left")

        content = tk.Frame(self.scan_frame, bg=BG)
        content.pack(fill="both", expand=True)

        # Left: BIG GIF centered
        left = tk.Frame(content, bg=BG, width=380)
        left.pack(side="left", fill="y"); left.pack_propagate(False)

        # Blob de luz ambiental, muy sutil, detras del ojo grande.
        ambient2_img = make_glow_image(420, 420, ACCENT, blur=55, alpha=80, shape="ellipse")
        self._glow_refs.append(ambient2_img)
        ambient2 = tk.Canvas(left, width=420, height=420, bg=BG, highlightthickness=0, bd=0)
        ambient2.create_image(210, 210, image=ambient2_img)
        ambient2.place(relx=0.5, rely=0.5, anchor="center")

        try:
            gif2 = GifLabel(left, _gif_path(), scale=1.0)
            gif2.place(relx=0.5, rely=0.5, anchor="center")
        except Exception:
            make_icon(left, "eye", size=140, color=ACCENT, bg=BG).place(relx=0.5, rely=0.5, anchor="center")

        tk.Frame(content, bg=LINE, width=1).pack(side="left", fill="y")

        # Right: progress + checklist de categorias
        right = tk.Frame(content, bg=SURFACE)
        right.pack(side="right", fill="both", expand=True)

        cats_col = tk.Frame(right, bg=SURFACE)
        cats_col.pack(side="right", fill="y", padx=(0, 26))

        prog_col = tk.Frame(right, bg=SURFACE)
        prog_col.pack(side="left", fill="both", expand=True)

        pa = tk.Frame(prog_col, bg=SURFACE)
        pa.place(relx=0.5, rely=0.5, anchor="center")

        self.module_counter_lbl = tk.Label(pa, text=f"0 / {TOTAL_MODULES} módulos",
                 font=tkfont.Font(family="Segoe UI", size=8, weight="bold"),
                 fg=TXT_FAINT, bg=SURFACE)
        self.module_counter_lbl.pack(pady=(0, 6))

        self.pct_lbl = tk.Label(pa, text="0%", font=self.f_pct, fg=ACCENT, bg=SURFACE)
        self.pct_lbl.pack()

        # Barra de progreso gruesa, con esquinas redondeadas + highlight sutil
        # + glow dinamico alrededor del relleno (se regenera en cada _upd).
        self._pb_w, self._pb_h = 360, 10
        self._pb_blur = 10
        self._pb_y0 = self._pb_blur + 3
        pb_canvas_h = self._pb_h + 2 * self._pb_y0
        pb_bg = tk.Canvas(pa, width=self._pb_w, height=pb_canvas_h, bg=SURFACE, highlightthickness=0, bd=0)
        pb_bg.pack(pady=(12, 6))
        self._pb_bg = pb_bg
        self._pb_glow_item = pb_bg.create_image(0, self._pb_y0 + self._pb_h / 2)
        pb_bg.itemconfigure(self._pb_glow_item, state="hidden")
        draw_round_rect(pb_bg, 0, self._pb_y0, self._pb_w, self._pb_y0 + self._pb_h,
                         self._pb_h / 2, fill=LINE, outline="")
        self.pb_fill = draw_round_rect(pb_bg, 0, self._pb_y0, 0, self._pb_y0 + self._pb_h,
                                        self._pb_h / 2, fill=ACCENT, outline="")
        self._pb_hl = pb_bg.create_line(3, self._pb_y0 + 2, 3, self._pb_y0 + 2,
                                         fill="#f87171", width=1, capstyle="round")
        pb_bg.itemconfigure(self._pb_hl, state="hidden")

        self.module_lbl = tk.Label(pa, text="Iniciando módulos…",
                                    font=self.f_module, fg=TXT_FAINT, bg=SURFACE,
                                    wraplength=340, justify="center")
        self.module_lbl.pack(pady=(2, 18))

        self.cat_lbl = tk.Label(pa, text="",
                 font=tkfont.Font(family="Segoe UI", size=8, weight="bold"),
                 fg=ACCENT2, bg=SURFACE)
        self.cat_lbl.pack(pady=(0, 14))

        warn_row = tk.Frame(pa, bg=SURFACE)
        warn_row.pack()
        make_icon(warn_row, "alert", size=16, color=TXT_PRIMARY, bg=SURFACE).pack(side="left", padx=(0, 6))
        tk.Label(warn_row, text="NO CIERRES ESTA VENTANA",
                 font=tkfont.Font(family="Segoe UI", size=10, weight="bold"),
                 fg=TXT_PRIMARY, bg=SURFACE).pack(side="left")

        tk.Label(pa, text="El análisis forense corre localmente. Solo el staff ve el resultado.",
                 font=self.f_status, fg=TXT_FAINT, bg=SURFACE).pack(pady=(5, 20))

        self.spinner_lbl = Spinner(pa, size=36, color=ACCENT, bg=SURFACE, width=3)
        self.spinner_lbl.pack()
        self.spinner_lbl.start()

        self.distract_lbl = tk.Label(pa, text="", font=self.f_module, fg=TXT_FAINT, bg=SURFACE,
                                      wraplength=340, justify="center")
        self.distract_lbl.pack(pady=(10, 0))
        self.eta_lbl = tk.Label(pa, text="", font=self.f_eta, fg=TXT_FAINT, bg=SURFACE)
        self.eta_lbl.pack(pady=(4, 0))

        # Checklist de categorias — se resalta la actual, tenue las completadas
        self._cat_defs = [
            ("Procesos",            ["proceso"]),
            ("Memoria",             ["memoria"]),
            ("Red",                 ["red", "conexion", "conexión", "network"]),
            ("Registro",            ["registro"]),
            ("Sistema de archivos", ["archivo", "disco", "usn"]),
            ("Historial",           ["historial", "prefetch", "powershell"]),
        ]
        self._cat_current = -1
        self._cat_rows = []

        cw, ch = 224, 246
        cats_canvas = tk.Canvas(cats_col, width=cw, height=ch, bg=SURFACE, highlightthickness=0, bd=0)
        cats_canvas.pack(pady=(0, 0))
        draw_round_rect(cats_canvas, 0, 0, cw - 1, ch - 1, 14, fill=CARD_BG, outline=LINE_SOFT, width=1)

        cats_inner = tk.Frame(cats_canvas, bg=CARD_BG)
        cats_canvas.create_window(cw / 2, ch / 2, window=cats_inner, width=cw - 8, height=ch - 8)

        tk.Label(cats_inner, text="CATEGORÍAS", font=self.f_label, fg=TXT_MUTED,
                 bg=CARD_BG).pack(anchor="w", padx=14, pady=(14, 10))
        for name, _kws in self._cat_defs:
            row = tk.Frame(cats_inner, bg=CARD_BG)
            row.pack(fill="x", padx=14, pady=5)
            dot = tk.Canvas(row, width=14, height=14, bg=CARD_BG, highlightthickness=0, bd=0)
            dot.pack(side="left", padx=(0, 8))
            dot.create_oval(3, 3, 11, 11, outline=LINE_SOFT, width=1.4)
            lbl = tk.Label(row, text=name, font=self.f_cat, fg=TXT_FAINT, bg=CARD_BG, anchor="w")
            lbl.pack(side="left", fill="x")
            self._cat_rows.append((dot, lbl))

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
        if self._spinner_i % 20 == 0:
            self.distract_lbl.config(text=self._msgs[self._mi % len(self._msgs)])
            self._mi += 1
        self._spinner_i += 1
        self._anim_job = self.root.after(180, self._animate_scan)

    def _paint_cat_row(self, i, state):
        dot, lbl = self._cat_rows[i]
        dot.delete("all")
        if state == "done":
            draw_icon(dot, "check", 7, 7, 12, TXT_MUTED, 1.5)
            lbl.config(fg=TXT_MUTED, font=self.f_cat)
        elif state == "current":
            draw_icon(dot, "dot", 7, 7, 10, ACCENT, 1.5)
            lbl.config(fg=ACCENT, font=self.f_cat_bold)
        else:
            dot.create_oval(3, 3, 11, 11, outline=LINE_SOFT, width=1.4)
            lbl.config(fg=TXT_FAINT, font=self.f_cat)

    def _match_category_index(self, raw):
        text = (raw or "").lower()
        for i, (_name, keywords) in enumerate(self._cat_defs):
            for kw in keywords:
                if kw in text:
                    return i
        return None

    def _advance_categories(self, idx):
        if idx is None or idx == self._cat_current:
            return
        self._cat_current = idx
        for i in range(len(self._cat_rows)):
            if i < idx:   self._paint_cat_row(i, "done")
            elif i == idx: self._paint_cat_row(i, "current")
            else:          self._paint_cat_row(i, "pending")

    # ─── Helpers ─────────────────────────────────────────────────────────
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
        self.status_lbl.config(text="Validando…", fg=TXT_MUTED)
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
        w = int(self._pb_w * max(0, min(1, pct / 100)))
        update_round_rect(self._pb_bg, self.pb_fill, 0, self._pb_y0, w, self._pb_y0 + self._pb_h,
                           self._pb_h / 2)
        if w > 6:
            self._pb_bg.coords(self._pb_hl, 3, self._pb_y0 + 2, w - 3, self._pb_y0 + 2)
            self._pb_bg.itemconfigure(self._pb_hl, state="normal")
            glow_w = min(self._pb_w, w) + 2 * self._pb_blur
            glow_h = self._pb_h + 2 * self._pb_blur
            self._pb_glow_ref = make_glow_image(glow_w, glow_h, ACCENT, blur=self._pb_blur,
                                                 alpha=140, radius=self._pb_h / 2)
            self._pb_bg.itemconfigure(self._pb_glow_item, image=self._pb_glow_ref, state="normal")
            self._pb_bg.coords(self._pb_glow_item, w / 2, self._pb_y0 + self._pb_h / 2)
        else:
            self._pb_bg.itemconfigure(self._pb_hl, state="hidden")
            self._pb_bg.itemconfigure(self._pb_glow_item, state="hidden")

        self.pct_lbl.config(text=f"{int(pct)}%")
        if label:
            self.module_lbl.config(text=label, fg=TXT_SECONDARY)
        if category:
            self.cat_lbl.config(text=f"[ {category.upper()} ]")
            self._advance_categories(self._match_category_index(category))
        if total:
            self.module_counter_lbl.config(text=f"{done} / {total} módulos", fg=TXT_MUTED)
        m, s = divmod(int(rem), 60)
        self.eta_lbl.config(text=f"Tiempo restante: {m}m {s:02d}s" if rem > 5 else "Finalizando…")

    def _done(self):
        if self._anim_job:
            self.root.after_cancel(self._anim_job); self._anim_job = None
        update_round_rect(self._pb_bg, self.pb_fill, 0, self._pb_y0, self._pb_w, self._pb_y0 + self._pb_h,
                           self._pb_h / 2)
        self._pb_bg.coords(self._pb_hl, 3, self._pb_y0 + 2, self._pb_w - 3, self._pb_y0 + 2)
        self._pb_bg.itemconfigure(self._pb_hl, state="normal")
        glow_w = self._pb_w + 2 * self._pb_blur
        glow_h = self._pb_h + 2 * self._pb_blur
        self._pb_glow_ref = make_glow_image(glow_w, glow_h, ACCENT, blur=self._pb_blur,
                                             alpha=140, radius=self._pb_h / 2)
        self._pb_bg.itemconfigure(self._pb_glow_item, image=self._pb_glow_ref, state="normal")
        self._pb_bg.coords(self._pb_glow_item, self._pb_w / 2, self._pb_y0 + self._pb_h / 2)
        self.pct_lbl.config(text="100%")
        self.spinner_lbl.show_check()
        self._status_dot.itemconfig(self._status_dot_id, fill=GREEN)
        self.status_top.config(text="COMPLETADO", fg=GREEN)
        self.module_lbl.config(text="Análisis forense completo.", fg=GREEN)
        self.cat_lbl.config(text="")
        self.module_counter_lbl.config(text="")
        self.eta_lbl.config(text="Podés cerrar esta ventana.")
        self.distract_lbl.config(text="")
        for i in range(len(self._cat_rows)):
            self._paint_cat_row(i, "done")
        self.root.protocol("WM_DELETE_WINDOW", self.root.destroy)

    def _fail(self, msg):
        if self._anim_job:
            self.root.after_cancel(self._anim_job); self._anim_job = None
        try: self.spinner_lbl.stop()
        except Exception: pass
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
