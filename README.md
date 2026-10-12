# file-organizer

A small Python script that tidies up a folder by moving each file into a subfolder named after its extension.

```
Downloads/                 Downloads/
├── report.pdf             ├── pdf/
├── photo.JPG       →      │   └── report.pdf
└── notes.txt              ├── jpg/
                           │   └── photo.JPG
                           └── txt/
                               └── notes.txt
```

## Requirements

Python 3.6+ (standard library only, no dependencies).

## Usage

Organize a specific folder:

```bash
python organize_files.py path/to/folder
```

Or copy `organize_files.py` into the folder you want to organize and run it with no arguments:

```bash
python organize_files.py
```

## Behavior

- Extensions are lowercased, so `photo.JPG` and `photo.jpg` both go into `jpg/`.
- Files without an extension (and hidden files like `.gitignore`) are left in place.
- Subfolders are not touched; only files directly inside the folder are moved.
- If a file with the same name already exists in the destination, it is skipped, never overwritten.
- The script never moves itself.

> **Note:** Running it with no arguments inside this repository will sort the repository's own files (e.g. `README.md` → `md/`). Pass a folder path instead.
