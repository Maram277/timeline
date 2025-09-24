from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from ui.crud_panel import CrudPanel
from ui.events_panel import EventsPanel
from ui.timeline_view import TimelineView
from storage import new_empty_project, load_project, save_project, autosave

class TimelineApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Timeline Project")
        self.geometry("980x520")
        self.minsize(900, 480)

        self.project_path: Path | None = None
        self._dirty = False
        self._autosave_job = None

        # Menu
        menubar = tk.Menu(self)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="New", command=self.new_project)
        file_menu.add_command(label="Open…   Ctrl+O", command=self.open_project)
        file_menu.add_command(label="Save     Ctrl+S", command=self.save_project)
        file_menu.add_command(label="Save As…", command=self.save_as)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.quit)
        menubar.add_cascade(label="File", menu=file_menu)
        self.config(menu=menubar)

        self.bind("<Control-s>", lambda e: self.save_project())
        self.bind("<Control-o>", lambda e: self.open_project())

        # Search bar (filters all panels)
        top = ttk.Frame(self, padding=(10, 6))
        top.pack(fill="x")
        ttk.Label(top, text="Search all").pack(side="left")
        self.global_search = tk.StringVar()
        self.global_search.trace_add("write", lambda *_: self.apply_global_filter())
        ttk.Entry(top, textvariable=self.global_search, width=40).pack(side="left", padx=(6,0))

        # Main layout: left (characters/locations), center (events), right (timeline)
        root = ttk.Frame(self, padding=10)
        root.pack(fill="both", expand=True)
        for i in (0,1,2): root.columnconfigure(i, weight=1)
        root.rowconfigure(0, weight=1)

        left = ttk.Frame(root); left.grid(row=0, column=0, sticky="nsew", padx=(0,8))
        center = ttk.Frame(root); center.grid(row=0, column=1, sticky="nsew", padx=8)
        right = ttk.Frame(root); right.grid(row=0, column=2, sticky="nsew", padx=(8,0))

        self.characters_panel = CrudPanel(left, "Characters", on_change=self.mark_dirty)
        self.locations_panel  = CrudPanel(left, "Locations",  on_change=self.mark_dirty)
        self.characters_panel.pack(fill="both", expand=True, pady=(0,8))
        self.locations_panel.pack(fill="both", expand=True)

        self.events_panel = EventsPanel(center,
            get_char_names=lambda: [c["name"] for c in self.characters_panel.data()],
            get_loc_names=lambda:  [l["name"] for l in self.locations_panel.data()],
            on_change=self.mark_dirty)
        self.events_panel.pack(fill="both", expand=True)

        self.timeline = TimelineView(right, get_events=lambda: self.events_panel.data())
        self.timeline.pack(fill="both", expand=True)

        self.new_project()

    # --- helpers ---
    def mark_dirty(self):
        self._dirty = True
        self.schedule_autosave()
        self.events_panel.refresh_refs()
        self.timeline.redraw()

    def schedule_autosave(self):
        if self._autosave_job: self.after_cancel(self._autosave_job)
        self._autosave_job = self.after(15000, self._do_autosave)  # 15s

    def _do_autosave(self):
        data = self._collect_data()
        autosave(self.project_path, data)

    def _collect_data(self):
        return {
            "characters": self.characters_panel.data(),
            "locations": self.locations_panel.data(),
            "events": self.events_panel.data(),
        }

    # --- file ops ---
    def new_project(self):
        data = new_empty_project()
        self.characters_panel.set_data(data["characters"])
        self.locations_panel.set_data(data["locations"])
        self.events_panel.set_data(data["events"])
        self.project_path = None
        self._dirty = False
        self.timeline.redraw()

    def save_as(self):
        path = filedialog.asksaveasfilename(defaultextension=".json",
                                            filetypes=[("JSON files","*.json")],
                                            title="Save project as")
        if path:
            self.project_path = Path(path)
            self._write_current()

    def save_project(self):
        if not self.project_path:
            return self.save_as()
        self._write_current()

    def _write_current(self):
        try:
            save_project(self.project_path, self._collect_data())
            self._dirty = False
        except Exception as e:
            messagebox.showerror("Error", f"Could not save file:\n{e}")

    def open_project(self):
        path = filedialog.askopenfilename(defaultextension=".json",
                                          filetypes=[("JSON files","*.json")],
                                          title="Open project")
        if not path: return
        try:
            data = load_project(Path(path))
            self.characters_panel.set_data(list(data.get("characters", [])))
            self.locations_panel.set_data(list(data.get("locations", [])))
            self.events_panel.set_data(list(data.get("events", [])))
            self.events_panel.refresh_refs()
            self.project_path = Path(path)
            self._dirty = False
            self.timeline.redraw()
        except Exception as e:
            messagebox.showerror("Error", f"Could not open file:\n{e}")

    def apply_global_filter(self):
        # vidarekoppla söksträngen till panelerna
        q = self.global_search.get()
        self.characters_panel.search_var.set(q)
        self.locations_panel.search_var.set(q)
        # events-panelen filtrerar inte listan (för enkelhet), men du kan lägga till om du vill
