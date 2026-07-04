"""
TITAN X — Cliente Minecraft
Empaquetar:
    pyinstaller --onefile --noconsole --uac-admin --name TitanXClient_Minecraft ^
        --add-data "core;core" --add-data "config.py;." --add-data "client/eye.gif;." ^
        --paths . client/titanx_minecraft.py
"""
import sys, os, io, json, time, threading, math, random, urllib.request, urllib.error

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tkinter as tk
from tkinter import font as tkfont
from PIL import Image, ImageTk, ImageDraw, ImageFilter

GAME_MODE   = "Minecraft"
APP_VERSION = "2.8.1"
ACCENT    = "#22c55e"
ACCENT2   = "#4ade80"
BG        = "#060606"
SURFACE   = "#0d0d0d"
SURFACE2  = "#111111"
WIN_W, WIN_H = 1040, 660
VERCEL_URL  = "https://titanxanticheat.xyz"


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


# ─── Helpers visuales: rectángulos redondeados e iconografía vectorial ─────
def _round_pts(x1, y1, x2, y2, r):
    """Calcula los puntos de un rectángulo con esquinas redondeadas para create_polygon(smooth=True)."""
    r = max(0, min(r, (x2 - x1) / 2, (y2 - y1) / 2))
    return [
        x1 + r, y1,   x2 - r, y1,   x2, y1,
        x2, y1 + r,   x2, y2 - r,   x2, y2,
        x2 - r, y2,   x1 + r, y2,   x1, y2,
        x1, y2 - r,   x1, y1 + r,   x1, y1,
    ]


def round_rect(canvas, x1, y1, x2, y2, r=10, **kw):
    """Dibuja (y devuelve el id de) un rectángulo con esquinas redondeadas simuladas en un Canvas."""
    return canvas.create_polygon(_round_pts(x1, y1, x2, y2, r), smooth=True, **kw)


def hex_to_rgb(h):
    """Convierte un color hex '#22c55e' a una tupla RGB (34, 197, 94)."""
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def make_glow_image(width, height, color_hex, blur=18, alpha=150, radius=None, shape="rounded"):
    """Genera un halo de luz (glow/neón) difuminado como PhotoImage.

    tk.Canvas no soporta blur/box-shadow nativo, así que se dibuja una forma
    sólida semitransparente sobre un lienzo RGBA vacío y se le aplica un
    GaussianBlur de PIL. El resultado se pega en el Canvas con create_image
    ANTES (o sea, primero) de dibujar la forma nítida encima, para que quede
    en una capa más abajo simulando un halo suave.
    """
    rgb = hex_to_rgb(color_hex)
    img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    pad = blur
    if shape == "ellipse":
        draw.ellipse([pad, pad, width - pad, height - pad], fill=rgb + (alpha,))
    else:
        r = radius if radius is not None else max(6, (min(width, height) - 2 * pad) // 3)
        draw.rounded_rectangle([pad, pad, width - pad, height - pad], radius=r, fill=rgb + (alpha,))
    img = img.filter(ImageFilter.GaussianBlur(blur))
    return ImageTk.PhotoImage(img)


def lighten_hex(h, amt=0.25):
    """Aclara un color hex hacia blanco en la proporcion `amt` (0-1)."""
    r, g, b = hex_to_rgb(h)
    r = int(r + (255 - r) * amt); g = int(g + (255 - g) * amt); b = int(b + (255 - b) * amt)
    return f"#{r:02x}{g:02x}{b:02x}"


def make_gradient_image(width, height, color1_hex, color2_hex, radius=12, horizontal=False):
    """Rectangulo redondeado con relleno degrade vertical, como PhotoImage RGBA."""
    width, height = max(2, int(width)), max(2, int(height))
    rgb1, rgb2 = hex_to_rgb(color1_hex), hex_to_rgb(color2_hex)
    if horizontal:
        base = Image.new("RGB", (2, 1))
        base.putpixel((0, 0), rgb1); base.putpixel((1, 0), rgb2)
    else:
        base = Image.new("RGB", (1, 2))
        base.putpixel((0, 0), rgb1); base.putpixel((0, 1), rgb2)
    grad = base.resize((width, height), Image.BILINEAR).convert("RGBA")
    mask = Image.new("L", (width, height), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, width - 1, height - 1], radius=radius, fill=255)
    grad.putalpha(mask)
    return ImageTk.PhotoImage(grad)


def draw_bolt(canvas, cx, cy, size, color):
    """Rayo vectorial (reemplaza el emoji de rayo en el botón principal)."""
    s = size
    pts = [
        cx - 0.05 * s, cy - 0.55 * s,
        cx - 0.34 * s, cy + 0.08 * s,
        cx - 0.06 * s, cy + 0.08 * s,
        cx - 0.16 * s, cy + 0.55 * s,
        cx + 0.34 * s, cy - 0.14 * s,
        cx + 0.02 * s, cy - 0.14 * s,
    ]
    return canvas.create_polygon(pts, fill=color, outline="", smooth=False)


def draw_check(canvas, cx, cy, size, color, width=3):
    """Check vectorial (reemplaza el emoji de check)."""
    s = size / 2
    return canvas.create_line(cx - s, cy + 0.05 * s, cx - 0.12 * s, cy + s * 0.65, cx + s, cy - s * 0.7,
                               fill=color, width=width, capstyle="round", joinstyle="round")


def draw_warning(canvas, cx, cy, size, color, fg="#04170b"):
    """Triángulo de alerta con signo de exclamación (reemplaza el emoji de alerta)."""
    s = size / 2
    tri = canvas.create_polygon(cx, cy - s, cx + s * 0.95, cy + s * 0.8, cx - s * 0.95, cy + s * 0.8,
                                 fill=color, outline="", smooth=False, joinstyle="round")
    canvas.create_line(cx, cy - s * 0.12, cx, cy + s * 0.3, fill=fg, width=max(2, int(size * 0.13)), capstyle="round")
    r = max(1.3, size * 0.07)
    canvas.create_oval(cx - r, cy + s * 0.48, cx + r, cy + s * 0.48 + 2 * r, fill=fg, outline="")
    return tri


def draw_dot(canvas, cx, cy, r, color, outline=""):
    """Punto/indicador vectorial (reemplaza el carácter de círculo relleno)."""
    return canvas.create_oval(cx - r, cy - r, cx + r, cy + r, fill=color, outline=outline)


def draw_eye(canvas, cx, cy, w, color):
    """Ojo vectorial simple (fallback cuando el GIF no carga)."""
    h = w * 0.55
    canvas.create_oval(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2, outline=color, width=3)
    r = w * 0.13
    canvas.create_oval(cx - r, cy - r, cx + r, cy + r, fill=color, outline="")


def draw_shield(canvas, cx, cy, size, color):
    """Ícono de escudo (feature: análisis 100% local)."""
    s = size / 2
    pts = [cx, cy - s, cx + s * 0.85, cy - s * 0.55, cx + s * 0.85, cy + s * 0.05,
           cx, cy + s, cx - s * 0.85, cy + s * 0.05, cx - s * 0.85, cy - s * 0.55]
    canvas.create_polygon(pts, fill="", outline=color, width=1.6, smooth=True, joinstyle="round")
    draw_check(canvas, cx, cy + 0.02 * s, size * 0.5, color, width=2)


def draw_no_signal(canvas, cx, cy, size, color):
    """Ícono de círculo tachado (feature: sin telemetría de terceros)."""
    s = size / 2
    canvas.create_oval(cx - s, cy - s, cx + s, cy + s, outline=color, width=1.6)
    canvas.create_line(cx - s * 0.62, cy - s * 0.62, cx + s * 0.62, cy + s * 0.62, fill=color, width=1.6)


def draw_lock(canvas, cx, cy, size, color):
    """Ícono de candado (feature: resultado solo visible al staff)."""
    s = size / 2
    canvas.create_arc(cx - s * 0.5, cy - s * 0.95, cx + s * 0.5, cy + s * 0.05, start=0, extent=180,
                       style=tk.ARC, outline=color, width=1.6)
    canvas.create_rectangle(cx - s * 0.72, cy - s * 0.1, cx + s * 0.72, cy + s * 0.85, outline=color, width=1.6)


def draw_arrow_up(canvas, cx, cy, size, color):
    """Flecha hacia arriba (banner de actualización disponible)."""
    s = size / 2
    pts = [cx, cy - s, cx + s * 0.7, cy + s * 0.15, cx + s * 0.28, cy + s * 0.15, cx + s * 0.28, cy + s,
           cx - s * 0.28, cy + s, cx - s * 0.28, cy + s * 0.15, cx - s * 0.7, cy + s * 0.15]
    canvas.create_polygon(pts, fill=color, outline="")


class RoundButton(tk.Canvas):
    """Botón con esquinas redondeadas, hover real e ícono vectorial (reemplaza tk.Button)."""
    def __init__(self, parent, text, command=None, width=300, height=56, bg=SURFACE,
                 fill=ACCENT, hover_fill=None, disabled_fill="#15291d",
                 fg="#ffffff", disabled_fg="#4d6b57", font=None, icon_fn=None):
        super().__init__(parent, width=width, height=height, bg=bg,
                          highlightthickness=0, cursor="hand2")
        self._command = command
        self._fill = fill
        self._hover_fill = hover_fill or fill
        self._disabled_fill = disabled_fill
        self._fg = fg
        self._disabled_fg = disabled_fg
        self._state = "normal"
        font = font or tkfont.Font(family="Segoe UI", size=12, weight="bold")
        r = height / 2

        # Relleno degrade (mas claro arriba, color base abajo) por estado —
        # se guardan referencias persistentes para que el garbage collector
        # no se lleve los PhotoImage.
        self._grad_normal = make_gradient_image(width, height, lighten_hex(fill, 0.24), fill, r)
        self._grad_hover = make_gradient_image(width, height, lighten_hex(self._hover_fill, 0.24),
                                                self._hover_fill, r)
        self._grad_disabled = make_gradient_image(width, height, disabled_fill, disabled_fill, r)
        self._img_refs = (self._grad_normal, self._grad_hover, self._grad_disabled)

        cx = width / 2
        self._rect = self.create_image(width / 2, height / 2, image=self._grad_normal)
        if icon_fn:
            icon_fn(self, cx - 82, height / 2, 16, fg)
            tx = cx + 12
        else:
            tx = cx
        self._label = self.create_text(tx, height / 2, text=text, fill=fg, font=font)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)

    def _on_enter(self, _e=None):
        if self._state == "normal":
            self.itemconfig(self._rect, image=self._grad_hover)

    def _on_leave(self, _e=None):
        if self._state == "normal":
            self.itemconfig(self._rect, image=self._grad_normal)

    def _on_click(self, _e=None):
        if self._state == "normal" and self._command:
            self._command()

    def config(self, **kwargs):
        if "state" in kwargs:
            state = kwargs.pop("state")
            self._state = state
            if state == "disabled":
                self.itemconfig(self._rect, image=self._grad_disabled)
                self.itemconfig(self._label, fill=self._disabled_fg)
                super().config(cursor="arrow")
            else:
                self.itemconfig(self._rect, image=self._grad_normal)
                self.itemconfig(self._label, fill=self._fg)
                super().config(cursor="hand2")
        if kwargs:
            super().config(**kwargs)
    configure = config


class ArcSpinner(tk.Canvas):
    """Spinner de arco animado dibujado en Canvas (reemplaza el carácter unicode rotando)."""
    def __init__(self, parent, size=46, color=ACCENT, track="#1c1c1c", width=3, bg=SURFACE2, **kw):
        super().__init__(parent, width=size, height=size, bg=bg, highlightthickness=0, **kw)
        self._size = size
        self._color = color
        self._track = track
        self._lw = width
        self._angle = 0
        self._job = None
        pad = width
        self.create_oval(pad, pad, size - pad, size - pad, outline=track, width=width)
        self._arc = self.create_arc(pad, pad, size - pad, size - pad, start=0, extent=100,
                                     style=tk.ARC, outline=color, width=width)

    def start(self):
        self.stop()
        self._spin()

    def _spin(self):
        self._angle = (self._angle - 9) % 360
        self.itemconfig(self._arc, start=self._angle)
        self._job = self.after(35, self._spin)

    def stop(self):
        if self._job:
            self.after_cancel(self._job)
            self._job = None

    def set_done(self):
        self.stop()
        self.delete("all")
        pad = self._lw
        size = self._size
        self.create_oval(pad, pad, size - pad, size - pad, outline=self._color, width=self._lw)
        draw_check(self, size / 2, size / 2, size * 0.42, self._color, width=3)


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


class TitanXMinecraftApp:
    def __init__(self, root):
        self.root    = root
        self.running = False
        self.eta_total = 0
        self.t0 = None
        self._anim_job = None
        self._spinner_i = 0
        self._glow_refs = []  # referencias persistentes a PhotoImage de glow (evita que el GC las borre)

        root.title("TITAN X — Minecraft")
        root.configure(bg=BG)
        root.geometry(f"{WIN_W}x{WIN_H}")
        root.resizable(False, False)
        try: root.iconbitmap(default="")
        except: pass

        self.f_title    = tkfont.Font(family="Segoe UI", size=32, weight="bold")
        self.f_sub      = tkfont.Font(family="Segoe UI", size=10)
        self.f_label    = tkfont.Font(family="Segoe UI", size=8, weight="bold")
        self.f_code     = tkfont.Font(family="Consolas", size=28, weight="bold")
        self.f_btn      = tkfont.Font(family="Segoe UI", size=12, weight="bold")
        self.f_status   = tkfont.Font(family="Segoe UI", size=9)
        self.f_pct      = tkfont.Font(family="Segoe UI", size=40, weight="bold")
        self.f_eta      = tkfont.Font(family="Segoe UI", size=9)
        self.f_module   = tkfont.Font(family="Segoe UI", size=9)
        self.f_badge    = tkfont.Font(family="Segoe UI", size=8, weight="bold")
        self.f_feat     = tkfont.Font(family="Segoe UI", size=7)
        self.f_stat_val = tkfont.Font(family="Segoe UI", size=12, weight="bold")
        self.f_stat_lbl = tkfont.Font(family="Segoe UI", size=7, weight="bold")

        self._build_idle()
        root.protocol("WM_DELETE_WINDOW", self._on_close)
        threading.Thread(target=self._check_update, daemon=True).start()

    # ─── Auto-update check ──────────────────────────────────────────
    def _check_update(self):
        try:
            req = urllib.request.Request(
                f"{VERCEL_URL}/version.json",
                headers={"User-Agent": "TitanXClient/2.5.0"}
            )
            with urllib.request.urlopen(req, timeout=5) as r:
                data = json.loads(r.read())
            latest = data.get("minecraft", APP_VERSION)
            if latest != APP_VERSION:
                self.root.after(0, lambda v=latest: self._show_update_banner(v))
        except Exception:
            pass

    def _show_update_banner(self, new_version):
        banner = tk.Frame(self.idle_frame, bg="#071a0a",
                          highlightthickness=1, highlightbackground=ACCENT)
        banner.place(relx=0, rely=0, relwidth=1, height=48)

        left_wrap = tk.Frame(banner, bg="#071a0a")
        left_wrap.pack(side="left", padx=16, pady=8)
        ic = tk.Canvas(left_wrap, width=18, height=18, bg="#071a0a", highlightthickness=0)
        ic.pack(side="left", padx=(0, 8))
        draw_arrow_up(ic, 9, 9, 14, "#86efac")
        tk.Label(left_wrap, text=f"Nueva versión disponible: v{new_version}",
                 font=tkfont.Font(family="Segoe UI", size=10, weight="bold"),
                 fg="#86efac", bg="#071a0a").pack(side="left")

        def _open_dl():
            import webbrowser
            webbrowser.open(f"{VERCEL_URL}/downloads/TitanXClient_Minecraft.exe")

        dl_btn = RoundButton(banner, text="Descargar actualización", command=_open_dl,
                              width=194, height=32, bg="#071a0a", fill=ACCENT,
                              hover_fill="#16a34a", fg="#04170b",
                              font=tkfont.Font(family="Segoe UI", size=9, weight="bold"))
        dl_btn.pack(side="right", padx=16, pady=8)

    # ─── Pantalla idle ───────────────────────────────────────────────
    def _build_idle(self):
        self.idle_frame = tk.Frame(self.root, bg=BG)
        self.idle_frame.place(x=0, y=0, width=WIN_W, height=WIN_H)
        tk.Frame(self.idle_frame, bg=ACCENT, height=2).pack(side="top", fill="x")

        left = tk.Frame(self.idle_frame, bg=BG, width=WIN_W // 2)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)

        # Blob de luz ambiental, muy difuminado, detrás de todo el panel izquierdo
        # (da atmósfera sutil sin saturar; queda oculto donde 'inner' es opaco).
        ambient = tk.Canvas(left, width=WIN_W // 2, height=WIN_H, bg=BG, highlightthickness=0)
        ambient.place(x=0, y=0)
        self._ambient_glow_img = make_glow_image(440, 420, ACCENT, blur=70, alpha=140, shape="ellipse")
        self._glow_refs.append(self._ambient_glow_img)
        ambient.create_image((WIN_W // 2) // 2, int(WIN_H * 0.42), image=self._ambient_glow_img)

        inner = tk.Frame(left, bg=BG)
        inner.place(relx=0.5, rely=0.5, anchor="center")

        badge_pad = 14
        badge_w, badge_h = 176, 30
        bcw, bch = badge_w + 2 * badge_pad, badge_h + 2 * badge_pad
        badge = tk.Canvas(inner, width=bcw, height=bch, bg=BG, highlightthickness=0)
        badge.pack(pady=(0, 18))
        self._badge_glow_img = make_glow_image(bcw, bch, ACCENT, blur=16, alpha=210, radius=14)
        self._glow_refs.append(self._badge_glow_img)
        badge.create_image(bcw / 2, bch / 2, image=self._badge_glow_img)
        bx, by = badge_pad, badge_pad
        self._badge_pill_img = make_gradient_image(badge_w, badge_h, "#16a34a", lighten_hex(ACCENT, 0.15),
                                                     radius=14, horizontal=True)
        self._glow_refs.append(self._badge_pill_img)
        badge.create_image(bx + badge_w / 2, by + badge_h / 2, image=self._badge_pill_img)
        draw_dot(badge, bx + 18, by + badge_h / 2, 3, "#ffffff")
        badge.create_text(bx + badge_w / 2 + 9, by + badge_h / 2, text=f"TITAN X · v{APP_VERSION}",
                           font=self.f_badge, fill="#ffffff")

        try:
            self.eye = GifLabel(inner, _gif_path(), scale=1.0)
            self.eye.pack(pady=(0, 16))
        except Exception:
            fb = tk.Canvas(inner, width=150, height=90, bg=BG, highlightthickness=0)
            fb.pack(pady=(0, 16))
            draw_eye(fb, 75, 45, 92, ACCENT)

        title_txt = "TITAN X"
        title_w = self.f_title.measure(title_txt) + 90
        title_h = self.f_title.metrics("linespace") + 50
        title_wrap = tk.Canvas(inner, width=title_w, height=title_h, bg=BG, highlightthickness=0)
        title_wrap.pack()
        self._title_glow_img = make_glow_image(title_w, title_h, ACCENT, blur=26, alpha=200, shape="ellipse")
        self._glow_refs.append(self._title_glow_img)
        title_wrap.create_image(title_w / 2, title_h / 2, image=self._title_glow_img)
        title_wrap.create_text(title_w / 2, title_h / 2, text=title_txt, font=self.f_title, fill="#ffffff")

        tk.Label(inner, text="Verificación forense — Minecraft",
                 font=self.f_sub, fg="#3a3a3a", bg=BG).pack(pady=(5, 0))

        stats_row = tk.Frame(inner, bg=BG)
        stats_row.pack(pady=(22, 0))
        stat_w, stat_h = 112, 66
        stat_pad = 12
        scw, sch = stat_w + 2 * stat_pad, stat_h + 2 * stat_pad
        for label, val in [("MÓDULOS", "201"), ("JUEGO", "Minecraft"), ("MODO", "Forense")]:
            c = tk.Canvas(stats_row, width=scw, height=sch, bg=BG, highlightthickness=0)
            c.pack(side="left", padx=5)
            # Glow sutil detrás del borde superior de acento: se dibuja PRIMERO
            # (capa de abajo) y la tarjeta nítida encima lo tapa casi entero,
            # dejando asomar solo un halo suave por arriba del borde.
            glow_img = make_glow_image(stat_w - 8, 26, ACCENT, blur=13, alpha=200, radius=6)
            self._glow_refs.append(glow_img)
            c.create_image(scw / 2, stat_pad + 2, image=glow_img)
            ox, oy = stat_pad, stat_pad
            round_rect(c, ox + 1, oy + 1, ox + stat_w - 1, oy + stat_h - 1, r=11,
                       fill=SURFACE2, outline="#1e1e1e", width=1)
            round_rect(c, ox + 16, oy + 7, ox + stat_w - 16, oy + 10, r=1.5, fill=ACCENT, outline="")
            c.create_text(ox + stat_w / 2, oy + stat_h / 2 + 6, text=val, font=self.f_stat_val, fill="#ffffff")
            c.create_text(ox + stat_w / 2, oy + stat_h - 13, text=label, font=self.f_stat_lbl, fill="#5a5a5a")

        right = tk.Frame(self.idle_frame, bg=SURFACE)
        right.pack(side="right", fill="both", expand=True)
        tk.Frame(right, bg="#1a1a1a", height=1).pack(fill="x")
        form = tk.Frame(right, bg=SURFACE)
        form.place(relx=0.5, rely=0.46, anchor="center")

        tk.Label(form, text="CÓDIGO DE ESCANEO SS", font=self.f_label, fg="#4a4a4a",
                 bg=SURFACE).pack(anchor="w", pady=(0, 10))

        ef_pad = 16
        ef_w, ef_h = 220, 78
        ecw, ech = ef_w + 2 * ef_pad, ef_h + 2 * ef_pad
        self._ef_canvas = tk.Canvas(form, width=ecw, height=ech, bg=SURFACE, highlightthickness=0)
        self._ef_canvas.pack(pady=(0, 12))
        # Glow del input: se crea oculto y se muestra/oculta al ganar/perder foco.
        self._ef_glow_img = make_glow_image(ecw, ech, ACCENT, blur=18, alpha=210, radius=20)
        self._glow_refs.append(self._ef_glow_img)
        self._ef_glow_id = self._ef_canvas.create_image(ecw / 2, ech / 2, image=self._ef_glow_img,
                                                          state="hidden")
        ex, ey = ef_pad, ef_pad
        self._ef_bg = round_rect(self._ef_canvas, ex + 1, ey + 1, ex + ef_w - 1, ey + ef_h - 1, r=16,
                                  fill="#0a0a0a", outline="#1e1e1e", width=2)
        self.code_var = tk.StringVar()
        self.entry = tk.Entry(self._ef_canvas, textvariable=self.code_var, font=self.f_code,
                               justify="center", width=7, bg="#0a0a0a", fg="#fff",
                               insertbackground=ACCENT, relief="flat", bd=0, highlightthickness=0)
        self._ef_canvas.create_window(ex + ef_w / 2, ey + ef_h / 2, window=self.entry)
        self.entry.bind("<KeyRelease>", self._fmt)
        self.entry.bind("<Return>", lambda e: self._start())
        self.entry.bind("<FocusIn>",  self._entry_focus_in)
        self.entry.bind("<FocusOut>", self._entry_focus_out)

        self.status_lbl = tk.Label(form, text="Ingresá el código que te dio el staff",
                                    font=self.f_status, fg="#3a3a3a", bg=SURFACE)
        self.status_lbl.pack(pady=(0, 20))

        btn_pad = 20
        btn_w, btn_h = 300, 56
        bwcw, bwch = btn_w + 2 * btn_pad, btn_h + 2 * btn_pad
        btn_wrap = tk.Frame(form, bg=SURFACE, width=bwcw, height=bwch)
        btn_wrap.pack()
        btn_wrap.pack_propagate(False)
        btn_glow_c = tk.Canvas(btn_wrap, width=bwcw, height=bwch, bg=SURFACE, highlightthickness=0)
        btn_glow_c.place(x=0, y=0)
        self._btn_glow_img = make_glow_image(bwcw, bwch, ACCENT, blur=28, alpha=220, radius=btn_h // 2)
        self._glow_refs.append(self._btn_glow_img)
        btn_glow_c.create_image(bwcw / 2, bwch / 2, image=self._btn_glow_img)

        self.btn = RoundButton(btn_wrap, text="INICIAR VERIFICACIÓN", command=self._start,
                                width=btn_w, height=btn_h, bg=SURFACE, fill=ACCENT,
                                hover_fill="#16a34a", fg="#ffffff",
                                disabled_fill="#15291d", disabled_fg="#4d6b57",
                                font=self.f_btn, icon_fn=draw_bolt)
        self.btn.place(x=btn_pad, y=btn_pad)

        feats_row = tk.Frame(form, bg=SURFACE)
        feats_row.pack(pady=(22, 0))
        feat_icon_color = "#454545"
        feats = [
            (draw_shield,    "Análisis 100% local"),
            (draw_no_signal, "Sin telemetría de terceros"),
            (draw_lock,      "Resultado solo visible al staff"),
        ]
        for icon_fn, text in feats:
            item = tk.Frame(feats_row, bg=SURFACE)
            item.pack(side="left", padx=12)
            ic = tk.Canvas(item, width=24, height=24, bg=SURFACE, highlightthickness=0)
            ic.pack()
            icon_fn(ic, 12, 12, 15, feat_icon_color)
            tk.Label(item, text=text, font=self.f_feat, fg="#3a3a3a", bg=SURFACE,
                     wraplength=88, justify="center").pack(pady=(6, 0))

        bot = tk.Frame(right, bg="#0a0a0a", height=32)
        bot.pack(side="bottom", fill="x"); bot.pack_propagate(False)
        tk.Label(bot, text=f"Minecraft · 201 módulos forenses · v{APP_VERSION}",
                 font=tkfont.Font(family="Segoe UI", size=8),
                 fg="#242424", bg="#0a0a0a").pack(side="left", padx=14, pady=8)
        tk.Label(bot, text="titanxanticheat.xyz",
                 font=tkfont.Font(family="Segoe UI", size=8),
                 fg="#242424", bg="#0a0a0a").pack(side="right", padx=14, pady=8)

    # ─── Pantalla de escaneo ─────────────────────────────────────────
    def _build_scan(self):
        self.scan_frame = tk.Frame(self.root, bg=BG)
        self.scan_frame.place(x=0, y=0, width=WIN_W, height=WIN_H)
        tk.Frame(self.scan_frame, bg=ACCENT, height=2).pack(fill="x")

        bar = tk.Frame(self.scan_frame, bg=SURFACE, height=56)
        bar.pack(fill="x"); bar.pack_propagate(False)
        tk.Label(bar, text="TITAN X — Minecraft",
                 font=tkfont.Font(family="Segoe UI", size=13, weight="bold"),
                 fg=ACCENT, bg=SURFACE).pack(side="left", padx=24, pady=14)

        status_wrap = tk.Frame(bar, bg=SURFACE)
        status_wrap.pack(side="right", padx=24)
        self._status_dot = tk.Canvas(status_wrap, width=10, height=10, bg=SURFACE, highlightthickness=0)
        self._status_dot.pack(side="left", padx=(0, 7))
        draw_dot(self._status_dot, 5, 5, 4, ACCENT)
        self.status_top = tk.Label(status_wrap, text="ESCANEANDO",
                                    font=tkfont.Font(family="Segoe UI", size=9, weight="bold"),
                                    fg=ACCENT, bg=SURFACE)
        self.status_top.pack(side="left")
        tk.Frame(self.scan_frame, bg="#1a1a1a", height=1).pack(fill="x")

        content = tk.Frame(self.scan_frame, bg=BG)
        content.pack(fill="both", expand=True)

        left = tk.Frame(content, bg=BG, width=300)
        left.pack(side="left", fill="y"); left.pack_propagate(False)
        try:
            gif2 = GifLabel(left, _gif_path(), scale=0.85)
            gif2.place(relx=0.5, rely=0.5, anchor="center")
        except Exception:
            pass

        # ── Panel derecho: checklist de cobertura ──
        catbox = tk.Frame(content, bg=SURFACE2, width=232)
        catbox.pack(side="right", fill="y"); catbox.pack_propagate(False)
        tk.Frame(catbox, bg="#1c1c1c", width=1).place(x=0, y=0, relheight=1)
        cat_inner = tk.Frame(catbox, bg=SURFACE2)
        cat_inner.pack(fill="both", expand=True, padx=20, pady=28)
        tk.Label(cat_inner, text="COBERTURA DEL ANÁLISIS", font=self.f_label,
                 fg="#3a3a3a", bg=SURFACE2).pack(anchor="w", pady=(0, 16))

        self._cat_names = [
            "Procesos y clientes", "Java / JVM", "Mods y launchers", "Memoria",
            "Registro de Windows", "Sistema de archivos", "Red y firewall", "Historial y prefetch",
        ]
        self._cat_keywords = [
            ["proceso", "process", "cliente", "wurst", "meteor", "liquidbounce"],
            ["java", "jvm", "agent", "dll"],
            ["mod", "launcher", "jar", "lunar", "badlion", "forge"],
            ["memoria", "memory"],
            ["registro", "registry", "mutex"],
            ["archivo", "file", "disco", "carpeta"],
            ["red", "network", "firewall", "host"],
            ["historial", "history", "prefetch", "powershell"],
        ]
        self._cat_font = tkfont.Font(family="Segoe UI", size=9)
        self._cat_font_bold = tkfont.Font(family="Segoe UI", size=9, weight="bold")
        self._cat_rows = []
        for name in self._cat_names:
            row = tk.Frame(cat_inner, bg=SURFACE2)
            row.pack(fill="x", pady=5)
            dot_c = tk.Canvas(row, width=16, height=16, bg=SURFACE2, highlightthickness=0)
            dot_c.pack(side="left", padx=(0, 10))
            lbl = tk.Label(row, text=name, font=self._cat_font, fg="#3a3a3a", bg=SURFACE2, anchor="w")
            lbl.pack(side="left", fill="x")
            self._cat_rows.append((dot_c, lbl))
        self._cat_idx = 0
        self._render_categories()

        # ── Centro: tarjeta de progreso ──
        right = tk.Frame(content, bg=SURFACE)
        right.pack(side="left", fill="both", expand=True)

        card_w, card_h = 460, 372
        card_c = tk.Canvas(right, width=card_w, height=card_h, bg=SURFACE, highlightthickness=0)
        card_c.place(relx=0.5, rely=0.5, anchor="center")
        round_rect(card_c, 1, 1, card_w - 1, card_h - 1, r=18, fill=SURFACE2, outline="#1c1c1c", width=1)
        round_rect(card_c, card_w / 2 - 26, 5, card_w / 2 + 26, 8, r=1.5, fill=ACCENT, outline="")

        pa = tk.Frame(card_c, bg=SURFACE2)
        card_c.create_window(card_w / 2, card_h / 2, window=pa)

        self.module_counter_lbl = tk.Label(pa, text="0 / 201 módulos",
                 font=tkfont.Font(family="Segoe UI", size=8, weight="bold"), fg="#3a3a3a", bg=SURFACE2)
        self.module_counter_lbl.pack(pady=(4, 6))

        self.pct_lbl = tk.Label(pa, text="0%", font=self.f_pct, fg=ACCENT, bg=SURFACE2)
        self.pct_lbl.pack()

        PB_W, PB_H = 380, 10
        PB_PAD = 14
        pb_bg = tk.Canvas(pa, width=PB_W + 2 * PB_PAD, height=PB_H + 2 * PB_PAD, bg=SURFACE2,
                           highlightthickness=0)
        pb_bg.pack(pady=(14, 8))
        px0, py0 = PB_PAD, PB_PAD
        round_rect(pb_bg, px0, py0, px0 + PB_W, py0 + PB_H, r=PB_H / 2, fill="#161616", outline="")
        # Item de glow del relleno: se crea vacío y se actualiza/reposiciona en _update_pb_glow.
        self._pb_glow_id = pb_bg.create_image(px0, py0 + PB_H / 2, anchor="w")
        self._pb_glow_img = None
        self.pb_fill = round_rect(pb_bg, px0, py0, px0, py0 + PB_H, r=PB_H / 2, fill=ACCENT, outline="")
        self._pb_hi = pb_bg.create_line(px0 - 10, py0 + 2, px0 - 10, py0 + 2, fill=ACCENT2, width=2,
                                         capstyle="round")
        self._pb_bg = pb_bg
        self._pb_w, self._pb_h = PB_W, PB_H
        self._pb_x0, self._pb_y0 = px0, py0

        self.module_lbl = tk.Label(pa, text="Iniciando módulos…", font=self.f_module, fg="#4a4a4a",
                                    bg=SURFACE2, wraplength=360, justify="center")
        self.module_lbl.pack(pady=(2, 6))
        self.cat_lbl = tk.Label(pa, text="", font=tkfont.Font(family="Segoe UI", size=8, weight="bold"),
                 fg=ACCENT2, bg=SURFACE2)
        self.cat_lbl.pack(pady=(0, 16))

        warn_row = tk.Frame(pa, bg=SURFACE2)
        warn_row.pack()
        warn_ic = tk.Canvas(warn_row, width=18, height=18, bg=SURFACE2, highlightthickness=0)
        warn_ic.pack(side="left", padx=(0, 7))
        draw_warning(warn_ic, 9, 10, 15, ACCENT, fg="#04170b")
        tk.Label(warn_row, text="NO CIERRES ESTA VENTANA",
                 font=tkfont.Font(family="Segoe UI", size=10, weight="bold"), fg="#fff", bg=SURFACE2).pack(side="left")

        tk.Label(pa, text="El análisis forense corre localmente. Solo el staff ve el resultado.",
                 font=self.f_status, fg="#3a3a3a", bg=SURFACE2).pack(pady=(5, 18))

        self.spinner_lbl = ArcSpinner(pa, size=42, color=ACCENT, track="#1c1c1c", width=3, bg=SURFACE2)
        self.spinner_lbl.pack()
        self.spinner_lbl.start()

        self.distract_lbl = tk.Label(pa, text="", font=self.f_module, fg="#3a3a3a",
                                      bg=SURFACE2, wraplength=360, justify="center")
        self.distract_lbl.pack(pady=(8, 0))
        self.eta_lbl = tk.Label(pa, text="", font=self.f_eta, fg="#2a2a2a", bg=SURFACE2)
        self.eta_lbl.pack(pady=(4, 0))

        self._msgs = [
            "Analizando mods y plugins instalados…",
            "Revisando carpetas de launchers (Lunar, Badlion, Forge)…",
            "Verificando procesos Java activos…",
            "Escaneando launcher_profiles.json…",
            "Revisando historial de prefetch del sistema…",
            "Analizando DLLs cargadas en la JVM…",
            "Buscando javaagents sospechosos…",
            "Verificando clientes de modificación (Wurst, Meteor, LiquidBounce)…",
            "Analizando jars en carpeta .minecraft/mods…",
            "Escaneando historial de PowerShell…",
            "Revisando mutexes de clientes hack conocidos…",
            "Verificando reglas de firewall y archivo hosts…",
        ]
        self._mi = 0
        self._animate_scan()

    def _render_categories(self):
        for i, (dot_c, lbl) in enumerate(self._cat_rows):
            dot_c.delete("all")
            if i < self._cat_idx:
                draw_check(dot_c, 8, 8, 11, ACCENT2, width=2)
                lbl.config(fg="#52605a", font=self._cat_font)
            elif i == self._cat_idx:
                draw_dot(dot_c, 8, 8, 4, ACCENT)
                lbl.config(fg="#ffffff", font=self._cat_font_bold)
            else:
                draw_dot(dot_c, 8, 8, 3, "#2a2a2a")
                lbl.config(fg="#3a3a3a", font=self._cat_font)

    def _update_categories(self, pct, category):
        n = len(self._cat_rows)
        idx = self._cat_idx
        if category:
            low = category.lower()
            for i, kws in enumerate(self._cat_keywords):
                if any(k in low for k in kws):
                    idx = max(idx, i)
                    break
        idx = max(idx, min(n - 1, int(pct / 100 * n)))
        if idx != self._cat_idx:
            self._cat_idx = idx
            self._render_categories()

    def _complete_categories(self):
        self._cat_idx = len(self._cat_rows)
        self._render_categories()

    def _animate_scan(self):
        self.distract_lbl.config(text=self._msgs[self._mi % len(self._msgs)])
        self._mi += 1
        self._anim_job = self.root.after(3500, self._animate_scan)

    def _fmt(self, _=None):
        raw = "".join(c for c in self.code_var.get().upper() if c.isalnum())[:6]
        fmt = raw if len(raw) <= 3 else f"{raw[:3]}-{raw[3:]}"
        if fmt != self.code_var.get():
            self.code_var.set(fmt); self.entry.icursor(tk.END)

    def _entry_focus_in(self, _e=None):
        self._ef_canvas.itemconfig(self._ef_bg, outline=ACCENT)
        self._ef_canvas.itemconfig(self._ef_glow_id, state="normal")

    def _entry_focus_out(self, _e=None):
        self._ef_canvas.itemconfig(self._ef_bg, outline="#1e1e1e")
        self._ef_canvas.itemconfig(self._ef_glow_id, state="hidden")

    def _on_close(self):
        if self.running: return
        self.root.destroy()

    def _start(self):
        if self.running: return
        code = self.code_var.get().strip().upper()
        if len(code) < 5:
            self.status_lbl.config(text="Ingresá el código completo (XXX-XXX).", fg=ACCENT); return
        self.status_lbl.config(text="Validando…", fg="#666")
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
        gm = claim.get("game_mode", GAME_MODE); deep = claim.get("deep", False)
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

    def _set_pb_width(self, w):
        w = max(0, min(self._pb_w, w))
        r = self._pb_h / 2
        x0, y0 = self._pb_x0, self._pb_y0
        self._pb_bg.coords(self.pb_fill, *_round_pts(x0, y0, x0 + w, y0 + self._pb_h, r))
        if w > 12:
            self._pb_bg.coords(self._pb_hi, x0 + 5, y0 + 2, x0 + w - 5, y0 + 2)
        else:
            self._pb_bg.coords(self._pb_hi, x0 - 10, y0 + 2, x0 - 10, y0 + 2)
        self._update_pb_glow(w)

    def _update_pb_glow(self, w):
        """Regenera el halo de glow detrás del relleno de la barra de progreso,
        siguiendo su ancho actual. Se guarda la referencia en self._pb_glow_img
        (pisando la anterior) para que el PhotoImage no sea recolectado por el GC
        mientras esté en pantalla."""
        if w < 6:
            self._pb_bg.itemconfig(self._pb_glow_id, image="")
            return
        blur = 12
        gw = int(w) + 2 * blur
        gh = self._pb_h + 2 * blur
        img = make_glow_image(gw, gh, ACCENT, blur=blur, alpha=140, radius=self._pb_h / 2)
        self._pb_glow_img = img
        self._pb_bg.coords(self._pb_glow_id, self._pb_x0 - blur, self._pb_y0 + self._pb_h / 2)
        self._pb_bg.itemconfig(self._pb_glow_id, image=img)

    def _upd(self, pct, rem, label="", category="", done=0, total=0):
        w = self._pb_w * max(0, min(1, pct / 100))
        self._set_pb_width(w)
        self.pct_lbl.config(text=f"{int(pct)}%")
        if label: self.module_lbl.config(text=label, fg="#5a5a5a")
        if category: self.cat_lbl.config(text=f"[ {category.upper()} ]")
        if total: self.module_counter_lbl.config(text=f"{done} / {total} módulos", fg="#4a4a4a")
        self._update_categories(pct, category)
        m, s = divmod(int(rem), 60)
        self.eta_lbl.config(text=f"Tiempo restante: {m}m {s:02d}s" if rem > 5 else "Finalizando…")

    def _done(self):
        if self._anim_job: self.root.after_cancel(self._anim_job)
        self._set_pb_width(self._pb_w)
        self.pct_lbl.config(text="100%")
        self.spinner_lbl.set_done()
        self._status_dot.delete("all")
        draw_dot(self._status_dot, 5, 5, 4, ACCENT)
        self.status_top.config(text="COMPLETADO")
        self.module_lbl.config(text="Análisis forense completo.", fg=ACCENT)
        self.cat_lbl.config(text="")
        self.module_counter_lbl.config(text="")
        self.eta_lbl.config(text="Podés cerrar esta ventana.")
        self._complete_categories()
        self.root.protocol("WM_DELETE_WINDOW", self.root.destroy)

    def _fail(self, msg):
        if self._anim_job: self.root.after_cancel(self._anim_job)
        self.running = False
        try: self.spinner_lbl.stop()
        except: pass
        try: self.scan_frame.place_forget()
        except: pass
        self.idle_frame.place(x=0, y=0, width=WIN_W, height=WIN_H)
        self.status_lbl.config(text=msg, fg=ACCENT)
        self.btn.config(state="normal")


if __name__ == "__main__":
    root = tk.Tk()
    TitanXMinecraftApp(root)
    root.mainloop()
