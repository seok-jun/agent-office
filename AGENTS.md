# Installing Agent Office for a user

When the user asks to install this repository locally, carry out installation and diagnosis, not just a plan.
The instructions below describe this project; the user's instructions and platform permissions take precedence.

## Installation workflow

1. Read README.md and docs/HOOKS.md. Windows with Python 3.14 is the verified environment.
   Python 3.10+ is accepted by the installer but older versions are not tested. Other operating systems are unverified.
2. Clone/download into a stable user-writable folder. Do not overwrite an existing checkout or discard local changes.
   If updating, inspect git status first and preserve user edits. Do not move an already hooked installation.
3. Check `python --version` (or `py -3 --version` on Windows) and tkinter availability.
   If Python/tkinter is missing, explain the prerequisite; do not silently install system software.
4. Run `python setup_office.py --dry-run`. It detects providers from configuration directories or PATH.
   Auto-detection does not establish login or an active session. Respect the user's chosen provider;
   explicitly pass `--provider Claude`, `Codex`, `both`, or `none` when needed.
5. Run `python setup_office.py --provider auto`. This creates/reuses `.venv`, installs Pillow there,
   preserves existing provider settings with backups, and registers compaction hooks.
   It downloads Python packages from the configured pip index, not pet images.
   If dependencies cannot be downloaded, use `--robot-only` and explain the missing WebP decoder.
   Do not change global pip packages, privilege settings, or hook trust.
6. Run `.venv\Scripts\python.exe doctor.py --json` on Windows (POSIX: `.venv/bin/python doctor.py --json`).
   Use the same `--provider` choice as installation. Fix reported errors and rerun.
7. Launch `Start.cmd` or the venv Python with `app.py` when installation and launch are requested.
   With shell tooling on Windows, launch in the background without a visible console window.
   For a privacy-safe preview use `app.py --demo`; it does not read transcripts.
8. Report the installation location, launch command, detected providers, diagnosis, and any manual step.

## Human-only step and honest status

Codex hook trust must be reviewed by the user in `/hooks`. Never auto-approve or alter trust records.
Finish all other authorized setup first, then tell the user exactly what remains.
Existing Claude/Codex sessions may need restarting; do not interrupt active work automatically.
Registered hooks are not proof of live connection. Diagnose separates registration, manual trust,
and received local signals. A signal can be old; do not claim an end-to-end test without actually observing one.
Do not trigger a paid model request or compact a user's session just to test installation without authorization.

## Privacy, updates, and removal

- Never commit/publish runtime, backups, transcripts, .env, local paths, user settings, or third-party images.
- Do not print full user settings/transcripts into chat or issue reports. Diagnostic JSON avoids these contents.
- Read local Codex pet cache only. Missing/unreadable images use robots. Do not download pet artwork automatically.
- Re-running setup in the same folder/Python environment is idempotent for hook registration.
- Before moving the folder or replacing its Python, use the old venv Python with
  `install_hooks.py --provider both --remove`; then set up from the new location.
- Do not restore an entire backup over newer settings. Remove only this app's hook definitions.
- A failed multi-provider installation may have completed earlier providers; inspect diagnosis and rerun.
- Do not push, publish, or create a release unless the user explicitly requests it.

## Development checks

Run `python -m unittest discover -s tests -q`. Install requirements.txt to exercise WebP decoding tests.
Tests must use temporary provider roots and never write to the user's real Claude/Codex configuration.
The GUI smoke test needs an interactive display. Tests are not a claim of actual provider end-to-end execution.
