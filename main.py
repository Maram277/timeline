import tkinter as tk
import json

characters = []

def add_character():
    name = entry.get()
    if name.strip():
        characters.append({"name": name})
        entry.delete(0, tk.END)
        update_listbox()

def update_listbox():
    listbox.delete(0, tk.END)
    for c in characters:
        listbox.insert(tk.END, c["name"])

def save_project(filename="project.json"):
    data = {"characters": characters}
    with open(filename, "w") as f:
        json.dump(data, f, indent=2)

def main():
    global entry, listbox

    root = tk.Tk()
    root.title("Timeline Projekt")
    root.geometry("400x300")

    label = tk.Label(root, text="Lägg till karaktär:")
    label.pack(pady=5)

    entry = tk.Entry(root, width=30)
    entry.pack(pady=5)

    add_button = tk.Button(root, text="Lägg till", command=add_character)
    add_button.pack(pady=5)

    listbox = tk.Listbox(root, width=30, height=10)
    listbox.pack(pady=10)

    save_button = tk.Button(root, text="Spara projekt", command=save_project)
    save_button.pack(pady=5)

    root.mainloop()

if __name__ == "__main__":
    main()
