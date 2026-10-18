Start a focused GTK4 migration work session.

## Instructions

1. **Check current status** (use Grep tool, not bash):
   - Count TODO markers: `# TODO GTK4` in quodlibet/
   - Report which files have the most TODOs

2. **Show priority queue**:
   - Queue DnD: `qltk/queue.py` (highest impact)
   - Songlist DnD: `qltk/songlist.py` (essential)
   - Browser DnD: `browsers/*/main.py` (do one at a time)

3. **Ask user** which task to tackle using AskUserQuestion with options:
   - "Queue DnD (queue.py)"
   - "Songlist DnD (songlist.py)"
   - "Pick a browser file"
   - "Something else"

4. **Reference files**:
   - Status doc: `GTK4_MIGRATION_STATUS.md`
   - Use `/gtk4` skill for idiomatic API patterns