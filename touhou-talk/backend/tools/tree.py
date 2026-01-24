import os

EXCLUDE_DIRS = {"__pycache__", ".git", ".venv", "venv", ".vscode", ".idea"}
EXCLUDE_FILES = {".pyc"}

def should_exclude(name):
    if name in EXCLUDE_DIRS:
        return True
    return any(name.endswith(ext) for ext in EXCLUDE_FILES)

def build_tree(path, prefix=""):
    entries = sorted(e for e in os.listdir(path) if not should_exclude(e))
    for i, entry in enumerate(entries):
        connector = "└── " if i == len(entries) - 1 else "├── "
        print(prefix + connector + entry)
        full = os.path.join(path, entry)
        if os.path.isdir(full):
            extension = "    " if i == len(entries) - 1 else "│   "
            build_tree(full, prefix + extension)

if __name__ == "__main__":
    build_tree(".")
