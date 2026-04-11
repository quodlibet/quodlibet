Quod Libet - Claude Code Project Guide
=======================================

Hard Rules
----------

1. **Write idiomatic GTK4 code.** Never add shims, monkey-patches, or compatibility wrappers that make GTK4 look like GTK3. Never maintain dual-use code that works on both GTK3 and GTK4. Always update the call site to use the native GTK4 API. If a shim already exists in `quodlibet/_init.py`, the fix is to remove usage of it, not to add more.
2. **Tests**: Write concise tests. Use descriptive names instead of docstrings. Reuse existing fixtures; extract new fixtures only when genuinely shared. Don't over-mock.
3. **No lazy imports.** Put all imports at the top of the file.
  Do not use inline / deferred imports unless there is a real circular dependency that cannot be resolved otherwise.


Project Overview
----------------

Quod Libet is a GTK-based music player/library manager written in Python. Currently migrating from GTK3 to GTK4 on the `gtk4` branch.

### Key Directories
- `quodlibet/` - Main application source
  - `qltk/` - UI widget toolkit layer (most GTK migration work here)
  - `browsers/` - Browser views (albums, playlists, filesystem, etc.)
  - `ext/` - Extension plugins
  - `plugins/` - Plugin system
  - `player/` - Playback engine (GStreamer)
  - `library/` - Music library management
  - `formats/` - Audio format handlers
- `tests/` - Test suite (pytest)


Environment
-----------

- **Nix flake** provides the dev environment (`nix develop -c -- <command>`)
- Python 3.12 (from Nix), NOT system Python
- If venv breaks, recreate: `nix develop -c -- bash -c 'rm -rf .venv && poetry env use python3.12 && poetry install --with dev -E plugins'`
- GTK4 requires `LD_LIBRARY_PATH` to include pango, fontconfig, gtk4 libs (handled by flake.nix)


Commands (always prefix with `nix develop -c --`)
--------------------------------------------------

- **Format**: `ruff format quodlibet tests`
- **Lint**: `ruff check --fix quodlibet tests`
- **Type check**: `mypy quodlibet tests`
- **Test**: `pytest tests/ -x --tb=short`
- **Test subset**: `pytest tests/ -x -k "pattern"`


GTK4 Migration (Current Branch: gtk4)
--------------------------------------

- **Status**: 98.7% tests passing (4606/4668). App starts and runs. See `GTK4_MIGRATION_STATUS.md` for full details.
- **Compatibility shims**: `quodlibet/_init.py` contains temporary GTK3→GTK4 shims. These are TECHNICAL DEBT - prefer updating call sites to use proper GTK4 APIs.
- **Helper**: `quodlibet/qltk/__init__.py` has `get_children()` for iterating GTK4 widget children
- **Remaining high-priority work**: Drag-and-drop rewrite, UIManager→Gio.Menu, keyboard accelerator restoration, event controller migration
- Use `/gtk4` skill for idiomatic GTK4 migration guidance
- Use `/lint` skill to run formatting/linting/type checks
- Official guide: https://docs.gtk.org/gtk4/migrating-3to4.html


Code Style
----------

- Python 3.10+, GPL-2.0-or-later
- Ruff for formatting and linting (config in pyproject.toml)
- Don't add excessive migration comments - keep code clean
- Mark incomplete migrations with `# TODO GTK4:` comments
