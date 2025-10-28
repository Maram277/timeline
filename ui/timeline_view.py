import re
import tkinter as tk
from tkinter import ttk, messagebox, Toplevel
from datetime import date
from pathlib import Path

# Pillow (behövs för JPG/WEBP)
try:
    from PIL import Image, ImageTk
    PIL_OK = True
except Exception:
    PIL_OK = False

# Paletter
PALETTE_CHAR = ["#3d9cd6", "#A7F3D0", "#CD5699", "#B76BE0", "#2047E6",
                "#A20909", "#5691D4", "#D8B4FE", "#FDBA74", "#86EFAC"]
PALETTE_LOC  = ["#334155", "#3f6212", "#155e75", "#7c2d12", "#da7adf",
                "#5e93dc", "#14532d", "#4572db", "#713f12", "#54d88b"]
_char_color_map: dict[str, str] = {}
_loc_color_map: dict[str, str] = {}

def color_for_character(name: str) -> str:
    if name not in _char_color_map:
        _char_color_map[name] = PALETTE_CHAR[len(_char_color_map) % len(PALETTE_CHAR)]
    return _char_color_map[name]

def color_for_location(name: str) -> str:
    if name not in _loc_color_map:
        _loc_color_map[name] = PALETTE_LOC[len(_loc_color_map) % len(PALETTE_LOC)]
    return _loc_color_map[name]

# date 
_MONTHS = {
    "jan":1,"januari":1,"feb":2,"februari":2,"mar":3,"mars":3,"march":3,
    "apr":4,"april":4,"maj":5,"may":5,"jun":6,"juni":6,"june":6,
    "jul":7,"juli":7,"july":7,"aug":8,"augusti":8,"august":8,
    "sep":9,"sept":9,"september":9,"okt":10,"oktober":10,"oct":10,"october":10,
    "nov":11,"november":11,"dec":12,"december":12,
}

def _parse_date_str(s: str) -> date | None:
    if not s: return None
    t = s.strip().lower()
    m = re.match(r"^\s*(\d{4})[\/\-. ](\d{1,2})[\/\-. ](\d{1,2})\s*$", t)
    if m:
        y, mo, d = map(int, m.groups())
        return date(y, max(1, min(mo, 12)), max(1, min(d, 31)))
    m = re.match(r"^\s*(\d{1,2})[\/\-. ](\d{1,2})(?:[\/\-. ](\d{2,4}))?\s*$", t)
    if m:
        d, mo, y = m.groups()
        d = int(d); mo = int(mo)
        if y is None: y = date.today().year
        else:
            y = int(y); y += 2000 if y < 50 else (1900 if y < 100 else 0)
        return date(y, max(1, min(mo, 12)), max(1, min(d, 31)))
    m = re.match(r"^\s*(\d{1,2})\s+([a-zåäö\.]+)\s*(\d{2,4})?\s*$", t)
    if m:
        d, mon_txt, y = m.groups()
        mon = _MONTHS.get(mon_txt.rstrip("."))
        if mon:
            d = int(d)
            if y is None: y = date.today().year
            else:
                y = int(y); y += 2000 if y < 50 else (1900 if y < 100 else 0)
            return date(y, mon, max(1, min(d, 31)))
    m = re.match(r"^\s*([a-zåäö\.]+)\s*(\d{2,4})?\s*$", t)
    if m:
        mon_txt, y = m.groups()
        mon = _MONTHS.get(mon_txt.rstrip("."))
        if mon:
            if y is None: y = date.today().year
            else:
                y = int(y); y += 2000 if y < 50 else (1900 if y < 100 else 0)
            return date(y, mon, 1)
    return None

def _format_date_dmy(d: date) -> str:
    return f"{d.day}/{d.month}/{d.year}"


class TimelineView(ttk.Frame):
    """Timeline med zoom/pan/drag, miniatyrer och detaljer med char+location-bilder."""
    def __init__(self, master, get_characters, get_locations, events_panel):
        super().__init__(master, padding=10)
        self.get_characters = get_characters
        self.get_locations  = get_locations 
        self.events_panel   = events_panel

        ttk.Label(self, text="Timeline (zoom, pan, drag; dbl-klick för detaljer)",
                  font=("TkDefaultFont", 11, "bold")).pack(anchor="w")
        self.canvas = tk.Canvas(self, bg="#fafafa", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, pady=(6, 0))

        # state
        self.scale = 1.0
        self._axis_dates: list[date] = []
        self._axis_start_x = 0.0
        self._axis_step = 100.0
        self._single_x = 0.0
        self._margin = 80

        self._legend_char_tags: dict[str, str] = {}
        self.highlight_names: set[str] = set()
        self._pan = 0.0
        self._pan_dragging = False
        self._pan_last_x = 0
        self._drag_ev_index: int | None = None
        self._drag_marker = None
        self._thumb_cache: dict[str, tk.PhotoImage] = {}

        # hover tooltip
        self._hover: Toplevel | None = None
        self._hover_img = None

        # binds
        self.canvas.bind("<Configure>",  lambda e: self.redraw())
        self.canvas.bind("<MouseWheel>", self.on_zoom)
        self.canvas.bind("<Button-4>",   self.on_zoom)   # linux
        self.canvas.bind("<Button-5>",   self.on_zoom)   # linux
        # pan
        self.canvas.bind("<Button-2>", self._pan_start)
        self.canvas.bind("<B2-Motion>", self._pan_drag)
        self.canvas.bind("<ButtonRelease-2>", self._pan_end)
        self.canvas.bind("<Button-3>", self._pan_start)
        self.canvas.bind("<B3-Motion>", self._pan_drag)
        self.canvas.bind("<ButtonRelease-3>", self._pan_end)
        # drag & detaljer
        self.canvas.tag_bind("event", "<Button-1>", self._drag_start)
        self.canvas.bind("<B1-Motion>", self._drag_motion)
        self.canvas.bind("<ButtonRelease-1>", self._drag_end)
        self.canvas.tag_bind("event", "<Double-Button-1>", self.on_canvas_event_details)
        self.canvas.bind("<Double-Button-1>", self._clear_highlight)
        # hover
        self.canvas.tag_bind("event", "<Enter>", self._event_hover_in)
        self.canvas.tag_bind("event", "<Leave>", self._event_hover_out)
        # legend
        self.canvas.tag_bind("legend_char", "<Button-1>", self.on_legend_char_click)

    def _get_thumb(self, path: str, max_wh=(40, 40)) -> tk.PhotoImage | None:
        p = (path or "").strip()
        if not p or not Path(p).exists():
            return None
        key = f"{Path(p).resolve()}|{max_wh[0]}x{max_wh[1]}"
        if key in self._thumb_cache:
            return self._thumb_cache[key]
        try:
            if PIL_OK:
                im = Image.open(p)
                im.thumbnail(max_wh)
                img = ImageTk.PhotoImage(im)
            else:
                img = tk.PhotoImage(file=p) 
            self._thumb_cache[key] = img
            return img
        except Exception:
            return None

    def _make_img(self, path: str, max_wh=(520, 520)) -> tk.PhotoImage | None:
        """Ladda bild för dialogens huvudbild."""
        p = (path or "").strip()
        if not p or not Path(p).exists():
            return None
        try:
            if PIL_OK:
                im = Image.open(p)
                im.thumbnail(max_wh)
                return ImageTk.PhotoImage(im)
            else:
                return tk.PhotoImage(file=p) 
        except Exception:
            return None

    def _char_image(self, name: str) -> str | None:
        for ci in self.get_characters():
            if ci.get("name", "") == name:
                p = (ci.get("image", "") or "").strip()
                return p if p else None
        return None

    def _loc_image(self, name: str) -> str | None:
        for li in self.get_locations():
            if li.get("name", "") == name:
                p = (li.get("image", "") or "").strip()
                return p if p else None
        return None

    # ---------- redraw ----------
    def redraw(self):
        c = self.canvas
        if not c.winfo_ismapped(): return
        c.delete("all")
        c._img_refs = []  
        w, h = c.winfo_width(), c.winfo_height()
        y = h // 2

        self._build_axis(w)

        # baslinje
        x0, x1 = self._margin, w - self._margin
        c.create_line(x0, y, x1, y, width=2, fill="#444")

        # ticks
        if len(self._axis_dates) == 1:
            d = self._axis_dates[0]
            c.create_line(self._single_x, y-8, self._single_x, y+8, fill="#777")
            c.create_text(self._single_x, y-24, text=_format_date_dmy(d),
                          font=("TkDefaultFont", 9, "bold"))
        else:
            for i, d in enumerate(self._axis_dates):
                xx = self._axis_start_x + i * self._axis_step
                c.create_line(xx, y-8, xx, y+8, fill="#777")
                c.create_text(xx, y-24, text=_format_date_dmy(d),
                              font=("TkDefaultFont", 9, "bold"))

        # events
        radius = int(12 * self.scale)
        per_day_counter: dict[date, int] = {}
        gap_y = max(8, int(6 * self.scale))

        for i, ev in enumerate(self.events_panel.filtered_data()):
            d = _parse_date_str(ev.get("date", ""))
            if not d: continue
            x = self._date_to_x(d)

            k = per_day_counter.get(d, 0)
            per_day_counter[d] = k + 1
            y0 = y + (k * (2 * radius + gap_y))

            chars = ev.get("characters") or []
            first_char = chars[0] if chars else ""
            loc = ev.get("location", "")

            # färger
            fill = color_for_character(first_char)
            outline = color_for_location(loc)
            tags = ("event", f"event_{i}")

            # highlight
            is_hit = (not self.highlight_names) or bool(self.highlight_names.intersection(chars))
            if not is_hit:
                fill = "#dddddd"; outline = "#cccccc"

            c.create_oval(x - radius, y0 - radius, x + radius, y0 + radius,
                fill=fill, outline=outline, width=3, tags=tags)

            txt_color = "#000" if is_hit else "#999"
            c.create_text(x, y0 - radius - 2, text=ev.get("title", ""),
                          fill=txt_color, font=("TkDefaultFont", 9), tags=tags)
            act = ev.get("activity", "")
            if act:
                c.create_text(x, y0 - radius + 12, text=act,
                              fill=txt_color, font=("TkDefaultFont", 8), tags=tags)

            # thumbnail: event -> char -> loc
            th = self._get_thumb(ev.get("image", ""))
            if th is None and first_char:
                th = self._get_thumb(self._char_image(first_char) or "")
            if th is None and loc:
                th = self._get_thumb(self._loc_image(loc) or "")
            if th is not None:
                c.create_image(x + radius + 10, y0, image=th, anchor="w", tags=tags)
                c._img_refs.append(th)

            # badges för karaktärer
            if chars:
                br = max(4, int(5 * self.scale)); gap = 2
                total = len(chars) * (2 * br) + (len(chars) - 1) * gap
                start = x - total / 2 + br
                badge_y = y0 + radius + 8
                for k2, nm in enumerate(chars):
                    bx = start + k2 * (2 * br + gap)
                    bfill = color_for_character(nm) if is_hit else "#e5e7eb"
                    c.create_oval(bx - br, badge_y - br, bx + br, badge_y + br,
                                  fill=bfill, outline="#222", width=1, tags=tags)

        self._draw_legend(c)

    # zoom
    def on_zoom(self, event):
        zin = False
        if hasattr(event, "delta") and event.delta: zin = event.delta > 0
        elif hasattr(event, "num"):                 zin = (event.num == 4)
        self.scale *= 1.1 if zin else 0.9
        self.scale = max(0.6, min(self.scale, 3.0))
        self.redraw()

    # axis 
    def _collect_unique_dates(self) -> list[date]:
        ds, seen = [], set()
        for ev in self.events_panel.filtered_data():
            d = _parse_date_str(ev.get("date", ""))
            if d and d not in seen:
                seen.add(d); ds.append(d)
        ds.sort()
        return ds

    def _build_axis(self, width: int):
        self._axis_dates = self._collect_unique_dates()
        usable = max(40, width - 2 * self._margin)
        n = len(self._axis_dates)
        if n <= 1:
            self._axis_start_x = self._margin + self._pan
            self._axis_step = 0.0
            self._single_x = width / 2 + self._pan
        else:
            self._axis_start_x = self._margin + self._pan
            self._axis_step = usable / (n - 1)
            self._single_x = 0.0

    def _date_to_x(self, d: date) -> float:
        if len(self._axis_dates) == 1:
            return self._single_x
        if d not in self._axis_dates:
            if not self._axis_dates: return self._axis_start_x
            idx = min(range(len(self._axis_dates)),
                      key=lambda i: abs((self._axis_dates[i] - d).days))
        else:
            idx = self._axis_dates.index(d)
        return self._axis_start_x + idx * self._axis_step

    def _x_to_nearest_date(self, x: float) -> date | None:
        if not self._axis_dates: return None
        if len(self._axis_dates) == 1: return self._axis_dates[0]
        idx = round((x - self._axis_start_x) / (self._axis_step if self._axis_step else 1))
        idx = max(0, min(idx, len(self._axis_dates) - 1))
        return self._axis_dates[idx]

    # legend
    def _draw_legend(self, c: tk.Canvas):
        chars = [ci.get("name", "") for ci in self.get_characters() if ci.get("name", "")]
        locs  = [li.get("name", "") for li in self.get_locations() if li.get("name", "")]

        if not chars and not locs:
            c.delete("legend"); c.delete("legend_bg"); return

        pad, x, y = 8, 12, 12
        line_h, r = 18, 6
        c.delete("legend"); c.delete("legend_bg")
        self._legend_char_tags.clear()

        if chars:
            c.create_text(x, y, anchor="nw", text="Characters",
                          font=("TkDefaultFont", 9, "bold"), tags=("legend",))
            y += line_h
            for idx, name in enumerate(chars):
                tag = f"legend_char_{idx}"
                self._legend_char_tags[tag] = name
                th = self._get_thumb(self._char_image(name) or "", max_wh=(22,22))
                if th:
                    c.create_image(x+11, y+9, image=th, tags=("legend","legend_char",tag))
                    c._img_refs.append(th)
                else:
                    clr = color_for_character(name)
                    c.create_oval(x, y, x+2*r, y+2*r, fill=clr, outline="#222",
                                  tags=("legend","legend_char",tag))
                c.create_text(x + 2*r + 6, y - 2, anchor="nw", text=name,
                              font=("TkDefaultFont", 9), tags=("legend","legend_char",tag))
                y += line_h

        if locs:
            y += 6 if chars else 0
            c.create_text(x, y, anchor="nw", text="Locations",
                          font=("TkDefaultFont", 9, "bold"), tags=("legend",))
            y += line_h
            for name in locs:
                clr = color_for_location(name)
                c.create_oval(x, y, x + 2*r, y + 2*r, fill="", outline=clr, width=2, tags=("legend",))
                c.create_text(x + 2*r + 6, y - 2, anchor="nw", text=name,
                              font=("TkDefaultFont", 9), tags=("legend",))
                y += line_h

        c.update_idletasks()
        bbox = c.bbox("legend")
        if bbox:
            x0, y0, x1, y1 = bbox
            bg = c.create_rectangle(x0 - pad, y0 - pad, x1 + pad, y1 + pad,
                                    fill="#fff", outline="#ddd", tags=("legend_bg",))
            c.tag_lower(bg, "legend")

    def on_legend_char_click(self, _event):
        cur = self.canvas.find_withtag("current")
        if not cur: return
        tags = self.canvas.gettags(cur[0])
        key = next((t for t in tags if t.startswith("legend_char_")), None)
        if not key: return
        name = self._legend_char_tags.get(key, "")
        if name in self.highlight_names: self.highlight_names.remove(name)
        else: self.highlight_names.add(name)
        self.redraw()

    def _clear_highlight(self, _e=None):
        if self.highlight_names:
            self.highlight_names.clear()
            self.redraw()

    # hover tooltip 
    def _event_hover_in(self, event):
        cur = self.canvas.find_withtag("current")
        if not cur: return
        tags = self.canvas.gettags(cur[0])
        fidx = next((int(t.split("_")[1]) for t in tags if t.startswith("event_")), None)
        if fidx is None: return
        ev = self.events_panel.filtered_data()[fidx]

        chars = ev.get("characters") or []
        loc = ev.get("location","")
        img_path = (ev.get("image","") or "").strip()
        if not img_path and chars:
            img_path = self._char_image(chars[0]) or ""
        if not img_path and loc:
            img_path = self._loc_image(loc) or ""

        if self._hover: self._hover.destroy()
        tip = Toplevel(self)
        tip.overrideredirect(True)
        tip.attributes("-topmost", True)
        x = self.winfo_rootx() + event.x + 16
        y = self.winfo_rooty() + event.y + 16
        tip.geometry(f"+{x}+{y}")

        frm = ttk.Frame(tip, padding=6, relief="solid")
        frm.pack(fill="both", expand=True)

        title = ev.get("Event",""); date_s = ev.get("date","")
        act = ev.get("activity","")
        info = f"{title}\n{date_s}" + (f"\n{act}" if act else "")
        ttk.Label(frm, text=info, font=("TkDefaultFont", 9, "bold")).grid(row=0, column=0, sticky="w")

        lbl = ttk.Label(frm); lbl.grid(row=0, column=1, sticky="w", padx=(8,0))
        self._hover_img = None
        if img_path and Path(img_path).exists():
            try:
                if PIL_OK:
                    im = Image.open(img_path); im.thumbnail((100,100))
                    self._hover_img = ImageTk.PhotoImage(im)
                else:
                    self._hover_img = tk.PhotoImage(file=img_path)
                lbl.configure(image=self._hover_img)
            except Exception:
                pass

        self._hover = tip

    def _event_hover_out(self, _e):
        if self._hover:
            self._hover.destroy()
            self._hover = None
            self._hover_img = None

    # detaljer: med char+location thumbnails
    def on_canvas_event_details(self, _event):
        cur = self.canvas.find_withtag("current")
        if not cur: return
        tags = self.canvas.gettags(cur[0])
        fidx = next((int(t.split("_")[1]) for t in tags if t.startswith("event_")), None)
        if fidx is None: return
        ev = self.events_panel.filtered_data()[fidx]

        chars = ev.get("characters", [])
        loc_name = ev.get("location", "")
        activity = ev.get("activity", "")

        def _cdesc(nm):
            for c in self.get_characters():
                if c.get("name","")==nm: return c.get("description","")
            return ""
        char_lines = [nm + (f"\n— {_cdesc(nm)}" if _cdesc(nm) else "") for nm in chars]
        lo_desc = next((l.get("description","") for l in self.get_locations()
                        if l.get("name","")==loc_name), "")
        text = (f"Event: {ev.get('Event','')}\n"
                f"Date: {ev.get('date','')}\n\n"
                f"Characters:\n" + ("\n\n".join(char_lines) if char_lines else "(none)") + "\n\n")
        if activity: text += f"Activity: {activity}\n\n"
        text += f"Location: {loc_name}\n— {lo_desc}"

        # huvudbild-kandidater
        main_candidates = []
        if ev.get("image"): main_candidates.append(ev.get("image"))
        if chars:
            ci = self._char_image(chars[0])
            if ci: main_candidates.append(ci)
        li = self._loc_image(loc_name)
        if li: main_candidates.append(li)

        # thumbnails (alla karaktärer + plats)
        thumbs: list[tuple[str,str]] = []
        for nm in chars:
            p = self._char_image(nm)
            if p: thumbs.append((nm, p))
        if li: thumbs.append((f"📍 {loc_name}", li))

        # fönster
        win = Toplevel(self); win.title("Event details")
        win.transient(self.winfo_toplevel()); win.grab_set()
        frm = ttk.Frame(win, padding=10); frm.pack(fill="both", expand=True)
        frm.columnconfigure(0, weight=1); frm.rowconfigure(0, weight=1)

        # text
        txt = tk.Text(frm, width=50, height=14, wrap="word")
        txt.insert("1.0", text); txt.configure(state="disabled")
        txt.grid(row=0, column=0, rowspan=2, sticky="nsew", padx=(0,8))

        # höger sida
        right = ttk.Frame(frm); right.grid(row=0, column=1, sticky="nsew")
        lbl_main = ttk.Label(right); lbl_main.pack(anchor="n")

        strip = ttk.Frame(frm); strip.grid(row=1, column=1, sticky="ew", pady=(8,0))
        win._imgs = []  # referenser

        def set_main(path: str):
            img = self._make_img(path, max_wh=(520,520))
            if img:
                lbl_main.configure(image=img, text="")
                win._imgs.append(img)
            else:
                lbl_main.configure(text=f"(Could not load image)\n{path}")

        # initial huvudbild
        done = False
        for p in main_candidates:
            if p and Path(p).exists():
                set_main(p); done = True; break
        if not done:
            lbl_main.configure(text="(No image)")

        # thumbnails klickbara
        for lab, p in thumbs:
            th = self._get_thumb(p, max_wh=(80,80))
            if not th: continue
            b = ttk.Label(strip, image=th, cursor="hand2")
            b.pack(side="left", padx=4)
            b.bind("<Button-1>", lambda e, path=p: set_main(path))
            win._imgs.append(th)
            ttk.Label(strip, text=lab).pack(side="left", padx=(0,8))

    #  pan 
    def _pan_start(self, e):
        self._pan_dragging = True
        self._pan_last_x = e.x

    def _pan_drag(self, e):
        if not self._pan_dragging: return
        dx = e.x - self._pan_last_x
        self._pan_last_x = e.x
        self._pan += dx
        self.redraw()

    def _pan_end(self, _e):
        self._pan_dragging = False

    # drag move 
    def _drag_start(self, event):
        cur = self.canvas.find_withtag("current")
        if not cur: return
        tags = self.canvas.gettags(cur[0])
        fidx = next((int(t.split("_")[1]) for t in tags if t.startswith("event_")), None)
        if fidx is None: return
        self._drag_ev_index = fidx
        if self._drag_marker:
            self.canvas.delete(self._drag_marker)
        self._drag_marker = self.canvas.create_line(event.x, event.y-20, event.x, event.y+20,
                                                    fill="#111", width=2, dash=(3,2))

    def _drag_motion(self, event):
        if self._drag_ev_index is None: return
        if self._drag_marker:
            self.canvas.coords(self._drag_marker, event.x, event.y-20, event.x, event.y+20)

    def _drag_end(self, event):
        if self._drag_ev_index is None: return
        near_date = self._x_to_nearest_date(event.x)
        if near_date:
            if hasattr(self.events_panel, "set_event_date_by_filtered_index"):
                self.events_panel.set_event_date_by_filtered_index(
                    self._drag_ev_index, _format_date_dmy(near_date)
                )
            else:
                ev = self.events_panel.filtered_data()[self._drag_ev_index]
                target_date = _format_date_dmy(near_date)
                idx = None
                for k, orig in enumerate(self.events_panel.data()):
                    if orig is ev: idx = k; break
                if idx is not None:
                    self.events_panel.data()[idx]["date"] = target_date
                    self.events_panel.refresh()
        self._drag_ev_index = None
        if self._drag_marker:
            self.canvas.delete(self._drag_marker); self._drag_marker = None
        self.redraw()
