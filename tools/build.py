#!/usr/bin/env python3
"""Package the add-on into dist/pathtofluent_waypoint.ankiaddon.   Run:  python3 tools/build.py"""
import os, zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src, out = os.path.join(ROOT, "addon"), os.path.join(ROOT, "dist", "pathtofluent_waypoint.ankiaddon")
os.makedirs(os.path.dirname(out), exist_ok=True)
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    for name in sorted(os.listdir(src)):
        if name.endswith((".py", ".json", ".md")):
            z.write(os.path.join(src, name), name)
print("built", os.path.relpath(out, ROOT))
