import re
import tkinter as tk
from tkinter import ttk, filedialog
from datetime import date

_MONTHS = {
    "jan": 1, "januari": 1, "feb": 2, "februari": 2,
    "mar": 3, "mars": 3, "march": 3, "apr": 4, "april": 4,
    "maj": 5, "may": 5, "jun": 6, "juni": 6, "june": 6,
    "jul": 7, "juli": 7, "july": 7, "aug": 8, "augusti": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9, "okt": 10, "oktober": 10, "oct": 10, "october": 10,
    "nov": 11, "november": 11, "dec": 12, "december": 12,
}
def _parse_date_str(s: str):
    if not s: return (9999, 12, 31)
    t = s.strip().lower()
    m = re.match(r"^\s*(\d{4})[\/\-\.\s](\d{1,2})[\/\-\.\s](\d{1,2})\s*$", t)
    if m:
        y,mo,d = map(int,m.groups()); return (y, max(1,min(mo,12)), max(1,min(d,31)))
    m = re.match(r"^\s*(\d{1,2})[\/\-\.\s](\d{1,2})(?:[\/\-\.\s](\d{2,4}))?\s*$", t)
    if m:
        d,mo,y = m.groups(); d=int(d); mo=int(mo)
        if y is None: y = date.today().year
        else:
            y=int(y); y += 2000 if y<50 else (1900 if y<100 else 0)
        return (y, max(1,min(mo,12)), max(1,min(d,31)))
    m = re.match(r"^\s*(\d{1,2})\s+([a-zåäö\.]+)\s*(\d{2,4})?\s*$", t)
    if m:
        d,mon_txt,y = m.groups(); mon=_MONTHS.get(mon_txt.rstrip("."), None)
        if mon:
            d=int(d)
            if y is None: y = date.today().year
            else:
                y=int(y); y += 2000 if y<50 else (1900 if y<100 else 0)
            return (y, mon, max(1,min(d,31)))
    m = re.match(r"^\s*([a-zåäö\.]+)\s*(\d{2,4})?\s*$", t)
    if m:
        mon_txt,y = m.groups(); mon=_MONTHS.get(mon_txt.rstrip("."), None)
        if mon:
            if y is None: y = date.today().year
            else:
                y=int(y); y += 2000 if y<50 else (1900 if y<100 else 0)
            return (y, mon, 1)
    return (9999, 12, 31)


class EventsPanel(ttk.Frame):
    """
    CRUD + sortering + SÖK. Flera personer per event.
    Fält: title, date, characters[], activity, location, image
    """
    def __init__(self, master, get_characters, get_locations, on_change, on_filter=None):
        super().__init__(master)
        self.get_characters = get_characters
        self.get_locations = get_locations
        self.on_change = on_change
        self.on_filter = on_filter
        self._events: list[dict] = []
        self._filtered: list[dict] = []
        self._index_map: list[int] = []

        ttk.Label(self, text="Events", font=("TkDefaultFont", 11, "bold")).pack(pady=(4,2))

        # Search
        filters = ttk.Frame(self); filters.pack(fill="x", padx=2, pady=(0,4))
        ttk.Label(filters, text="Search").grid(row=0, column=0, sticky="w")
        self.search_var = tk.StringVar()
        ent = ttk.Entry(filters, textvariable=self.search_var, width=28)
        ent.grid(row=0, column=1, sticky="w", padx=(4,8))
        ent.bind("<KeyRelease>", lambda e: self._filter_changed())
        ttk.Button(filters, text="Clear", command=self._clear_search).grid(row=0, column=2, padx=(6,0))

        # Form
        form = ttk.Frame(self); form.pack(fill="x", pady=4)

        ttk.Label(form, text="Event").grid(row=0, column=0, sticky="w")
        self.title_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.title_var, width=22).grid(row=0, column=1, sticky="w")

        ttk.Label(form, text="Date").grid(row=1, column=0, sticky="w")
        self.date_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.date_var, width=22).grid(row=1, column=1, sticky="w")

        ttk.Label(form, text="Characters (flera val)").grid(row=2, column=0, sticky="nw")
        self.char_list = tk.Listbox(form, selectmode="multiple", height=6, exportselection=False)
        self.char_list.grid(row=2, column=1, sticky="nsew", pady=(2,2))
        self.char_list.bind("<Button-1>", self._toggle_on_click)
        form.columnconfigure(1, weight=1)

        ttk.Label(form, text="Activity:").grid(row=3, column=0, sticky="w")
        self.activity_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.activity_var, width=22).grid(row=3, column=1, sticky="w")

        ttk.Label(form, text="Location").grid(row=4, column=0, sticky="w")
        self.loc_var = tk.StringVar()
        self.loc_cb = ttk.Combobox(form, textvariable=self.loc_var, values=[], width=20, state="readonly")
        self.loc_cb.grid(row=4, column=1, sticky="w")

        ttk.Label(form, text="Image").grid(row=5, column=0, sticky="w")
        self.image_var = tk.StringVar()
        img_row = ttk.Frame(form); img_row.grid(row=5, column=1, sticky="we")
        ttk.Entry(img_row, textvariable=self.image_var, width=22).pack(side="left", fill="x", expand=True)
        ttk.Button(img_row, text="Browse…", command=self._browse_image).pack(side="left", padx=4)

        # Buttons
        btns = ttk.Frame(self); btns.pack(pady=4)
        ttk.Button(btns, text="Add", command=self.add_event).pack(side="left", padx=2)
        ttk.Button(btns, text="Update", command=self.update_event).pack(side="left", padx=2)
        ttk.Button(btns, text="Delete", command=self.delete_event).pack(side="left", padx=2)

        # List
        self.listbox = tk.Listbox(self, height=12)
        self.listbox.pack(fill="both", expand=True, pady=4)
        self.listbox.bind("<<ListboxSelect>>", self.fill_form)

    # Behaviors 
    def _toggle_on_click(self, event):
        idx = self.char_list.nearest(event.y)
        if idx >= 0:
            if self.char_list.selection_includes(idx):
                self.char_list.selection_clear(idx)
            else:
                self.char_list.selection_set(idx)
        return "break"

    # Public helpers
    def refresh_refs(self):
        self.char_list.delete(0, tk.END)
        for name in self.get_characters():
            self.char_list.insert(tk.END, name)
        self.loc_cb["values"] = self.get_locations()

    def data(self): return self._events
    def filtered_data(self): return list(self._filtered)

    def filtered_index_to_data_index(self, i: int) -> int | None:
        return self._index_map[i] if 0 <= i < len(self._index_map) else None

    def set_search(self, text: str):
        self.search_var.set(text or "")
        self._filter_changed()

    def events_for_character(self, name: str) -> list[dict]:
        return [ev for ev in self._events if name in (ev.get("characters") or [])]

    def set_data(self, items: list[dict]):
        normalized = []
        for ev in items or []:
            ev = dict(ev)
            if "characters" not in ev:
                ch = ev.get("character","").strip()
                ev["characters"] = [ch] if ch else []
            else:
                ev["characters"] = [s for s in (ev.get("characters") or []) if str(s).strip()]
            ev["activity"] = ev.get("activity","").strip()
            ev["location"] = ev.get("location","").strip()
            ev["image"] = (ev.get("image","") or "").strip()
            ev.pop("character", None)
            normalized.append(ev)
        self._events = normalized
        self._sort(); self._apply_filter()
        if self.on_filter: self.on_filter()

    # sort/filter
    def _sort(self): self._events.sort(key=lambda ev: _parse_date_str(ev.get("date","")))
    def _clear_search(self): self.search_var.set(""); self._filter_changed()
    def _filter_changed(self): self._apply_filter();  self.on_filter and self.on_filter()

    def _apply_filter(self):
        self._sort()
        q = self.search_var.get().strip().lower()

        def match(ev):
            if not q: return True
            chars = ", ".join(ev.get("characters", []))
            hay = " ".join([ev.get("Event",""), ev.get("date",""),
                            ev.get("activity",""), chars, ev.get("location",""),
                            ev.get("image","")]).lower()
            return q in hay

        self._filtered, self._index_map = [], []
        for i, ev in enumerate(self._events):
            if match(ev):
                self._filtered.append(ev); self._index_map.append(i)

        self.listbox.delete(0, tk.END)
        for ev in self._filtered:
            chars = ", ".join(ev.get("characters", []))
            lo = ev.get("location","")
            act = ev.get("activity","")
            label = f'{ev.get("date","")}: {ev.get("title","")}'
            if act: label += f' – {act}'
            label += f' ({chars}/{lo})'
            if ev.get("image"): label += " [🖼]"
            self.listbox.insert(tk.END, label)

    # CRUD
    def _selected_chars_from_form(self) -> list[str]:
        return [self.char_list.get(i) for i in self.char_list.curselection()]

    def add_event(self):
        t = self.title_var.get().strip()
        if not t: return
        self._events.append({
            "Event": t,
            "date": self.date_var.get().strip(),
            "characters": self._selected_chars_from_form(),
            "activity": self.activity_var.get().strip(),
            "location": self.loc_var.get().strip(),
            "image": self.image_var.get().strip(),
        })
        self.refresh(); self.clear_form()

    def update_event(self):
        idx = self.filtered_index_to_data_index(self._selected_index())
        if idx is None: return
        self._events[idx] = {
            "Event": self.title_var.get().strip(),
            "date": self.date_var.get().strip(),
            "characters": self._selected_chars_from_form(),
            "activity": self.activity_var.get().strip(),
            "location": self.loc_var.get().strip(),
            "image": self.image_var.get().strip(),
        }
        self.refresh()

    def delete_event(self):
        idx = self.filtered_index_to_data_index(self._selected_index())
        if idx is None: return
        del self._events[idx]
        self.refresh(); self.clear_form()

    def refresh(self):
        self._apply_filter()
        self.on_change()

    # listbox helpers
    def _selected_index(self):
        sel = self.listbox.curselection()
        return sel[0] if sel else None

    def fill_form(self, *_):
        i = self._selected_index()
        if i is None: return
        ev = self._filtered[i]
        self.title_var.set(ev.get("Event",""))
        self.date_var.set(ev.get("date",""))
        self.activity_var.set(ev.get("activity",""))
        self.loc_var.set(ev.get("location",""))
        self.image_var.set(ev.get("image",""))
        self.char_list.selection_clear(0, tk.END)
        all_names = [self.char_list.get(j) for j in range(self.char_list.size())]
        for j, nm in enumerate(all_names):
            if nm in (ev.get("characters") or []):
                self.char_list.selection_set(j)

    def clear_form(self):
        self.title_var.set(""); self.date_var.set("")
        self.activity_var.set(""); self.loc_var.set("")
        self.image_var.set("")
        self.char_list.selection_clear(0, tk.END)

    # browse
    def _browse_image(self):
        path = filedialog.askopenfilename(
            title="Select image",
            filetypes=[("Image files", "*.png;*.jpg;*.jpeg;*.gif;*.webp;*.bmp"), ("All files", "*.*")]
        )
        if path:
            self.image_var.set(path)

    def set_event_date_by_filtered_index(self, filtered_idx: int, new_date_str: str):
        di = self.filtered_index_to_data_index(filtered_idx)
        if di is None: return
        self._events[di]["date"] = (new_date_str or "").strip()
        self.refresh()
