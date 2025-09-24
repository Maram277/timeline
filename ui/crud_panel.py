import tkinter as tk
from tkinter import ttk, filedialog

class CrudPanel(ttk.Frame):
    def __init__(self, master, title: str, on_change, *_, **__):
        super().__init__(master)
        self.on_change = on_change
        self._items: list[dict] = []
        self._filtered_idx: list[int] = []

        ttk.Label(self, text=title, font=("TkDefaultFont", 11, "bold")).grid(row=0, column=0, columnspan=4, pady=(2,6))

        # Filter
        ttk.Label(self, text="Search").grid(row=1, column=0, sticky="w")
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self.refresh())
        ttk.Entry(self, textvariable=self.search_var, width=28).grid(row=1, column=1, columnspan=3, sticky="ew", pady=2)

        # Form (2 fields)
        ttk.Label(self, text="Name").grid(row=2, column=0, sticky="w")
        self.name_var = tk.StringVar()
        ttk.Entry(self, textvariable=self.name_var, width=32).grid(row=2, column=1, columnspan=3, sticky="ew")

        ttk.Label(self, text="Description").grid(row=3, column=0, sticky="w")
        self.desc_var = tk.StringVar()
        ttk.Entry(self, textvariable=self.desc_var, width=32).grid(row=3, column=1, columnspan=2, sticky="ew")

        self.image_path: str | None = None
        ttk.Button(self, text="Attach image…", command=self.pick_image).grid(row=3, column=3, sticky="ew", padx=(6,0))

        # Buttons
        ttk.Button(self, text="Add", command=self.add_item).grid(row=4, column=0, sticky="ew", pady=4)
        ttk.Button(self, text="Update", command=self.update_item).grid(row=4, column=1, sticky="ew")
        ttk.Button(self, text="Delete", command=self.delete_item).grid(row=4, column=2, sticky="ew")
        ttk.Button(self, text="Clear", command=self.clear_form).grid(row=4, column=3, sticky="ew")

        # List
        self.listbox = tk.Listbox(self, height=10)
        self.listbox.grid(row=5, column=0, columnspan=4, sticky="nsew", pady=(6,0))
        self.listbox.bind("<<ListboxSelect>>", self.fill_from_selection)

        self.columnconfigure(1, weight=1)
        self.rowconfigure(5, weight=1)

    def pick_image(self):
        path = filedialog.askopenfilename(filetypes=[("Images","*.png;*.jpg;*.jpeg;*.gif")])
        if path: self.image_path = path

    # API
    def data(self) -> list[dict]: return self._items
    def set_data(self, items: list[dict]): self._items = items or []; self.refresh()

    # CRUD
    def add_item(self):
        name = self.name_var.get().strip()
        if not name: return
        item = {"name": name, "description": self.desc_var.get().strip()}
        if self.image_path: item["image"] = self.image_path
        self._items.append(item)
        self.refresh(); self.clear_form()

    def update_item(self):
        idx = self._current_index()
        if idx is None: return
        self._items[idx]["name"] = self.name_var.get().strip()
        self._items[idx]["description"] = self.desc_var.get().strip()
        if self.image_path: self._items[idx]["image"] = self.image_path
        self.refresh()

    def delete_item(self):
        idx = self._current_index()
        if idx is None: return
        del self._items[idx]
        self.refresh(); self.clear_form()

    def _current_index(self):
        sel = self.listbox.curselection()
        if not sel: return None
        visual_idx = sel[0]
        return self._filtered_idx[visual_idx] if self._filtered_idx else visual_idx

    def fill_from_selection(self, *_):
        idx = self._current_index()
        if idx is None: return
        it = self._items[idx]
        self.name_var.set(it.get("name",""))
        self.desc_var.set(it.get("description",""))
        self.image_path = it.get("image")

    def clear_form(self):
        self.name_var.set(""); self.desc_var.set(""); self.image_path = None

    def refresh(self):
        q = self.search_var.get().lower().strip()
        self.listbox.delete(0, tk.END)
        self._filtered_idx = []
        for i, it in enumerate(self._items):
            label = it.get("name","")
            if not q or q in label.lower():
                self.listbox.insert(tk.END, label)
                self._filtered_idx.append(i)
        self.on_change()
