"""
Settings window — Claude Dark theme.
Launched as subprocess by menubar_app.py. Reads/writes data/config.json.
"""
import tkinter as tk
from tkinter import messagebox
import json
import os

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "config.json")

# ── Claude Dark Palette ────────────────────────────────────────
BG          = "#1E1B18"   # warm charcoal
SURFACE     = "#272320"   # card / row background
INPUT_BG    = "#201D1A"   # entry field
BORDER      = "#3D3830"   # subtle divider
ACCENT      = "#C96B3B"   # Claude orange
ACCENT_HOV  = "#A8552D"   # hover darken
TEXT        = "#F0EDE8"   # warm white
SUBTEXT     = "#9E9A94"   # muted labels
UNIT_TEXT   = "#6B6560"   # unit (g / mg / hrs)
SECT_TEXT   = "#C96B3B"   # section header colour (matches accent)
BTN_BG      = "#2C2825"   # secondary button bg
BTN_HOV     = "#38332E"   # secondary hover

FONT_HEAD   = ("Helvetica Neue", 17, "bold")
FONT_SECT   = ("Helvetica Neue", 9,  "bold")
FONT_LABEL  = ("Helvetica Neue", 13)
FONT_ENTRY  = ("Helvetica Neue", 13)
FONT_UNIT   = ("Helvetica Neue", 11)
FONT_BTN    = ("Helvetica Neue", 12, "bold")
FONT_BTN_SM = ("Helvetica Neue", 11)

DEFAULTS = {
    "calorie_goal":           2000,
    "protein_goal":           150,
    "fat_goal":               65,
    "carbs_goal":             250,
    "sugar_goal":             50,
    "fiber_goal":             25,
    "sodium_goal":            2300,
    "reminder_interval_hours": 4.0,
    "reminders_enabled":      True,
}

# Groups: (section_title, [(label, key, unit, is_float), ...])
SECTIONS = [
    ("ENERGY & CORE MACROS", [
        ("Daily Calories",  "calorie_goal",  "kcal", False),
        ("Protein",         "protein_goal",  "g",    False),
        ("Fat",             "fat_goal",      "g",    False),
        ("Carbs",           "carbs_goal",    "g",    False),
    ]),
    ("ADDITIONAL NUTRIENTS", [
        ("Sugar",           "sugar_goal",    "g",    False),
        ("Fiber",           "fiber_goal",    "g",    False),
        ("Sodium",          "sodium_goal",   "mg",   False),
    ]),
    ("NOTIFICATIONS", [
        ("Remind me every", "reminder_interval_hours", "hours", True),
    ]),
]


def load_config() -> dict:
    config = dict(DEFAULTS)
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH) as f:
                config.update(json.load(f))
        except Exception:
            pass
    return config


def save_config(data: dict):
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(data, f, indent=2)


def make_entry(parent, var) -> tk.Entry:
    """Styled dark entry field."""
    e = tk.Entry(
        parent,
        textvariable=var,
        width=8,
        bg=INPUT_BG,
        fg=TEXT,
        insertbackground=ACCENT,
        relief="flat",
        borderwidth=0,
        highlightthickness=1,
        highlightbackground=BORDER,
        highlightcolor=ACCENT,
        font=FONT_ENTRY,
        justify="right",
    )
    return e


def make_btn(parent, text, command, primary=False) -> tk.Button:
    bg  = ACCENT    if primary else BTN_BG
    hov = ACCENT_HOV if primary else BTN_HOV
    fg  = "#FFFFFF" if primary else TEXT
    font = FONT_BTN if primary else FONT_BTN_SM

    b = tk.Button(
        parent, text=text, command=command,
        bg=bg, fg=fg, activebackground=hov, activeforeground=fg,
        relief="flat", borderwidth=0, padx=16, pady=7,
        font=font, cursor="hand2",
    )
    b.bind("<Enter>", lambda _: b.config(bg=hov))
    b.bind("<Leave>", lambda _: b.config(bg=bg))
    return b


def build_window():
    config = load_config()

    root = tk.Tk()
    root.title("Settings")
    root.resizable(False, False)
    root.configure(bg=BG)

    # ── Header ────────────────────────────────────────────────
    header = tk.Frame(root, bg=BG)
    header.pack(fill="x", padx=0, pady=0)

    # Left orange accent strip
    tk.Frame(header, bg=ACCENT, width=4).pack(side="left", fill="y")

    header_inner = tk.Frame(header, bg=BG)
    header_inner.pack(side="left", fill="x", expand=True, padx=(16, 20), pady=(20, 16))

    tk.Label(header_inner, text="Goals & Reminders",
             bg=BG, fg=TEXT, font=FONT_HEAD).pack(anchor="w")
    tk.Label(header_inner, text="Nutrition targets and notification preferences",
             bg=BG, fg=SUBTEXT, font=FONT_UNIT).pack(anchor="w", pady=(2, 0))

    # ── Divider ───────────────────────────────────────────────
    tk.Frame(root, bg=BORDER, height=1).pack(fill="x")

    # ── Scrollable content area ───────────────────────────────
    content = tk.Frame(root, bg=BG)
    content.pack(fill="both", expand=True, padx=24, pady=(16, 0))

    entries: dict[str, tk.Variable] = {}

    for sect_title, fields in SECTIONS:
        # Section header
        sect_frame = tk.Frame(content, bg=BG)
        sect_frame.pack(fill="x", pady=(10, 4))
        tk.Label(sect_frame, text=sect_title,
                 bg=BG, fg=SECT_TEXT, font=FONT_SECT).pack(side="left")
        tk.Frame(sect_frame, bg=BORDER, height=1).pack(
            side="left", fill="x", expand=True, padx=(10, 0), pady=(0, 2)
        )

        # Field rows
        for label_text, key, unit, is_float in fields:
            val = config.get(key, DEFAULTS[key])
            var = tk.DoubleVar(value=float(val)) if is_float else tk.IntVar(value=int(val))
            entries[key] = var

            row = tk.Frame(content, bg=SURFACE)
            row.pack(fill="x", pady=2)

            tk.Label(row, text=label_text, bg=SURFACE, fg=TEXT,
                     font=FONT_LABEL, anchor="w", width=18).pack(
                side="left", padx=(14, 8), pady=9
            )

            entry = make_entry(row, var)
            entry.pack(side="left", pady=9)

            tk.Label(row, text=unit, bg=SURFACE, fg=UNIT_TEXT,
                     font=FONT_UNIT).pack(side="left", padx=(8, 14), pady=9)

    # ── Reminders toggle ──────────────────────────────────────
    tk.Frame(content, bg=BORDER, height=1).pack(fill="x", pady=(14, 6))

    toggle_row = tk.Frame(content, bg=SURFACE)
    toggle_row.pack(fill="x", pady=2)

    reminders_var = tk.BooleanVar(value=bool(config.get("reminders_enabled", True)))
    cb = tk.Checkbutton(
        toggle_row,
        text="  Enable meal reminder notifications",
        variable=reminders_var,
        bg=SURFACE, fg=TEXT, selectcolor=BG,
        activebackground=SURFACE, activeforeground=TEXT,
        font=FONT_LABEL,
        borderwidth=0, relief="flat",
        cursor="hand2",
    )
    cb.pack(anchor="w", padx=10, pady=9)

    # ── Footer divider ────────────────────────────────────────
    tk.Frame(root, bg=BORDER, height=1).pack(fill="x", pady=(14, 0))

    # ── Button row ────────────────────────────────────────────
    btn_row = tk.Frame(root, bg=BG)
    btn_row.pack(fill="x", padx=24, pady=16)

    def on_reset():
        for key, var in entries.items():
            var.set(DEFAULTS[key])
        reminders_var.set(DEFAULTS["reminders_enabled"])

    def on_save():
        try:
            new_config = load_config()
            for key, var in entries.items():
                new_config[key] = var.get()
            new_config["reminders_enabled"] = reminders_var.get()
            save_config(new_config)
            messagebox.showinfo(
                "Saved",
                "Settings saved.\nChanges apply on next menu refresh.",
                parent=root,
            )
            root.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"Could not save:\n{e}", parent=root)

    make_btn(btn_row, "Reset to Defaults", on_reset).pack(side="left")
    make_btn(btn_row, "Cancel", root.destroy).pack(side="left", padx=(8, 0))
    make_btn(btn_row, "Save", on_save, primary=True).pack(side="right")

    # ── Center on screen ──────────────────────────────────────
    root.update_idletasks()
    w, h = root.winfo_reqwidth(), root.winfo_reqheight()
    sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
    root.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")

    root.lift()
    root.attributes("-topmost", True)
    root.after(500, lambda: root.attributes("-topmost", False))
    root.focus_force()

    root.mainloop()


if __name__ == "__main__":
    build_window()
