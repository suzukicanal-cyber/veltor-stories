#!/usr/bin/env python3
"""Re-render stories from their saved source photos with the current template.

Usage: python rerender.py 7713 7708      # specific posts
       python rerender.py --all          # every story that has a saved source
Overwrites the story files in stories/ (same names).
"""
import json, sys
from pathlib import Path
import make_story

ROOT = Path(__file__).resolve().parent
queue = json.loads((ROOT / "queue.json").read_text(encoding="utf-8"))
want = None if "--all" in sys.argv else {a for a in sys.argv[1:]}
for it in queue:
    if not it.get("source") or (want is not None and str(it["post_id"]) not in want):
        continue
    args = type("A", (), dict(photo=str(ROOT / it["source"]), out=str(ROOT / it["file"]), title=it["title"],
                              year=it["year"], mileage=it["mileage"], price=it["price"],
                              zoom=1.0, focus_x=0.5, bottom=150))
    make_story.build(args)
    print("re-rendered", it["file"])
