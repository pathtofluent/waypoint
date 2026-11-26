#!/usr/bin/env python3
"""
Copy subtitle files into Waypoint's subtitle bank without opening Anki.
(Inside Anki, use Tools > PathToFluent Waypoint > Add subtitles to the bank.)

Run:   python3 tools/gather_subtitles.py
You choose a folder. Every subtitle file inside it, at any depth, is checked, and the ones in
your language are COPIED into <Anki data folder>/<profile>/waypoint/subtitle-bank/<folder name>/...
Originals are never moved or changed, and nothing already in the bank is overwritten.

Options:
  python3 tools/gather_subtitles.py /path/to/folder     skip the folder chooser
  --lang fr        language to keep (es, en, fr, pt, it, de)            default: es
  --all            keep every language
  --ext srt,vtt    file types to look for                               default: srt,vtt,ass,ssa
  --dest FOLDER    copy somewhere other than the Waypoint subtitle bank
  --dry-run        show what would happen without copying anything
"""
import argparse, os, subprocess, sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "addon"))
import gather


def anki_base():
    home = os.path.expanduser("~")
    if sys.platform == "darwin":
        return os.path.join(home, "Library", "Application Support", "Anki2")
    if os.name == "nt":
        return os.path.join(os.environ.get("APPDATA", os.path.join(home, "AppData", "Roaming")), "Anki2")
    return os.path.join(os.environ.get("XDG_DATA_HOME", os.path.join(home, ".local", "share")), "Anki2")


def find_bank():
    base = anki_base()
    if not os.path.isdir(base):
        sys.exit("Couldn't find Anki's data folder at:\n  %s\nUse --dest to say where the files should go." % base)
    profiles = sorted(d for d in os.listdir(base) if os.path.isfile(os.path.join(base, d, "collection.anki2")))
    if not profiles:
        sys.exit("No Anki profile found in %s. Use --dest to say where the files should go." % base)
    profile = profiles[0]
    if len(profiles) > 1:
        print("Which Anki profile?")
        for i, p in enumerate(profiles, 1):
            print("  %d. %s" % (i, p))
        profile = profiles[int(input("Number [1]: ").strip() or "1") - 1]
    return os.path.join(base, profile, "waypoint", "subtitle-bank")


def choose_folder():
    if sys.platform == "darwin":
        script = 'POSIX path of (choose folder with prompt "Choose the folder that holds your subtitle files")'
        r = subprocess.run(["osascript", "-e", script], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.decode("utf-8").strip()
        sys.exit("No folder chosen.")
    try:
        import tkinter
        from tkinter import filedialog
        root = tkinter.Tk()
        root.withdraw()
        path = filedialog.askdirectory(title="Choose the folder that holds your subtitle files")
        root.destroy()
        if path:
            return path
        sys.exit("No folder chosen.")
    except Exception:
        return input("Folder that holds your subtitle files: ").strip().strip('"')


def main():
    ap = argparse.ArgumentParser(description="Copy subtitle files into Waypoint's subtitle bank")
    ap.add_argument("folder", nargs="?")
    ap.add_argument("--lang", default="es", choices=sorted(gather.WORDS))
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--ext", default="srt,vtt,ass,ssa")
    ap.add_argument("--dest")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    source = os.path.abspath(os.path.expanduser(args.folder or choose_folder()))
    if not os.path.isdir(source):
        sys.exit("Not a folder: %s" % source)
    bank = os.path.abspath(os.path.expanduser(args.dest)) if args.dest else find_bank()
    if gather.inside(source, bank):
        sys.exit("That folder is already inside the subtitle bank.")
    print("Searching %s ..." % source)
    plan = gather.scan(source, bank, args.lang, [e for e in args.ext.split(",") if e.strip()], args.all)
    print("\n".join(gather.summary(plan, args.lang, args.all)))
    if args.dry_run or not plan["to_copy"]:
        return
    copied, failed = gather.copy(plan)
    print("\nCopied %d into:\n  %s" % (copied, plan["target"]))
    if failed:
        print("%d could not be copied." % len(failed))
    print("Next: in Anki, Tools > PathToFluent Waypoint > Reconcile cards.")


if __name__ == "__main__":
    main()
