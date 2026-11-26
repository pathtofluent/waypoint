"""PathToFluent Waypoint - daily numbers. Pure Python, no Anki imports.

When a folder is chosen in Settings, Waypoint keeps one line of numbers per day in
STATS_FILE there, so another tool (PathToFluent Logbook, a spreadsheet, a script) can
show progress over time. Running again on the same day replaces that day's line.
"""
import datetime, json, os

STATS_FILE, UNREADABLE = "waypoint_stats.json", "waypoint_stats.unreadable.json"
APP, FORMAT, KEEP_DAYS = "PathToFluent Waypoint", 1, 3660
NUMBERS = ("known_words", "learning_words", "known_sentences", "cards_studied", "cards_ready", "cards_waiting")


def day_line(stats, cards_studied, language, today):
    """One day's line from the numbers of a run."""
    line = {"date": today.isoformat(), "language": language,
            "known_words": stats.get("known_words", 0), "learning_words": stats.get("learning_words", 0),
            "known_sentences": stats.get("known_sentences", 0), "cards_studied": cards_studied,
            "cards_ready": stats.get("ready", 0), "cards_waiting": stats.get("held", 0)}
    return {k: (int(v) if k in NUMBERS else v) for k, v in line.items()}


def merge(days, line):
    """The list of days with `line` put in: it replaces the same date and language, the rest stay."""
    same = lambda d: d.get("date") == line["date"] and d.get("language") == line["language"]
    kept = [d for d in days if isinstance(d, dict) and d.get("date") and not same(d)]
    kept.append(line)
    kept.sort(key=lambda d: (d["date"], d.get("language") or ""))
    return kept[-KEEP_DAYS:]


def read(path):
    """The days already in the file. A missing file is no days; a damaged one raises ValueError."""
    if not os.path.isfile(path):
        return []
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        days = data["days"]
        if not isinstance(days, list):
            raise ValueError("no list of days")
        for d in days:
            datetime.date.fromisoformat(d["date"])
    except (OSError, ValueError, KeyError, TypeError) as e:
        raise ValueError("%s: %s" % (type(e).__name__, e))
    return days


def write(folder, line):
    """Put today's line into the file in `folder`. A damaged file is set aside, never overwritten."""
    path, note = os.path.join(folder, STATS_FILE), ""
    try:
        days = read(path)
    except ValueError:
        os.replace(path, os.path.join(folder, UNREADABLE))
        days, note = [], "The old numbers file couldn't be read. It was renamed to %s and a new one started." % UNREADABLE
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"app": APP, "format": FORMAT, "days": merge(days, line)}, f, ensure_ascii=False, indent=1)
        f.write("\n")
    os.replace(tmp, path)
    return note
