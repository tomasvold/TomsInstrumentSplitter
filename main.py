import os
import glob
import shutil
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import subprocess
import threading
import re

def select_file():
    path = filedialog.askopenfilename(
        title="Select Audio File",
        filetypes=[("Audio Files", "*.wav *.mp3 *.flac")]
    )
    if not path:
        return
    entry_file.delete(0, tk.END)
    entry_file.insert(0, path)
    # Auto-set output folder to the file's directory
    folder = os.path.dirname(path)
    entry_output.delete(0, tk.END)
    entry_output.insert(0, folder)

def select_output_dir():
    path = filedialog.askdirectory(title="Select Output Directory")
    if not path:
        return
    entry_output.delete(0, tk.END)
    entry_output.insert(0, path)

def process_with_progress(cmd):
    """Run subprocess, parse 'XX%' lines to update bar and label,
    suppressing the extra console window on Windows."""
    # Prepare to hide console on Windows
    startupinfo = None
    creationflags = 0
    if sys.platform.startswith("win"):
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        creationflags = subprocess.CREATE_NO_WINDOW

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        startupinfo=startupinfo,
        creationflags=creationflags
    )
    prog_re = re.compile(r'(\d{1,3})%')
    for line in proc.stdout:
        m = prog_re.search(line)
        if m:
            pct = int(m.group(1))
            progressbar['value'] = pct
            percent_label.config(text=f"{pct}%")
        root.update_idletasks()
    proc.wait()
    return proc.returncode

def run_separation():
    # 1) Grab + validate
    inp = entry_file.get().strip()
    out = entry_output.get().strip()
    if not inp or not out:
        messagebox.showerror("Error", "Please select both input file and output directory.")
        start_button.config(state='normal')
        return

    # 2) Map dropdown label to Demucs source name
    label = var_stem.get()
    stem_map = {
        "Drums": "drums",
        "Bass": "bass",
        "Vocals": "vocals",
        "Guitars & other": "other"
    }
    source = stem_map.get(label)
    if not source:
        messagebox.showerror("Error", f"Unknown instrument: {label}")
        start_button.config(state='normal')
        return

    # Helper to run Demucs with progress
    def run_cmd(cmd):
        progressbar.config(mode='determinate', maximum=100, value=0)
        percent_label.config(text="0%")
        return process_with_progress(cmd)

    # 3) Build the two-stems command
    cmd = [
        "demucs",
        f"--two-stems={source}",
        "--out", out,
        inp
    ]

    # 4) Execute Demucs
    if run_cmd(cmd) != 0:
        messagebox.showerror("Error", "Stem extraction failed.")
        start_button.config(state='normal')
        return

    # 5) Move both <source>.wav and no_<source>.wav to the root of out/
    for suffix in (source, f"no_{source}"):
        pattern = os.path.join(out, "**", f"{suffix}.wav")
        matches = glob.glob(pattern, recursive=True)
        if matches:
            src = matches[0]
            dst = os.path.join(out, f"{suffix}.wav")
            try:
                shutil.move(src, dst)
            except OSError:
                pass

    # 6) Remove the empty 'htdemucs' folder that Demucs leaves behind
    htdemucs_dir = os.path.join(out, "htdemucs")
    if os.path.isdir(htdemucs_dir):
        shutil.rmtree(htdemucs_dir, ignore_errors=True)

    messagebox.showinfo(
        "Done",
        f"Extraction complete!\nCheck \"{source}.wav\" and \"no_{source}.wav\" in:\n{out}"
    )
    start_button.config(state='normal')

def on_start():
    start_button.config(state='disabled')
    threading.Thread(target=run_separation, daemon=True).start()

# ——— UI Setup ———
root = tk.Tk()
root.title("Toms Instrument Splitter")

# File picker
tk.Label(root, text="Audio File:").grid(row=0, column=0, sticky="e", padx=5, pady=5)
entry_file = tk.Entry(root, width=50)
entry_file.grid(row=0, column=1, padx=5, pady=5)
tk.Button(root, text="Browse", command=select_file).grid(row=0, column=2, padx=5)

# Output folder picker
tk.Label(root, text="Output Folder:").grid(row=1, column=0, sticky="e", padx=5, pady=5)
entry_output = tk.Entry(root, width=50)
entry_output.grid(row=1, column=1, padx=5, pady=5)
tk.Button(root, text="Browse", command=select_output_dir).grid(row=1, column=2, padx=5)

# Dropdown to select one instrument
tk.Label(root, text="Choose an instrument to separate:").grid(row=2, column=0, sticky="e", padx=5, pady=5)
instruments = ['Drums', 'Bass', 'Vocals', 'Guitars & other']
var_stem = tk.StringVar(value=instruments[0])
dropdown = ttk.Combobox(root, textvariable=var_stem, values=instruments, state='readonly', width=18)
dropdown.grid(row=2, column=1, padx=5, pady=5, sticky="w")

# Progress bar & percentage
progressbar = ttk.Progressbar(root, length=400, mode='determinate')
progressbar.grid(row=3, column=0, columnspan=2, padx=10, pady=(0,10), sticky="w")
percent_label = tk.Label(root, text="0%")
percent_label.grid(row=3, column=2, padx=5, pady=(0,10), sticky="w")

# Start button
start_button = tk.Button(root, text="Start splitting", bg="lightgrey", command=on_start)
start_button.grid(row=4, column=0, columnspan=3, pady=10)

root.mainloop()

#to compile: python -m PyInstaller --onedir -w main.py
#use Inno setup compiler program to create the installation wizard program, include the main executable and the main folder inside of "Dist" directory
#last updated May 2 2025
