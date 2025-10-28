Timeline – Working Prototype

A simple desktop app (Tkinter) to plan stories on a timeline with Characters, Locations, and Events.
Features
Create/edit/delete Characters & Locations (optional image preview with Pillow).
Create Events and link them to characters/locations.
Flexible date parsing (e.g., 2025-10-28, 28/10/2025, 28 Oct 2025).
Color-coded Timeline view for quick overview.
Save/Open projects as JSON.

Requirements:
Python 3.10+
Tkinter
Pillow (recommended for image preview)

Installation
git clone <YOUR-REPO-URL>
cd timeline

python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate
pip install -r requirements.txt

Run
python main.py

Project Structure:
├─ main.py              
├─ app.py               
├─ storage.py           
├─ ui/
│  ├─ crud_panel.py     
│  ├─ events_panel.py   
│  └─ timeline_view.py  
├─ *.json               
└─ README.md

Everything savs in JSON.