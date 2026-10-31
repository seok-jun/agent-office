"""Explicit user-requested downloads from the Codex CLI's public pet CDN."""
import io
import os
import ssl
from pathlib import Path
import tempfile
from urllib.request import Request, urlopen

BASE_URL = 'https://persistent.oaistatic.com/codex/pets/v1'
PETS = ('codex', 'dewey', 'fireball', 'rocky', 'seedy', 'stacky', 'bsod', 'null-signal')
MAX_BYTES = 4 * 1024 * 1024


def validate(data):
    from PIL import Image
    if len(data) > MAX_BYTES:
        raise ValueError('Image exceeds 4 MiB')
    with Image.open(io.BytesIO(data)) as image:
        if image.format != 'WEBP' or image.size != (1536, 1872):
            raise ValueError('Unexpected pet image format or dimensions')
        image.load()


def download_pet(pet, directory=None):
    if pet not in PETS:
        raise ValueError('Unknown CLI pet')
    # Fail before network access if WebP decoding is unavailable.
    from PIL import Image
    directory = Path(directory) if directory is not None else Path(__file__).resolve().parent/'runtime/pets'
    name = pet + '-spritesheet-v4.webp'
    destination = directory/name
    try:
        if destination.stat().st_size <= MAX_BYTES:
            validate(destination.read_bytes())
            return 'cached'
    except (OSError, ValueError):
        pass
    import certifi
    context = ssl.create_default_context()
    context.load_verify_locations(cafile=certifi.where())
    request = Request(BASE_URL + '/' + name,
                      headers={'User-Agent': 'AgentOffice/1.0', 'Accept': 'image/webp'})
    with urlopen(request, timeout=30, context=context) as response:
        data = response.read(MAX_BYTES + 1)
    validate(data)
    directory.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=directory, prefix='pet-', suffix='.tmp', delete=False) as output:
            temporary = Path(output.name)
            output.write(data)
        os.replace(temporary, destination)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return 'downloaded'
