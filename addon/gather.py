"""PathToFluent Waypoint - gather subtitle files into the subtitle bank. Pure Python, no Anki imports."""
import os, re, shutil

# A few very common words per language: enough to tell subtitle files apart.
WORDS = {
    "es": "que de no la el y es en lo un por qué me una te los se con para mi está si bien pero yo eso las su tu aquí del al como le más esto ya todo esta vamos muy hay ahora algo estoy tengo nos cuando nada él así sí quiero",
    "en": "the you i to a and it of that is in what we me this he for my on have your do no don't are be not was know with but all so just there here they like get she go if right out about up at him oh yeah",
    "fr": "je de est pas le vous la tu que un il et à ne les ce en on ça une ai pour des moi qui nous mais y me dans du bien elle si tout plus non mon suis te au avec oui va toi fait ils as être faire se comme",
    "pt": "que não o de a é você e eu um para se me uma está com do por te os bem em ele isso mas da como no sim mais meu aqui muito foi na estou vamos ela vai isto já minha tem ser ao quando eles nos",
    "it": "non che di e la il un a è per mi sono ho ma lo ha le si ti cosa una con no i da se come io ci questo qui bene hai sei del tu sì me più al mio c'è va lei solo te era gli tutto della",
    "de": "ich sie das ist du nicht die es und der was wir zu er ein in mir mit ja wie den auf mich dass so hier eine wenn hat sind von dich war haben für an habe da nein bin noch dir uns sich nur einen",
}
LANGUAGES = {"es": "Spanish", "en": "English", "fr": "French", "pt": "Portuguese", "it": "Italian", "de": "German"}
WORDSETS = {k: set(v.split()) for k, v in WORDS.items()}
TOKEN = re.compile(r"[^\W\d_]+(?:'[^\W\d_]+)?")
DEFAULT_EXTS = (".srt", ".vtt", ".ass", ".ssa")


def read_start(path, limit=60000):
    with open(path, "rb") as f:
        data = f.read(limit)
    for enc in ("utf-8-sig", "utf-16", "cp1252"):
        try:
            return data.decode(enc)
        except (UnicodeDecodeError, UnicodeError):
            continue
    return data.decode("utf-8", "replace")


def language_of(path):
    """Best guess at a subtitle file's language code, or '' if it can't tell."""
    try:
        text = read_start(path)
    except OSError:
        return ""
    if path.lower().endswith((".ass", ".ssa")):      # keep the dialogue, drop the style header
        text = "\n".join(l.split(",", 9)[-1] for l in text.splitlines() if l.lower().startswith("dialogue:"))
    tokens = TOKEN.findall(re.sub(r"<[^>]+>|\{[^}]*\}", " ", text).lower())
    if len(tokens) < 40:
        return ""
    scores = {lang: sum(1 for t in tokens if t in words) for lang, words in WORDSETS.items()}
    ranked = sorted(scores.values(), reverse=True)
    if ranked[0] < 0.08 * len(tokens) or ranked[0] < 1.15 * ranked[1]:
        return ""                                    # too few hits, or too close to call
    return max(scores, key=scores.get)


def inside(child, parent):
    child, parent = os.path.abspath(child), os.path.abspath(parent)
    try:
        return os.path.commonpath([child, parent]) == parent
    except ValueError:
        return False


def scan(source, bank, lang="es", exts=DEFAULT_EXTS, keep_all=False, tick=None):
    """Look through `source` at any depth and decide what to copy. Nothing is written.
    A file already in the bank is never overwritten: an identical one is counted as `already`,
    a different file with the same name and place as `name_clash` (the bank's copy is kept)."""
    source, bank = os.path.abspath(source), os.path.abspath(bank)
    target = os.path.join(bank, os.path.basename(source.rstrip(os.sep)) or "subtitles")
    plan = {"source": source, "target": target, "found": 0, "to_copy": [], "already": 0,
            "name_clash": 0, "other": {}, "unknown": 0}
    exts = tuple(e.lower() if e.startswith(".") else "." + e.lower() for e in exts)
    for folder, dirs, files in os.walk(source):
        dirs[:] = sorted(d for d in dirs if not d.startswith("."))
        for name in sorted(files):
            if name.startswith(".") or not name.lower().endswith(exts):
                continue
            plan["found"] += 1
            if tick and plan["found"] % 50 == 0:
                tick(plan["found"])
            src = os.path.join(folder, name)
            if not keep_all:
                found_lang = language_of(src)
                if found_lang != lang:
                    if found_lang:
                        plan["other"][found_lang] = plan["other"].get(found_lang, 0) + 1
                    else:
                        plan["unknown"] += 1
                    continue
            dst = os.path.join(target, os.path.relpath(src, source))
            if os.path.exists(dst):
                same = os.path.isfile(dst) and os.path.getsize(dst) == os.path.getsize(src)
                plan["already" if same else "name_clash"] += 1
                continue
            plan["to_copy"].append((src, dst))
    return plan


def copy(plan, tick=None):
    """Carry out a plan from scan(). Returns (number copied, list of paths that failed)."""
    copied, failed = 0, []
    for src, dst in plan["to_copy"]:
        try:
            if os.path.exists(dst):                  # appeared since the scan: still never overwrite
                continue
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
            copied += 1
        except OSError:
            failed.append(src)
        if tick and copied % 50 == 0:
            tick(copied)
    return copied, failed


def summary(plan, lang="es", keep_all=False):
    """Plain-language lines describing a plan."""
    lines = ["Found %s subtitle file(s)." % format(plan["found"], ",")]
    what = "" if keep_all else LANGUAGES.get(lang, lang) + " "
    lines.append("%s new %sfile(s) to copy." % (format(len(plan["to_copy"]), ","), what))
    if plan["already"]:
        lines.append("%s already in the bank." % format(plan["already"], ","))
    if plan["name_clash"]:
        lines.append("%s left alone: the bank already has a different file with that name in that place."
                     % format(plan["name_clash"], ","))
    if plan["other"]:
        detail = ", ".join("%s %d" % (LANGUAGES.get(k, k), v) for k, v in sorted(plan["other"].items(), key=lambda x: -x[1]))
        lines.append("%s in another language (%s)." % (format(sum(plan["other"].values()), ","), detail))
    if plan["unknown"]:
        lines.append("%s skipped: language couldn't be identified (too short, or not text)." % format(plan["unknown"], ","))
    return lines
