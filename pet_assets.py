"""Read known local pet locations only; never download or modify assets."""
import os
from pathlib import Path


def candidates(pet, app_dir=None, codex_home=None):
    app = Path(app_dir) if app_dir is not None else Path(__file__).resolve().parent
    home = Path(codex_home) if codex_home is not None else Path(
        os.environ.get('CODEX_HOME', Path.home() / '.codex'))
    # Official Codex CLI v1 cache layout. Do not recursively scan personal folders.
    cache = home / 'cache' / 'tui-pets' / 'v1' / 'assets'
    return [app / 'assets' / (pet + '.png'),
            cache / (pet + '-spritesheet-v4.webp'),
            cache / (pet + '-spritesheet-v4.png')]


def load_sheet(pet, master, app_dir=None, codex_home=None):
    import tkinter as tk
    for path in candidates(pet, app_dir, codex_home):
        try:
            if not path.is_file() or path.stat().st_size > 16 * 1024 * 1024:
                continue
            if path.suffix.lower() == '.png':
                image = tk.PhotoImage(master=master, file=str(path))
                if (image.width(), image.height()) == (1536, 1872):
                    return image
            else:
                # Optional dependency: missing WebP support simply uses the robot.
                from PIL import Image, ImageTk
                with Image.open(path) as source:
                    if source.size != (1536, 1872):
                        continue
                    return ImageTk.PhotoImage(source.convert('RGBA'), master=master)
        except (OSError, ValueError, tk.TclError, ImportError):
            continue
    return None
