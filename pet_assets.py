"""Read known local pet locations only; never download or modify assets."""
import io
import json
import struct
import sys
import subprocess
from functools import lru_cache
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
            cache / (pet + '-spritesheet-v4.png'),
            app / 'runtime' / 'pets' / (pet + '-spritesheet-v4.webp')]


@lru_cache(maxsize=1)
def desktop_archives():
    """Inspect known local app locations only; never download or scan recursively."""
    if sys.platform == 'darwin':
        return tuple(root / 'Codex.app/Contents/Resources/app.asar'
                     for root in (Path('/Applications'), Path.home() / 'Applications'))
    if os.name != 'nt':
        return ()
    try:
        result = subprocess.run(
            ['powershell.exe', '-NoProfile', '-NonInteractive', '-Command',
             "[Console]::OutputEncoding=[System.Text.Encoding]::UTF8; Get-AppxPackage -Name OpenAI.Codex | Select-Object -ExpandProperty InstallLocation"],
            capture_output=True, encoding='utf-8', timeout=10,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        if result.returncode:
            return ()
        return tuple(Path(line.strip())/'app/resources/app.asar'
                     for line in result.stdout.splitlines() if line.strip())
    except (OSError, subprocess.TimeoutExpired):
        return ()


@lru_cache(maxsize=8)
def archive_index(path, size, mtime):
    with Path(path).open('rb') as source:
        prefix = source.read(16)
        if len(prefix) != 16:
            raise ValueError('Truncated ASAR')
        _, header_size, _, json_size = struct.unpack('<4I', prefix)
        if not 0 < json_size <= 16*1024*1024 or header_size < json_size+8 or 8+header_size > size:
            raise ValueError('Invalid ASAR header')
        header = json.loads(source.read(json_size))
    entries = header['files']['webview']['files']['assets']['files']
    return 8+header_size, entries


def desktop_bytes(pet):
    for path in desktop_archives():
        try:
            stat = path.stat()
            base, entries = archive_index(str(path), stat.st_size, stat.st_mtime_ns)
            for name, entry in sorted(entries.items(), reverse=True):
                if not (name.startswith(pet+'-spritesheet-v') and name.endswith('.webp')):
                    continue
                if entry.get('unpacked') or 'link' in entry:
                    continue
                length, offset = int(entry['size']), int(entry['offset'])
                if not 0 < length <= 16*1024*1024 or offset < 0 or base+offset+length > stat.st_size:
                    continue
                with path.open('rb') as source:
                    source.seek(base+offset)
                    data = source.read(length)
                if len(data) == length:
                    yield data
        except (OSError, ValueError, KeyError, TypeError):
            continue


def has_local_asset(pet):
    for path in candidates(pet):
        try:
            if path.is_file():
                return True
        except OSError:
            pass
    return next(desktop_bytes(pet), None) is not None


def load_sheet(pet, master, app_dir=None, codex_home=None):
    import tkinter as tk
    for path in candidates(pet, app_dir, codex_home):
        try:
            if not path.is_file() or path.stat().st_size > 16 * 1024 * 1024:
                continue
            if path.suffix.lower() == '.png':
                image = tk.PhotoImage(master=master, file=str(path))
                if (image.width(), image.height()) in ((1536, 1872), (1536, 2288)):
                    return image
            else:
                # Optional dependency: missing WebP support simply uses the robot.
                from PIL import Image, ImageTk
                with Image.open(path) as source:
                    if source.size not in ((1536, 1872), (1536, 2288)):
                        continue
                    return ImageTk.PhotoImage(source.convert('RGBA'), master=master)
        except (OSError, ValueError, tk.TclError, ImportError):
            continue
    for data in desktop_bytes(pet):
        try:
            from PIL import Image, ImageTk
            with Image.open(io.BytesIO(data)) as source:
                if source.size not in ((1536, 1872), (1536, 2288)):
                    continue
                return ImageTk.PhotoImage(source.convert('RGBA'), master=master)
        except (OSError, ValueError, tk.TclError, ImportError):
            continue
    return None
