# app.py
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path

from ui.crud_panel import CrudPanel
from ui.events_panel import EventsPanel
from ui.timeline_view import TimelineView, color_for_character, color_for_location
from storage import new_empty_project, load_project, save_project


# ScrollableFrame (för Editor-fliken) 
class ScrollableFrame(ttk.Frame):
    """En ttk.Frame som kan scrollas vertikalt via en Canvas."""
    def __init__(self, master, *args, **kwargs):
        super().__init__(master, *args, **kwargs)

        self.canvas = tk.Canvas(self, highlightthickness=0)
        self.vbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.vbar.set)

        # 'inner' är där vi placerar det riktiga innehållet
        self.inner = ttk.Frame(self.canvas)
        self.inner_id = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")

        self.canvas.pack(side="left", fill="both", expand=True)
        self.vbar.pack(side="right", fill="y")

        # håll scrollregion uppdaterad
        self.inner.bind("<Configure>", self._on_inner_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        # mus/tangent-scroll
        self._bind_scroll(self.canvas)

    def _on_inner_configure(self, _e=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, e):
        self.canvas.itemconfigure(self.inner_id, width=e.width)

    def _bind_scroll(self, widget):
        # Windows/macOS
        widget.bind_all("<MouseWheel>", self._on_mousewheel, add="+")
        # Linux
        widget.bind_all("<Button-4>", self._on_mousewheel, add="+")
        widget.bind_all("<Button-5>", self._on_mousewheel, add="+")
        # PgUp/PgDn/Home/End
        widget.bind_all("<Next>", lambda e: self._scroll_pages(1), add="+")
        widget.bind_all("<Prior>", lambda e: self._scroll_pages(-1), add="+")
        widget.bind_all("<Home>", lambda e: self.canvas.yview_moveto(0), add="+")
        widget.bind_all("<End>",  lambda e: self.canvas.yview_moveto(1), add="+")

    def _on_mousewheel(self, e):
        # Linux: Button-4/5, annars delta
        if getattr(e, "num", None) == 4:
            self.canvas.yview_scroll(-3, "units")
        elif getattr(e, "num", None) == 5:
            self.canvas.yview_scroll(3, "units")
        else:
            # På Windows är delta positiv uppåt
            step = -1 if e.delta > 0 else 1
            self.canvas.yview_scroll(step * 3, "units")

    def _scroll_pages(self, pages):
        self.canvas.yview_scroll(pages, "pages")


#  Huvudapp 
class TimelineApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Timeline Project")
        self.geometry("1100x650")

        self.project_path: Path | None = None
        self._dirty = False

        # Meny
        menubar = tk.Menu(self)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="New Project", command=self.new_project)
        file_menu.add_command(label="Open…",        command=self.open_project, accelerator="Ctrl+O")
        file_menu.add_command(label="Save",         command=self.save_project, accelerator="Ctrl+S")
        file_menu.add_command(label="Save As…",     command=self.save_as)
        file_menu.add_separator()
        file_menu.add_command(label="Exit",         command=self.quit)
        menubar.add_cascade(label="File", menu=file_menu)
        self.config(menu=menubar)

        self.bind("<Control-s>", lambda e: self.save_project())
        self.bind("<Control-o>", lambda e: self.open_project())

        # Notebook
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True)
        self.editor_tab = ttk.Frame(self.notebook)
        self.timeline_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.editor_tab, text="Editor")
        self.notebook.add(self.timeline_tab, text="Timeline")
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)

        #  Editor-sidan (scrollbar) 
        editor_scroll = ScrollableFrame(self.editor_tab)  
        editor_scroll.pack(fill="both", expand=True)
        editor_root = editor_scroll.inner                 

        editor_root.columnconfigure(0, weight=1)
        editor_root.columnconfigure(1, weight=1)

        # Vänster kolumn: Characters + Locations
        left = ttk.Frame(editor_root, padding=10)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        self.characters_panel = CrudPanel(
            left,
            "Characters (name, description)",
            on_change=self.mark_dirty,
            color_getter=color_for_character,   
        )
        self.characters_panel.pack(fill="both", expand=True, pady=(0, 8))

        self.locations_panel = CrudPanel(
            left,
            "Locations (name, description)",
            on_change=self.mark_dirty,
            color_getter=color_for_location,    
        )
        self.locations_panel.pack(fill="both", expand=True)

        # Hjälpare för namnlistor till EventsPanel
        def _get_char_names():
            return [c.get("name", "") for c in self.characters_panel.data()]

        def _get_loc_names():
            return [l.get("name", "") for l in self.locations_panel.data()]

        # Höger kolumn: Events
        right = ttk.Frame(editor_root, padding=10)
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        self.events_panel = EventsPanel(
            right,
            get_characters=lambda: _get_char_names(),
            get_locations=lambda: _get_loc_names(),
            on_change=self.mark_dirty,
            on_filter=self._timeline_redraw_safe,
        )
        self.events_panel.pack(fill="both", expand=True)

        #  Timeline-sidan 
        self.timeline_view = TimelineView(
            self.timeline_tab,
            get_characters=lambda: self.characters_panel.data(),
            get_locations=lambda: self.locations_panel.data(),
            events_panel=self.events_panel,
        )
        self.timeline_view.pack(fill="both", expand=True)

        # Start
        self.new_project()

    #  interna hjälpare 
    def _timeline_redraw_safe(self):
        try:
            self.timeline_view.redraw()
        except Exception:
            pass

    def _on_tab_changed(self, _e):
        if self.notebook.select() == self.notebook.tabs()[1]:
            self.timeline_view.redraw()

    def mark_dirty(self):
        self._dirty = True
        # uppdatera referenser i event-form (namnlistor)
        try:
            self.events_panel.refresh_refs()
        except Exception:
            pass
        self._timeline_redraw_safe()

    #  Filhantering 
    def new_project(self):
        """Starta helt tomt projekt + rensa alla formulär & sökfält."""
        # 1) Tom data
        self.characters_panel.set_data([])
        self.locations_panel.set_data([])
        self.events_panel.set_data([])

        # 2) Rensa alla formulär + sök
        try:
            self.characters_panel.clear_form()
        except Exception:
            pass
        try:
            self.locations_panel.clear_form()
        except Exception:
            pass
        try:
            self.events_panel.set_search("") 
            self.events_panel.clear_form()
        except Exception:
            pass

        # 3) Återställ filstatus och timeline
        self.project_path = None
        self._dirty = False
        self._timeline_redraw_safe()

    def save_as(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
            title="Save project as"
        )
        if path:
            self.project_path = Path(path)
            self._write_current()

    def save_project(self):
        if not self.project_path:
            return self.save_as()
        self._write_current()

    def _write_current(self):
        data = {
            "characters": self.characters_panel.data(),
            "locations":  self.locations_panel.data(),
            "events":     self.events_panel.data(),  
        }
        try:
            save_project(self.project_path, data)
            self._dirty = False
        except Exception as e:
            messagebox.showerror("Error", f"Could not save file:\n{e}")

    def open_project(self):
        path = filedialog.askopenfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
            title="Open project"
        )
        if not path:
            return
        try:
            data = load_project(Path(path))

            try:
                self.characters_panel.clear_form()
                self.locations_panel.clear_form()
                self.events_panel.set_search("")
                self.events_panel.clear_form()
            except Exception:
                pass

            self.characters_panel.set_data(list(data.get("characters", [])))
            self.locations_panel.set_data(list(data.get("locations", [])))
            self.events_panel.set_data(list(data.get("events", [])))  

            self.project_path = Path(path)
            self._dirty = False
            self._timeline_redraw_safe()
        except Exception as e:
            messagebox.showerror("Error", f"Could not open file:\n{e}")


if __name__ == "__main__":
    TimelineApp().mainloop()
