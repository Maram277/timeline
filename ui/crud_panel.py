import tkinter as tk
from tkinter import ttk

class CrudPanel(ttk.Frame):
    """
    Reusable panel for Characters/Locations with 2 fields (name, description),
    a list, and buttons: Add / Update / Delete.
    """
    def __init__(self, master, title: str, on_change, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.on_change = on_change
        self._items: list[dict[str, str]] = []

        # Title
        ttk.Label(self, text=title, font=("TkDefaultFont", 11, "bold")).grid(
            row=0, column=0, columnspan=3, pady=(2, 6)
        )

        # Form (2 fields)
        ttk.Label(self, text="Name").grid(row=1, column=0, sticky="w")
        self.name_var = tk.StringVar()
        self.name_entry = ttk.Entry(self, textvariable=self.name_var, width=34)
        self.name_entry.grid(row=1, column=1, columnspan=2, sticky="ew", pady=2)

        ttk.Label(self, text="Description").grid(row=2, column=0, sticky="w")
        self.desc_var = tk.StringVar()
        self.desc_entry = ttk.Entry(self, textvariable=self.desc_var, width=34)
        self.desc_entry.grid(row=2, column=1, columnspan=2, sticky="ew", pady=(0, 6))

        # Buttons
        ttk.Button(self, text="Add", command=self.add_item).grid(row=3, column=0, pady=2, sticky="ew")
        ttk.Button(self, text="Update", command=self.update_item).grid(row=3, column=1, pady=2, sticky="ew")
        ttk.Button(self, text="Delete", command=self.delete_item).grid(row=3, column=2, pady=2, sticky="ew")

        # List
        self.listbox = tk.Listbox(self, height=10)
        self.listbox.grid(row=4, column=0, columnspan=3, sticky="nsew", pady=(6, 0))
        self.listbox.bind("<<ListboxSelect>>", self.fill_form_from_selection)
        self.listbox.bind("<Double-Button-1>", self.fill_form_from_selection)

        # Layout weights
        self.columnconfigure(1, weight=1)
        self.rowconfigure(4, weight=1)

    # --- Public API ---
    def data(self) -> list[dict]:
        return self._items

    def set_data(self, items: list[dict]):
        self._items = items or []
        self.refresh()

    # --- Internals ---
    def refresh(self):
        self.listbox.delete(0, tk.END)
        for it in self._items:
            self.listbox.insert(tk.END, it.get("name", ""))
        self.on_change()

    def selected_index(self):
        sel = self.listbox.curselection()
        return sel[0] if sel else None

    def fill_form_from_selection(self, *_):
        i = self.selected_index()
        if i is None:
            return
        self.name_var.set(self._items[i].get("name", ""))
        self.desc_var.set(self._items[i].get("description", ""))

    def clear_form(self):
        self.name_var.set("")
        self.desc_var.set("")
        self.name_entry.focus()

    def add_item(self):
        name = self.name_var.get().strip()
        if not name:
            return
        self._items.append({"name": name, "description": self.desc_var.get().strip()})
        self.refresh()
        self.clear_form()

    def update_item(self):
        i = self.selected_index()
        if i is None:
            return
        self._items[i] = {
            "name": self.name_var.get().strip(),
            "description": self.desc_var.get().strip(),
        }
        self.refresh()

    def delete_item(self):
        i = self.selected_index()
        if i is None:
            return
        del self._items[i]
        self.refresh()
        self.clear_form()
