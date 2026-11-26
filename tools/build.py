#!/usr/bin/env python3
"""Package the add-on into download/pathtofluent_waypoint.ankiaddon.   Run:  python3 tools/build.py

The file is kept in the repository so anyone can download and install it without building.
It is built the same way every time (fixed dates inside), so it only changes when the add-on does.
"""
import os, zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src, out = os.path.join(ROOT, "addon"), os.path.join(ROOT, "download", "pathtofluent_waypoint.ankiaddon")
os.makedirs(os.path.dirname(out), exist_ok=True)
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    for name in sorted(os.listdir(src)):
        if name.endswith((".py", ".json", ".md")):
            info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type, info.external_attr = zipfile.ZIP_DEFLATED, 0o644 << 16
            with open(os.path.join(src, name), "rb") as f:
                z.writestr(info, f.read())
print("built", os.path.relpath(out, ROOT))
