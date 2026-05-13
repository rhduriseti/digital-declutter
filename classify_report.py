"""
Quick classification report — scans a folder and prints how each file was classified.

Usage:
    python3 classify_report.py /path/to/your/folder
"""
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

if len(sys.argv) < 2:
    print("Usage: python3 classify_report.py /path/to/folder")
    sys.exit(1)

folder = Path(sys.argv[1])
if not folder.exists():
    print(f"Folder not found: {folder}")
    sys.exit(1)

from declutter_bot.tools.scan_folder import scan_folder
from declutter_bot.tools.categorize_files import categorize_files

print(f"\nScanning: {folder}")
print("─" * 70)

files = scan_folder(folder)
if not files:
    print("No files found.")
    sys.exit(0)

print(f"Found {len(files)} files — classifying...\n")

index = {
    str(f.path): {
        "path": str(f.path),
        "name": f.name,
        "extension": f.extension,
        "size_bytes": f.size_bytes,
        "created_at": str(f.created_at),
        "modified_at": str(f.modified_at),
        "source": f.source,
        "category": None,
        "duplicate_of": None,
    }
    for f in files
}

def progress(done, total):
    bar_len = 30
    filled = int(bar_len * done / total) if total else 0
    bar = "█" * filled + "░" * (bar_len - filled)
    print(f"  [{bar}] {done}/{total}", end="\r", flush=True)

result = categorize_files(index, on_progress=progress)
print()  # newline after progress bar

# Print table
col_file   = 40
col_cat    = 18
col_group  = 8
col_conf   = 10
col_also   = 16

header = (
    f"{'File':<{col_file}} {'Category':<{col_cat}} {'Group':<{col_group}} {'Confidence':<{col_conf}} {'Also could be':<{col_also}}"
)
print(header)
print("─" * len(header))

GROUP_LABELS = {
    "A":         "A (metadata)",
    "B":         "B (content) ",
    "C":         "C (Gemma)   ",
    "C_visual":  "C (vision)  ",
    "extension": "ext         ",
    "fallback":  "—           ",
}

for path, entry in sorted(result.items(), key=lambda x: x[1].get("category", "")):
    name = Path(path).name
    name = name[:col_file - 1] if len(name) >= col_file else name

    category = entry.get("category", "—")
    group_raw = entry.get("classification_group", "—")
    group = GROUP_LABELS.get(group_raw, group_raw)
    confidence = entry.get("confidence_score")
    conf_str = f"{confidence:.0%}" if confidence else "—"
    also_raw = entry.get("also_could_be")
    also = also_raw if also_raw and also_raw != category else "—"

    print(f"{name:<{col_file}} {category:<{col_cat}} {group:<{col_group}} {conf_str:<{col_conf}} {also:<{col_also}}")

print("─" * len(header))
print(f"\nTotal: {len(result)} files\n")

# Summary by category
from collections import Counter
cats = Counter(e.get("category") for e in result.values())
print("By category:")
for cat, count in cats.most_common():
    print(f"  {cat:<20} {count} file{'s' if count != 1 else ''}")

# Summary by group
groups = Counter(e.get("classification_group") for e in result.values())
print("\nBy classification group:")
for g, count in groups.most_common():
    label = GROUP_LABELS.get(g, g)
    print(f"  {label:<20} {count} file{'s' if count != 1 else ''}")

print()
