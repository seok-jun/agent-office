"""Platform defaults shared by Tk widgets and canvas text."""
import sys
import tkinter as tk
from tkinter import ttk

UI_FONT = 'Apple SD Gothic Neo' if sys.platform == 'darwin' else 'Malgun Gothic'
MONO_FONT = 'Menlo' if sys.platform == 'darwin' else 'Consolas'


def _mac_control(parent, kind, options):
    """Use drawn controls: Aqua native buttons override custom dark colors."""
    style = ttk.Style(parent)
    if style.theme_use() != 'clam':
        style.theme_use('clam')
    background = options.pop('bg', '#2b394a')
    foreground = options.pop('fg', '#e9eee7')
    active = options.pop('activebackground', '#3b4a5c')
    active_fg = options.pop('activeforeground', foreground)
    selected = options.pop('selectcolor', background)
    font = options.pop('font', (UI_FONT, 10))
    padding = (options.pop('padx', 10), options.pop('pady', 6))
    anchor = options.pop('anchor', 'center')
    options.pop('relief', None)
    options.pop('bd', None)
    # Reuse styles for identical controls, including rebuilt session cards.
    settings = (background, foreground, active, active_fg, selected, font, padding, anchor, kind)
    name = 'Office' + str(abs(hash(settings))) + '.' + kind
    style.configure(name, background=background, foreground=foreground, font=font,
                    padding=padding, anchor=anchor, borderwidth=0,
                    lightcolor=background, darkcolor=background,
                    indicatorbackground=selected, indicatorforeground=foreground)
    style.map(name,
              background=[('disabled', background), ('pressed', active), ('active', active)],
              foreground=[('disabled', '#8996ab'), ('pressed', active_fg), ('active', active_fg)],
              indicatorbackground=[('selected', '#93dfb1'), ('!selected', selected)])
    cls = ttk.Button if kind == 'TButton' else ttk.Checkbutton
    return cls(parent, style=name, **options)


def Button(parent, **options):
    if sys.platform == 'darwin':
        return _mac_control(parent, 'TButton', options)
    return tk.Button(parent, **options)


def Checkbutton(parent, **options):
    if sys.platform == 'darwin':
        return _mac_control(parent, 'TCheckbutton', options)
    return tk.Checkbutton(parent, **options)


def wheel_units(delta, windowing_system):
    """Aqua sends small deltas; Windows sends multiples of 120."""
    if not delta:
        return 0
    if windowing_system == 'aqua':
        return -int(delta) if abs(delta) >= 1 else (-1 if delta > 0 else 1)
    return -int(delta / 120)
