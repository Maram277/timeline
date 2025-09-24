import json
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from ui.crud_panel import CrudPanel
from storage import new_empty_project, load_project, save_project


class TimelineApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Timeline Projekt")
        self.geometry("720x420")
        self.minsize(680, 380)

        self.project_path: Path | None = None
        self._dirty = False

        # Meny
        menubar = tk.Menu(self)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Ny", command=self.new_project)
        file_menu.add_command(label="Öppna…   Ctrl+O", command=self.open_project)
        file_menu.add_command(label="Spara     Ctrl+S", command=self.save_project)
        file_menu.add_command(label="Spara som…", command=self.save_as)
        file_menu.add_separator()
        file_menu.add_command(label="Avsluta", command=self.quit)
        menubar.add_cascade(label="Arkiv", menu=file_menu)
        self.config(menu=menubar)

        # Kortkommandon
        self.bind("<Control-s>", lambda e: self.save_project())
        self.bind("<Control-o>", lambda e: self.open_project())

        # Layout: två CRUD-paneler sida vid sida
        container = ttk.Frame(self, padding=10)
        container.pack(fill="both", expand=True)
        container.columnconfigure(0, weight=1)
        container.columnconfigure(1, weight=1)
        container.rowconfigure(0, weight=1)

        self.characters_panel = CrudPanel(
            container, title="Karaktärer (name, description)",
            on_change=self.mark_dirty
        )
        self.characters_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        self.locations_panel = CrudPanel(
            container, title="Platser (name, description)",
            on_change=self.mark_dirty
        )
        self.locations_panel.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        self.new_project()

    # --- state helpers ---
    def mark_dirty(self):  # kallas vid ändringar i panelerna
        self._dirty = True

    # --- file actions ---
    def new_project(self):
        data = new_empty_project()
        self.characters_panel.set_data(data["characters"])
        self.locations_panel.set_data(data["locations"])
        self.project_path = None
        self._dirty = False

    def save_as(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
            title="Spara projekt som"
        )
        if path:
            self.project_path = Path(path)
            self._write_current_data()

    def save_project(self):
        if not self.project_path:
            return self.save_as()
        self._write_current_data()

    def _write_current_data(self):
        data = {
            "characters": self.characters_panel.data(),
            "locations": self.locations_panel.data(),
        }
        try:
            save_project(self.project_path, data)
            self._dirty = False
        except Exception as e:
            messagebox.showerror("Fel", f"Kunde inte spara filen:\n{e}")

    def open_project(self):
        path = filedialog.askopenfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
            title="Öppna projekt"
        )
        if not path:
            return
        try:
            data = load_project(Path(path))
            self.characters_panel.set_data(list(data.get("characters", [])))
            self.locations_panel.set_data(list(data.get("locations", [])))
            self.project_path = Path(path)
            self._dirty = False
        except Exception as e:
            messagebox.showerror("Fel", f"Kunde inte öppna filen:\n{e}")
