# ui/crud_panel.py
import tkinter as tk
from tkinter import ttk, filedialog
from pathlib import Path

try:
    from PIL import Image, ImageTk
    PIL_OK = True
except Exception:
    PIL_OK = False


class CrudPanel(ttk.Frame):
    """
    Återanvändbar panel för Characters/Locations med 3 fält:
    name, description, image (FAST preview).
    - Behåller vald post vid Add/Update (formuläret rensas inte automatiskt).
    - Visar färger i listan via optional color_getter(name)->hex.
    """
    PREVIEW_SIZE = (220, 160)

    def __init__(self, master, title: str, on_change, color_getter=None, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.on_change = on_change
        self.color_getter = color_getter  # optional: func(name)-> "#rrggbb"
        self._items: list[dict[str, str]] = []
        self._preview_img = None

        ttk.Label(self, text=title, font=("TkDefaultFont", 11, "bold")).grid(
            row=0, column=0, columnspan=4, pady=(2, 6), sticky="w"
        )

        # Name
        ttk.Label(self, text="Name").grid(row=1, column=0, sticky="w")
        self.name_var = tk.StringVar()
        self.name_entry = ttk.Entry(self, textvariable=self.name_var, width=34)
        self.name_entry.grid(row=1, column=1, columnspan=3, sticky="ew", pady=2)

        # Description
        ttk.Label(self, text="Description").grid(row=2, column=0, sticky="w")
        self.desc_var = tk.StringVar()
        self.desc_entry = ttk.Entry(self, textvariable=self.desc_var, width=34)
        self.desc_entry.grid(row=2, column=1, columnspan=3, sticky="ew", pady=(0, 6))

        # Image
        ttk.Label(self, text="Image").grid(row=3, column=0, sticky="w")
        self.image_var = tk.StringVar()
        self.image_entry = ttk.Entry(self, textvariable=self.image_var)
        self.image_entry.grid(row=3, column=1, sticky="ew", pady=2)
        ttk.Button(self, text="Choose...", command=self._choose_image).grid(row=3, column=2, padx=(6, 0))
        ttk.Button(self, text="Clear", command=self._clear_image).grid(row=3, column=3)

        # Preview (låst storlek)
        holder = ttk.Frame(self, height=self.PREVIEW_SIZE[1])
        holder.grid(row=4, column=0, columnspan=4, sticky="ew", pady=(6, 6))
        holder.grid_propagate(False)
        self.preview = ttk.Label(holder, anchor="center")
        self.preview.place(relx=0.5, rely=0.5, anchor="center",
                           width=self.PREVIEW_SIZE[0], height=self.PREVIEW_SIZE[1])

        # Buttons
        ttk.Button(self, text="Add", command=self.add_item).grid(row=5, column=0, pady=2, sticky="ew")
        ttk.Button(self, text="Update", command=self.update_item).grid(row=5, column=1, pady=2, sticky="ew")
        ttk.Button(self, text="Delete", command=self.delete_item).grid(row=5, column=2, pady=2, sticky="ew")

        # Listbox
        self.listbox = tk.Listbox(self, height=10)
        self.listbox.grid(row=6, column=0, columnspan=4, sticky="nsew", pady=(6, 0))
        self.listbox.bind("<<ListboxSelect>>", self.fill_form_from_selection)

        # Layout
        self.columnconfigure(1, weight=1)
        self.rowconfigure(6, weight=1)
        self.rowconfigure(4, weight=0)

        # Uppdatera preview när texten ändras
        self.image_var.trace_add("write", lambda *_: self._refresh_preview())

    def data(self) -> list[dict]:
        return self._items

    def set_data(self, items: list[dict]):
        self._items = []
        for it in (items or []):
            it = dict(it)
            it["name"] = it.get("name", "")
            it["description"] = it.get("description", "")
            it["image"] = it.get("image", "")
            self._items.append(it)
        self.refresh()
        self._refresh_preview()

    def refresh(self):
        self.listbox.delete(0, tk.END)
        for idx, it in enumerate(self._items):
            nm = it.get("name", "")
            label = nm + ("  [🖼]" if it.get("image") else "")
            self.listbox.insert(tk.END, label)
            if self.color_getter and nm:
                try:
                    clr = self.color_getter(nm)
                    self.listbox.itemconfig(idx, foreground=clr)
                except Exception:
                    pass
        self.on_change()

    def selected_index(self):
        sel = self.listbox.curselection()
        return sel[0] if sel else None

    def _select_and_fill(self, idx: int):
        """Välj given post i listan och fyll formuläret (används efter Add/Update)."""
        if 0 <= idx < len(self._items):
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(idx)
            self.listbox.see(idx)
            self.fill_form_from_selection()

    def fill_form_from_selection(self, *_):
        i = self.selected_index()
        if i is None:
            return
        self.name_var.set(self._items[i].get("name", ""))
        self.desc_var.set(self._items[i].get("description", ""))
        self.image_var.set(self._items[i].get("image", ""))
        self._refresh_preview()

    # CRUD 
    def add_item(self):
        name = self.name_var.get().strip()
        if not name:
            return
        self._items.append({
            "name": name,
            "description": self.desc_var.get().strip(),
            "image": self.image_var.get().strip(),
        })
        new_idx = len(self._items) - 1
        self.refresh()
        self._select_and_fill(new_idx)

    def update_item(self):
        i = self.selected_index()
        if i is None:
            return
        self._items[i] = {
            "name": self.name_var.get().strip(),
            "description": self.desc_var.get().strip(),
            "image": self.image_var.get().strip(),
        }
        self.refresh()
        self._select_and_fill(i)

    def delete_item(self):
        i = self.selected_index()
        if i is None:
            return
        del self._items[i]
        self.refresh()
        # välj närmaste kvarvarande
        self._select_and_fill(min(i, len(self._items) - 1))

    def clear_form(self):
        self.name_var.set("")
        self.desc_var.set("")
        self.image_var.set("")
        self._refresh_preview()
        self.name_entry.focus()

    def _choose_image(self):
        path = filedialog.askopenfilename(
            title="Select image",
            filetypes=[
                ("Image files", "*.png;*.jpg;*.jpeg;*.gif;*.webp;*.bmp"),
                ("All files", "*.*"),
            ],
        )
        if path:
            self.image_var.set(path)

    def _clear_image(self):
        self.image_var.set("")

    def _refresh_preview(self):
        path = self.image_var.get().strip()
        if not path or not Path(path).exists():
            self.preview.configure(image="", text="")
            self._preview_img = None
            return
        try:
            if PIL_OK:
                im = Image.open(path)
                im.thumbnail(self.PREVIEW_SIZE)
                img = ImageTk.PhotoImage(im)
            else:
                img = tk.PhotoImage(file=path)
            self.preview.configure(image=img, text="")
            self._preview_img = img
        except Exception:
            self.preview.configure(image="", text=f"(Could not load)\n{path}")
            self._preview_img = None
