"""The todo list, from todo.md in this repo. Edit that file (on GitHub or here) to change it."""

from pathlib import Path

TODO_FILE = Path(__file__).parent / "todo.md"


def read():
    """Open items: lines like '- Buy milk' or '- [ ] Buy milk'. Done items ('- [x] ...') are left out."""
    items = []
    for line in TODO_FILE.read_text().splitlines():
        line = line.strip()
        if line.startswith(("- ", "* ")) and not line[2:].lower().startswith("[x]"):
            items.append(line[2:].removeprefix("[ ]").strip())
    return items
