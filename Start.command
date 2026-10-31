#!/bin/sh
# Resolve relative to this launcher, including when opened from Finder.
cd "$(dirname "$0")" || exit 1

if [ -x ".venv/bin/python" ]; then
    office_python=".venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
    office_python="python3"
else
    printf '%s\n' 'Python 3.10+ with tkinter is required. See README.md.'
    exit 1
fi

if ! "$office_python" -c 'import sys, tkinter; assert sys.version_info >= (3, 10)' ; then
    printf '%s\n' 'Install Python 3.10+ with tkinter, then run python3 setup_office.py.'
    exit 1
fi

exec "$office_python" app.py "$@"
