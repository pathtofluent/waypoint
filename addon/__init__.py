"""
PathToFluent Waypoint - an Anki add-on.

Sorts the new cards of your sentence decks so the next card is always the most
useful sentence containing exactly one word you don't know yet.

  * Read-only decks (e.g. an Assimil deck) are never touched; as you learn their
    cards, their words and sentences count as known.
  * Sorted decks (e.g. your Trailblazer decks) are scored, sorted, held back or cleared.

Tools > Waypoint > Settings to choose the decks and files.
It runs when Anki opens, after each sync, and from Tools > Waypoint > Reconcile cards.
"""
import datetime
import html
import json
import os
import re
import shutil
import time

from aqt import dialogs, gui_hooks, mw
from aqt.qt import *
from aqt.utils import askUser, openFolder, showInfo, showWarning, tooltip

from . import core, daily, gather, labels, layout

VERSION = "0.7.0"
HELD, CLEARED, KNOWN, LEARN_NOW = "waypoint_held", "waypoint_cleared", "waypoint_known", "waypoint_learn_now"
LABELLED = "waypoint_labelled"
MODE_BI, MODE_MONO = "waypoint_bilingual", "waypoint_monolingual"   # which definition a card shows
USEFUL = "waypoint_useful_"            # + 1..5, the usefulness rating from the labels hand-off
OLD_TAGS = {"ou_held": HELD, "ou_cleared": CLEARED, "ou_known": KNOWN, "ou_learn_now": LEARN_NOW}
FIRST = "(first field)"
DEFAULTS = {
    "source_decks": {},                 # {"Deck name": "Field holding the sentence"}  ("" = first field)
    "managed_decks": [],                # decks whose new cards are sorted
    "managed_note_types": ["PathToFluent Trailblazer", "SubDeck"],  # used only when managed_decks is empty
    "sentence_field": "Sentence",
    "unknown_field": "Unknown Words",
    "labels_field": "Labels",
    "lemma_field": "Lemma",
    "definition_field": "Definition",
    "definition_mono_field": "Definition Monolingual",
    "dictionary_field": "Dictionary Link",
    "dictionary_url": "https://dle.rae.es/{lemma}",
    "dictionary_name": "RAE",
    "card_mode": "bilingual",           # what new cards show: "bilingual" or "monolingual"
    "known_interval_days": 21,
    "source_known_interval_days": 21,
    "count_learning_as_known": False,
    "word_weight": 1.0,
    "sentence_weight": 1.0,
    "exact_sentence_weight": 0.5,
    "chunk_weight": 0.5,
    "frequency_list": "",
    "subtitle_bank_folder": "",
    "run_automatically": True,
    "bank_language": "es",
    "labels_folder": "",                # hand-off folder for labels; blank = labelling off
    "labels_batch_size": 300,
    "stats_folder": "",                 # folder for the daily numbers file; blank = off
    "usefulness_weight": 0.25,
    "usefulness_goal": "",              # blank = everyday conversation at an educated adult's level
    "highlight_unknown_word": True,
    "highlight_color": "#2f9e77",
    "shortcut_mark_known": "K",
    "shortcut_browse_same_word": "L",
}
_cache = {}


def cfg():
    conf = dict(DEFAULTS)
    conf.update(mw.addonManager.getConfig(__name__) or {})
    return conf


FOLDERS = ("subtitle-bank", "frequency-list", "lists")


def data_dir(sub=""):
    """<Anki data folder>/<profile>/waypoint/... Created on demand; survives add-on updates and removal."""
    d = os.path.join(mw.pm.profileFolder(), "waypoint", sub)
    os.makedirs(d, exist_ok=True)
    return d


def legacy_freq():
    """<profile>/dbs/frequency.txt, where MorphMan-style add-ons keep theirs. Read-only fallback."""
    return os.path.join(mw.pm.profileFolder(), "dbs", "frequency.txt")


def default_freq():
    """The first file in waypoint/frequency-list. Falls back to dbs/frequency.txt if that folder is empty."""
    folder = data_dir("frequency-list")
    files = sorted(f for f in os.listdir(folder) if not f.startswith("."))
    if files:
        return os.path.join(folder, files[0])
    return legacy_freq() if os.path.isfile(legacy_freq()) else ""


def freq_path(conf):
    return os.path.expanduser(conf["frequency_list"] or "") or default_freq()


def names_path():
    path = os.path.join(data_dir(), "names.txt")
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            f.write("# One name per line. These are ignored when counting unknown words.\n")
    return path


def read_names():
    with open(names_path(), encoding="utf-8-sig") as f:
        return {line.strip().lower() for line in f if line.strip() and not line.lstrip().startswith("#")}


def write_lists(plan):
    """Readable copies of what the cards currently say. Rewritten on every run; the cards are the record."""
    for name, items in plan["lists"].items():
        with open(os.path.join(data_dir("lists"), name + ".txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(items) + ("\n" if items else ""))


def load_stats():
    try:
        return json.load(open(os.path.join(data_dir(), "stats.json"), encoding="utf-8"))
    except Exception:
        return {}


def save_stats(stats):
    try:
        json.dump(stats, open(os.path.join(data_dir(), "stats.json"), "w", encoding="utf-8"))
    except OSError:
        pass


def get_freq(conf):
    path = freq_path(conf)
    if not path or not os.path.isfile(path):
        return {}
    stamp = (path, os.path.getmtime(path))
    if _cache.get("freq_stamp") != stamp:
        _cache["freq"], _cache["freq_stamp"] = core.load_freq(path), stamp
    return _cache["freq"]


def bank_folder(conf):
    return os.path.expanduser(conf["subtitle_bank_folder"] or "") or data_dir("subtitle-bank")


def bank_breakdown(folder):
    """Subtitle files per top-level folder of the bank, largest first."""
    counts = {}
    for root, _, files in os.walk(folder):
        n = sum(1 for f in files if f.lower().endswith(core.SUB_EXT) and not f.startswith("."))
        if n:
            rel = os.path.relpath(root, folder)
            top = "(loose files)" if rel == "." else rel.split(os.sep)[0]
            counts[top] = counts.get(top, 0) + n
    return sorted(counts.items(), key=lambda x: (-x[1], x[0].lower()))


def get_bank(conf, freq, force=False, names=None):
    folder = bank_folder(conf)
    tick = lambda n, name: mw.progress.update(label="Indexing subtitles: %d files\n%s" % (n, name[:60]))
    return core.Bank.load_or_build(folder, os.path.join(data_dir(), "bank_index.pkl"), freq, force, tick, names)


def rows(card_ids):
    out, ids = [], list(card_ids)
    for i in range(0, len(ids), 900):
        chunk = ",".join(str(x) for x in ids[i:i + 900])
        out += mw.col.db.all("select c.id, c.nid, c.type, c.queue, c.ivl, n.mid, n.flds, n.tags "
                             "from cards c join notes n on n.id = c.nid where c.id in (%s)" % chunk)
    return out


def field_ord(mid, name):
    key = (mid, name)
    if key not in _cache:
        model = mw.col.models.get(mid)
        fmap = mw.col.models.field_map(model) if model else {}
        _cache[key] = fmap[name][0] if name in fmap else None
    return _cache[key]


def quoted(name):
    return '"%s"' % name.replace('"', '\\"')


def pick_ord(mid, names):
    for name in names:
        o = field_ord(mid, name) if name else None
        if o is not None:
            return o
    return None


def collect(conf):
    cards, seen, missing = [], set(), set()
    if conf["managed_decks"]:
        searches = [("deck:" + quoted(d), d) for d in conf["managed_decks"]]
    else:
        searches = [("note:" + quoted(n), n) for n in conf["managed_note_types"]]
    for search, label in searches:
        for cid, nid, ctype, queue, ivl, mid, flds, tags in rows(mw.col.find_cards(search)):
            if cid in seen:
                continue
            f, tagset = flds.split("\x1f"), set(tags.split())
            s_ord = pick_ord(mid, [conf["sentence_field"], "Sentence", "Expression"])
            l_ord = field_ord(mid, conf["labels_field"])
            if s_ord is None:
                missing.add("%s: some cards have no '%s' field and were skipped" % (label, conf["sentence_field"]))
                continue
            if field_ord(mid, conf["unknown_field"]) is None:
                missing.add("%s: some cards have no '%s' field, so the unknown word can't be written on them"
                            % (label, conf["unknown_field"]))
            seen.add(cid)
            cards.append({"cid": cid, "nid": nid, "mid": mid, "role": "managed", "sentence": f[s_ord],
                          "labels": f[l_ord] if l_ord is not None else "", "type": ctype, "ivl": ivl,
                          "suspended": queue == -1, "held": HELD in tagset, "cleared": CLEARED in tagset,
                          "known_manual": KNOWN in tagset, "learn_now": LEARN_NOW in tagset,
                          "labelled": LABELLED in tagset, "can_label": l_ord is not None,
                          "can_define": None not in (field_ord(mid, conf["definition_field"]),
                                                     field_ord(mid, conf["definition_mono_field"])),
                          "definition": "".join(f[o] for o in (field_ord(mid, conf["definition_field"]),
                                                               field_ord(mid, conf["definition_mono_field"]))
                                                if o is not None),
                          "mode": "mono" if MODE_MONO in tagset else "bi" if MODE_BI in tagset else None,
                          "usefulness": next((int(t[len(USEFUL):]) for t in tagset
                                              if t.startswith(USEFUL) and t[len(USEFUL):] in "12345"
                                              and len(t) == len(USEFUL) + 1), None)})
    for deck, fld in conf["source_decks"].items():
        for cid, nid, ctype, queue, ivl, mid, flds, tags in rows(mw.col.find_cards("deck:" + quoted(deck))):
            if cid in seen:
                continue
            o = pick_ord(mid, [fld, "Expression", "Sentence"]) if fld else 0
            cards.append({"cid": cid, "nid": nid, "mid": mid, "role": "source",
                          "sentence": flds.split("\x1f")[o or 0], "labels": "", "type": ctype, "ivl": ivl,
                          "known_manual": KNOWN in tags.split()})
    return cards, missing


# ── labels hand-off ─────────────────────────────────────────────────────────
def labels_dir(conf):
    folder = os.path.expanduser(conf["labels_folder"] or "")
    return folder if folder and os.path.isdir(folder) else ""


def import_labels(conf):
    """Read the answers file if there is one, store the valid labels on their cards, set the file aside."""
    folder = labels_dir(conf)
    path = os.path.join(folder, labels.ANSWERS) if folder else ""
    if not path or not os.path.isfile(path):
        return {}
    try:
        data = labels.load_answers(path)
    except Exception as e:
        os.replace(path, os.path.join(folder, "waypoint_labels.unreadable.json"))
        return {"labels_error": "The answers file couldn't be read (%s). It was renamed to "
                                "waypoint_labels.unreadable.json." % type(e).__name__}
    keys = set()
    for name in ("labels", "usefulness", "definitions"):
        table = data.get(name) if isinstance(data, dict) else None
        keys.update(table if isinstance(table, dict) else ())
    sentences, notes, targets = {}, {}, {}
    for key in keys:
        try:
            note = mw.col.get_note(int(key))
        except Exception:
            continue
        s_ord = pick_ord(note.mid, [conf["sentence_field"], "Sentence", "Expression"])
        if s_ord is not None and field_ord(note.mid, conf["labels_field"]) is not None:
            sentences[int(key)], notes[int(key)] = core.plain(note.fields[s_ord]), note
            u_ord = field_ord(note.mid, conf["unknown_field"])
            words = [w for w in re.sub(r"<[^>]+>", "", note.fields[u_ord]).split(",") if w.strip()] \
                if u_ord is not None else []
            if len(words) == 1 and None not in (field_ord(note.mid, conf["definition_field"]),
                                                field_ord(note.mid, conf["definition_mono_field"])):
                targets[int(key)] = words[0]
    parsed, rejected, strangers = labels.parse_answers(data, sentences)
    ratings, bad_ratings = labels.parse_usefulness(data, set(sentences))
    defs, bad_defs = labels.parse_definitions(data, targets)
    for nid in set(parsed) | set(ratings) | set(defs):
        note = notes[nid]
        if parsed.get(nid):
            note.fields[field_ord(note.mid, conf["labels_field"])] = parsed[nid]
        if nid in defs:
            d = defs[nid]
            marker = html.escape(d["word"], quote=True)
            wrap = lambda text: '<span data-word="%s">%s</span>' % (marker, html.escape(text)) if text else ""
            note.fields[field_ord(note.mid, conf["definition_field"])] = wrap(d["en"])
            note.fields[field_ord(note.mid, conf["definition_mono_field"])] = wrap(d["es"])
            for name, value in ((conf["lemma_field"], html.escape(d["lemma"])),
                                (conf["dictionary_field"], labels.dictionary_link(
                                    conf["dictionary_url"], conf["dictionary_name"], d["lemma"]))):
                o = field_ord(note.mid, name)
                if o is not None:
                    note.fields[o] = value
        if nid in ratings:
            for tag in [t for t in note.tags if t.startswith(USEFUL)]:
                note.remove_tag(tag)
            note.add_tag(USEFUL + str(ratings[nid]))
        if nid in parsed:
            note.add_tag(LABELLED)
        mw.col.update_note(note)
    os.replace(path, os.path.join(folder, labels.IMPORTED))
    return {"labels_imported": len(set(parsed) | set(ratings) | set(defs)), "labels_rated": len(ratings),
            "labels_defined": len(defs), "labels_rejected": rejected + bad_ratings + bad_defs,
            "labels_unknown_cards": strangers}


def export_labels(conf, cards, plan):
    """Write the list of cards that still need a look, most useful first."""
    folder = labels_dir(conf)
    if not folder:
        return {}
    front = [cid for _, cid, _ in plan["ready"]] + [cid for _, cid, _ in plan["fallback"]]
    place = {cid: i for i, cid in enumerate(front)}
    unknown_of = lambda c: [w.strip() for w in plan["unknown_field"].get(c["nid"], "").split(",") if w.strip()]
    def needs_of(c):
        need = []
        if c.get("can_label") and not c.get("labelled") and not c["labels"].strip():
            need.append("labels")
        words = unknown_of(c)
        if c.get("can_define") and len(words) == 1 and \
                'data-word="%s"' % html.escape(labels.base_word(words[0]), quote=True) not in c.get("definition", ""):
            need.append("definition")
        return need

    todo = {}
    for c in cards:
        if c["role"] == "managed" and c["type"] == 0 and not c.get("cleared") and not c.get("known_manual") \
                and not (c.get("suspended") and not c.get("held")) and c["nid"] not in todo:
            need = needs_of(c)
            if need:
                todo[c["nid"]] = dict(c, needs=need)
    ordered = sorted(todo.values(), key=lambda c: (0, place[c["cid"]], 0) if c["cid"] in place
                     else (1, len(unknown_of(c)), c["cid"]))
    senses = labels.senses_in_use(core.parse_labels(c["labels"]) for c in cards if c.get("labels"))
    doc = labels.build_export([{"id": c["nid"], "sentence": core.plain(c["sentence"]), "unknown": unknown_of(c),
                                "needs": c["needs"]} for c in ordered], senses, conf["bank_language"], conf["labels_batch_size"],
                              conf["usefulness_goal"] or labels.DEFAULT_GOAL)
    with open(os.path.join(folder, labels.TO_LABEL), "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
    howto = os.path.join(folder, labels.HOWTO)
    if not os.path.isfile(howto) or open(howto, encoding="utf-8").read() != labels.HOWTO_TEXT:
        with open(howto, "w", encoding="utf-8") as f:
            f.write(labels.HOWTO_TEXT)
    return {"labels_waiting": sum(1 for c in ordered if "labels" in c["needs"]),
            "definitions_waiting": sum(1 for c in ordered if "definition" in c["needs"]),
            "definitions_done": len({c["nid"] for c in cards if c.get("definition")}),
            "labels_done": len({c["nid"] for c in cards if c.get("labelled")}),
            "labels_rated_total": len({c["nid"] for c in cards if c.get("usefulness")})}


def apply(plan, cards, conf):
    by_cid = {c["cid"]: c for c in cards}
    order = [cid for _, cid, _ in plan["ready"]] + [cid for _, cid, _ in plan["fallback"]]
    wake = [cid for cid in order if by_cid[cid]["held"]]
    sleep_hold = [cid for cid in plan["hold"] if not by_cid[cid]["held"]]
    sleep_clear = plan["clear"]
    nids = lambda cids: [by_cid[c]["nid"] for c in cids]
    if wake:
        mw.col.sched.unsuspend_cards(wake)
        mw.col.tags.bulk_remove(nids(wake), HELD)
    if sleep_hold:
        mw.col.sched.suspend_cards(sleep_hold)
        mw.col.tags.bulk_add(nids(sleep_hold), HELD)
    if sleep_clear:
        mw.col.sched.suspend_cards(sleep_clear)
        mw.col.tags.bulk_remove(nids(sleep_clear), HELD)
        mw.col.tags.bulk_add(nids(sleep_clear), CLEARED)
    if order:
        mw.col.sched.reposition_new_cards(card_ids=order, starting_from=0, step_size=1,
                                          randomize=False, shift_existing=False)
    # Which definition a card shows. New cards follow the setting; a card you have studied keeps its own.
    want_key, want, other = ("mono", MODE_MONO, MODE_BI) if conf["card_mode"] == "monolingual" \
        else ("bi", MODE_BI, MODE_MONO)
    managed = [c for c in cards if c["role"] == "managed"]
    switch = sorted({c["nid"] for c in managed if c["type"] == 0 and c.get("mode") != want_key})
    untagged = sorted({c["nid"] for c in managed if c["type"] != 0 and c.get("mode") is None})
    if switch:
        mw.col.tags.bulk_remove(switch, other)
        mw.col.tags.bulk_add(switch, want)
    if untagged:
        mw.col.tags.bulk_add(untagged, MODE_BI)
    changed = 0
    by_nid = {c["nid"]: c for c in cards}
    for nid, text in plan["unknown_field"].items():
        o = field_ord(by_nid[nid]["mid"], conf["unknown_field"])
        if o is None:
            continue
        note = mw.col.get_note(nid)
        if note.fields[o] != text:
            note.fields[o] = text
            mw.col.update_note(note)
            changed += 1
    return changed


def reconcile(silent=False, rebuild=False):
    if not mw.col:
        return
    conf = cfg()
    if not conf["managed_decks"] and not conf["source_decks"]:
        if not silent:
            showInfo("Waypoint isn't set up yet. Choose your decks in Tools > Waypoint > Settings.")
        return
    mw.progress.start(immediate=True, label="Waypoint: reading cards...")
    try:
        label_stats = {}
        try:
            label_stats.update(import_labels(conf))
        except Exception as e:                       # labelling must never stop the sorting
            label_stats["labels_error"] = "Importing labels failed: %s: %s" % (type(e).__name__, e)
        cards, missing = collect(conf)
        freq = get_freq(conf)
        names = read_names()
        bank = get_bank(conf, freq, force=rebuild, names=names)
        mw.progress.update(label="Waypoint: scoring %d cards..." % len(cards))
        plan = core.analyse(cards, conf, freq, bank, names)
        s = plan["stats"]
        s["fields_updated"] = apply(plan, cards, conf)
        s["bank_files"] = bank.files if bank else 0
        s["bank_sentences"] = bank.total if bank else 0
        try:
            label_stats.update(export_labels(conf, cards, plan))
        except Exception as e:
            label_stats["labels_error"] = "Writing the cards to label failed: %s: %s" % (type(e).__name__, e)
        s.update(label_stats)
        s["stats_note"] = write_daily(conf, s, cards)
        s["bank_folders"] = bank_breakdown(bank_folder(conf))
        s["frequency_words"] = len(freq)
        s["frequency_file"] = freq_path(conf) if freq else "(none found)"
        save_stats(s)
        write_lists(plan)
    except Exception as e:
        if not silent:
            showWarning("Waypoint could not finish:\n%s: %s" % (type(e).__name__, e))
        return
    finally:
        mw.progress.finish()
    mw.reset()
    mw.toolbar.draw()
    if missing and not silent:
        showWarning("\n".join(sorted(missing)))
    if not silent:
        tooltip("Waypoint: %(ready)d ready, %(fallback)d review-only, %(held)d waiting, %(cleared)d cleared" % s)


def write_daily(conf, stats, cards):
    """Keep today's line in the daily numbers file, if a folder is chosen. Never stops the sorting."""
    folder = os.path.expanduser(conf["stats_folder"] or "")
    if not folder:
        return ""
    if not os.path.isdir(folder):
        return "The folder for daily numbers can't be found: %s" % folder
    try:
        studied = sum(1 for c in cards if c["type"] != 0)
        return daily.write(folder, daily.day_line(stats, studied, conf["bank_language"], datetime.date.today()))
    except Exception as e:
        return "Writing the daily numbers failed: %s: %s" % (type(e).__name__, e)


def show_stats():
    s = load_stats()
    if not s:
        showInfo("No numbers yet. Choose your decks in Tools > Waypoint > Settings, then Reconcile cards.")
        return
    lines = [("Known words", "known_words"), ("Words being learned", "learning_words"),
             ("Known sentences", "known_sentences"), ("Sentences studied", "seen_sentences"), None,
             ("Cards ready (one unknown word)", "ready"), ("Cards with no unknown words", "fallback"),
             ("Cards waiting", "held"), ("Cards cleared this run", "cleared"), None,
             ("Subtitle files in bank", "bank_files"), ("Sentences in bank", "bank_sentences"),
             ("Words in frequency list", "frequency_words")]
    text = "\n".join("" if l is None else "%s: %s" % (l[0], format(s.get(l[1], 0), ",")) for l in lines)
    text += "\nFrequency file: %s" % s.get("frequency_file", "(run Reconcile to see)")
    if cfg()["labels_folder"]:
        text += "\n\nLabels hand-off:\n  Cards checked so far: %s\n  Cards with a usefulness rating: %s\n  Cards with a definition: %s\n  Cards waiting to be checked: %s\n  Cards waiting for a definition: %s\n  Read in on the last run: %s" % (
            format(s.get("labels_done", 0), ","), format(s.get("labels_rated_total", 0), ","),
            format(s.get("definitions_done", 0), ","), format(s.get("labels_waiting", 0), ","),
            format(s.get("definitions_waiting", 0), ","), format(s.get("labels_imported", 0), ","))
        if s.get("labels_rejected") or s.get("labels_unknown_cards"):
            text += "\n  Ignored on the last run: %d invalid label(s), rating(s) or definition(s), %d card(s) not found" % (
                s.get("labels_rejected", 0), s.get("labels_unknown_cards", 0))
        if s.get("labels_error"):
            text += "\n  Problem: %s" % s["labels_error"]
    if cfg()["stats_folder"]:
        text += "\n\nDaily numbers: %s" % (s.get("stats_note") or "written to %s" % daily.STATS_FILE)
    folders = s.get("bank_folders") or []
    if folders:
        text += "\n\nIn the subtitle bank:\n" + "\n".join("  %s: %s" % (name, format(n, ",")) for name, n in folders[:15])
        if len(folders) > 15:
            text += "\n  ...and %d more folders" % (len(folders) - 15)
    showInfo(text, title="PathToFluent Waypoint")


# ── settings window ─────────────────────────────────────────────────────────
class Settings(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("PathToFluent Waypoint - Settings")
        self.setMinimumWidth(620)
        conf = cfg()
        decks = sorted(d.name for d in mw.col.decks.all_names_and_ids())
        lay = QVBoxLayout(self)

        cols = QHBoxLayout()
        self.source = self.deck_list(decks, set(conf["source_decks"]))
        self.managed = self.deck_list(decks, set(conf["managed_decks"]))
        for title, hint, widget in (
                ("Read-only decks", "Never changed. The words and sentences you learn here count as known.", self.source),
                ("Decks to sort", "New cards here are sorted, held back or cleared.", self.managed)):
            box = QVBoxLayout()
            box.addWidget(QLabel("<b>%s</b><br><small>%s</small>" % (title, hint)))
            box.addWidget(widget)
            cols.addLayout(box)
        lay.addLayout(cols)

        form = QFormLayout()
        names = sorted({f["name"] for m in mw.col.models.all() for f in m["flds"]})
        self.source_field = QComboBox()
        self.source_field.addItems([FIRST] + names)
        current = next(iter(conf["source_decks"].values()), "")
        self.source_field.setCurrentText(current or FIRST)
        form.addRow("Sentence field in read-only decks", self.source_field)
        self.sentence_field = QComboBox()
        self.sentence_field.addItems(names)
        self.sentence_field.setCurrentText(conf["sentence_field"])
        form.addRow("Sentence field in decks to sort", self.sentence_field)

        self.freq = QLineEdit(conf["frequency_list"])
        self.freq.setPlaceholderText("Blank = the file in Waypoint's frequency-list folder")
        form.addRow("Frequency list file", self.with_button(self.freq, self.pick_file))
        self.bank = QLineEdit(conf["subtitle_bank_folder"])
        self.bank.setPlaceholderText("Blank = the subtitle-bank folder")
        form.addRow("Subtitle bank folder", self.with_button(self.bank, self.pick_folder))

        self.labels = QLineEdit(conf["labels_folder"])
        self.labels.setPlaceholderText("Blank = labelling off")
        form.addRow("Labels hand-off folder", self.with_button(self.labels, self.pick_labels))

        self.stats = QLineEdit(conf["stats_folder"])
        self.stats.setPlaceholderText("Blank = off")
        form.addRow("Daily numbers folder", self.with_button(self.stats, self.pick_stats))

        self.mode = QComboBox()
        self.mode.addItem("An English definition (bilingual)", "bilingual")
        self.mode.addItem("A definition in the language I'm learning (monolingual)", "monolingual")
        self.mode.setCurrentIndex(max(0, self.mode.findData(conf["card_mode"])))
        form.addRow("New cards show", self.mode)

        self.language = QComboBox()
        for code, name in sorted(gather.LANGUAGES.items(), key=lambda x: x[1]):
            self.language.addItem(name, code)
        self.language.setCurrentIndex(max(0, self.language.findData(conf["bank_language"])))
        form.addRow("Language of the subtitle bank", self.language)

        self.days, self.source_days = QSpinBox(), QSpinBox()
        for spin, value in ((self.days, conf["known_interval_days"]), (self.source_days, conf["source_known_interval_days"])):
            spin.setRange(1, 365)
            spin.setValue(int(value))
            spin.setSuffix(" days")
        form.addRow("A word is known when its card's interval reaches", self.days)
        form.addRow("Same, for read-only decks", self.source_days)
        self.auto = QCheckBox("Run when Anki opens and after each sync")
        self.auto.setChecked(bool(conf["run_automatically"]))
        form.addRow("", self.auto)
        lay.addLayout(form)

        where = QLabel("<small>Data folder: %s</small>" % data_dir())
        where.setWordWrap(True)
        where.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        lay.addWidget(where)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        opener = buttons.addButton("Open data folder", QDialogButtonBox.ButtonRole.ActionRole)
        opener.clicked.connect(open_data_folder)
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)
        lay.addWidget(buttons)

    def deck_list(self, decks, checked):
        area, inner, col = QScrollArea(), QWidget(), QVBoxLayout()
        area.boxes = []
        for name in decks:
            box = QCheckBox(name.replace("&", "&&"))
            box.setChecked(name in checked)
            col.addWidget(box)
            area.boxes.append(box)
        col.addStretch(1)
        inner.setLayout(col)
        area.setWidget(inner)
        area.setWidgetResizable(True)
        area.setMinimumHeight(240)
        return area

    def checked(self, area):
        return [box.text().replace("&&", "&") for box in area.boxes if box.isChecked()]

    def with_button(self, edit, fn):
        holder, row = QWidget(), QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        button = QPushButton("Browse...")
        button.clicked.connect(fn)
        row.addWidget(edit)
        row.addWidget(button)
        holder.setLayout(row)
        return holder

    def pick_file(self):
        path = QFileDialog.getOpenFileName(self, "Choose your frequency list", os.path.expanduser("~"))[0]
        if path:
            self.freq.setText(path)

    def pick_folder(self):
        path = QFileDialog.getExistingDirectory(self, "Choose your subtitle bank folder", os.path.expanduser("~"))
        if path:
            self.bank.setText(path)

    def pick_labels(self):
        path = QFileDialog.getExistingDirectory(self, "Choose the folder for the labels hand-off",
                                                self.labels.text().strip() or os.path.expanduser("~"))
        if path:
            self.labels.setText(path)

    def pick_stats(self):
        path = QFileDialog.getExistingDirectory(self, "Choose the folder for the daily numbers file",
                                                self.stats.text().strip() or os.path.expanduser("~"))
        if path:
            self.stats.setText(path)

    def save(self):
        source, managed = self.checked(self.source), self.checked(self.managed)
        both = sorted(set(source) & set(managed))
        if both:
            showWarning("A deck can't be both read-only and sorted:\n" + "\n".join(both))
            return
        hand_off = os.path.expanduser(self.labels.text().strip())
        if hand_off and not os.path.isdir(hand_off):
            try:
                os.makedirs(hand_off)
            except OSError as e:
                showWarning("Couldn't create the labels hand-off folder:\n%s" % e.strerror)
                return
        numbers = os.path.expanduser(self.stats.text().strip())
        if numbers and not os.path.isdir(numbers):
            showWarning("The folder for daily numbers doesn't exist:\n%s" % numbers)
            return
        field = self.source_field.currentText()
        conf = cfg()
        conf.update({
            "source_decks": {d: ("" if field == FIRST else field) for d in source},
            "managed_decks": managed,
            "sentence_field": self.sentence_field.currentText(),
            "frequency_list": self.freq.text().strip(),
            "subtitle_bank_folder": self.bank.text().strip(),
            "bank_language": self.language.currentData() or "es",
            "labels_folder": self.labels.text().strip(),
            "stats_folder": self.stats.text().strip(),
            "card_mode": self.mode.currentData() or "bilingual",
            "known_interval_days": self.days.value(),
            "source_known_interval_days": self.source_days.value(),
            "run_automatically": self.auto.isChecked(),
        })
        mw.addonManager.writeConfig(__name__, conf)
        self.accept()
        reconcile()


def open_settings():
    Settings(mw).exec()


def add_subtitles():
    """Tools > PathToFluent Waypoint > Add subtitles to the bank."""
    conf = cfg()
    lang, bank = conf["bank_language"], bank_folder(conf)
    source = QFileDialog.getExistingDirectory(mw, "Choose the folder that holds your subtitle files",
                                              os.path.expanduser("~"))
    if not source:
        return
    if gather.inside(source, bank):
        showInfo("That folder is already inside the subtitle bank.")
        return
    mw.progress.start(immediate=True, label="Looking for subtitle files...")
    try:
        plan = gather.scan(source, bank, lang,
                           tick=lambda n: mw.progress.update(label="Checked %s subtitle files..." % format(n, ",")))
    except Exception as e:
        showWarning("Couldn't read that folder:\n%s: %s" % (type(e).__name__, e))
        return
    finally:
        mw.progress.finish()
    text = "\n".join(gather.summary(plan, lang))
    if not plan["to_copy"]:
        showInfo(text + "\n\nNothing new to copy.", title="PathToFluent Waypoint")
        return
    question = "%s\n\nCopy %s file(s) into the subtitle bank? Your originals are not moved or changed." % (
        text, format(len(plan["to_copy"]), ","))
    if not askUser(question, title="PathToFluent Waypoint"):
        return
    mw.progress.start(immediate=True, label="Copying subtitle files...")
    try:
        copied, failed = gather.copy(plan, tick=lambda n: mw.progress.update(label="Copied %s files..." % format(n, ",")))
    finally:
        mw.progress.finish()
    if failed:
        showWarning("%d file(s) could not be copied." % len(failed))
    tooltip("Added %s subtitle file(s) to the bank. Re-indexing..." % format(copied, ","))
    if copied:
        reconcile()


def prepare_note_type():
    """Tools > PathToFluent Waypoint > Prepare a note type: add the fields Waypoint uses, and its layout."""
    mm = mw.col.models
    names = sorted(n.name for n in mm.all_names_and_ids())
    likely = next((n for n in names if n.startswith(("PathToFluent Trailblazer", "SubDeck"))), names[0])
    name, ok = QInputDialog.getItem(mw, "PathToFluent Waypoint", "Note type to prepare:", names,
                                    names.index(likely), False)
    if not ok or not name:
        return
    m = mm.by_name(name)
    have = [f["name"] for f in m["flds"]]
    missing = [f for f in layout.FIELDS if f not in have]
    ours = name.startswith(("PathToFluent Trailblazer", "SubDeck")) and len(m["tmpls"]) == 1
    current = (m["tmpls"][0]["qfmt"], m["tmpls"][0]["afmt"], m["css"])
    new_layout = ours and current != (layout.FRONT, layout.BACK, layout.CSS)
    # Cards made before Trailblazer got its name still carry the old note type name and tag.
    rename_to = "PathToFluent Trailblazer" if name == "SubDeck" and not mm.by_name("PathToFluent Trailblazer") else ""
    if not missing and not new_layout and not rename_to:
        showInfo("'%s' already has everything Waypoint uses." % name)
        return
    lines = []
    if rename_to:
        lines.append("Rename this note type from 'SubDeck' to '%s', and the 'SubDeck' tag on its cards to "
                     "'Trailblazer'. Only the names change." % rename_to)
    if missing:
        lines.append("Add %d field(s): %s." % (len(missing), ", ".join(missing)))
        lines.append("Adding fields makes Anki ask for a one-time full sync. Your cards keep everything they have.")
    if new_layout:
        lines.append("Update the card layout so the new word's definition shows on the back. "
                     "The current layout is saved in Waypoint's data folder first.")
    if not ours and "Definition" in missing:
        lines.append("This isn't a Trailblazer note type, so its layout is left alone: add the new fields to "
                     "your card template yourself if you want them shown.")
    if not askUser("\n\n".join(lines) + "\n\nGo ahead?", title="PathToFluent Waypoint"):
        return
    if missing and hasattr(mw, "confirm_schema_modification") and not mw.confirm_schema_modification():
        return
    try:
        for f in missing:
            mm.add_field(m, mm.new_field(f))
        if new_layout:
            slug = re.sub(r"[^A-Za-z0-9]+", "-", name).strip("-")
            backup = os.path.join(data_dir(), "layout-backup-%s-%s.json" % (slug, time.strftime("%Y%m%d-%H%M%S")))
            with open(backup, "w", encoding="utf-8") as f:
                json.dump({"note_type": name, "front": current[0], "back": current[1], "css": current[2]}, f,
                          ensure_ascii=False, indent=1)
            m["tmpls"][0]["qfmt"], m["tmpls"][0]["afmt"], m["css"] = layout.FRONT, layout.BACK, layout.CSS
        if rename_to:
            m["name"] = rename_to
        mm.update_dict(m)
        if rename_to and mw.col.find_notes("tag:SubDeck"):
            mw.col.tags.rename("SubDeck", "Trailblazer")
    except Exception as e:
        showWarning("Couldn't change the note type:\n%s: %s" % (type(e).__name__, e))
        return
    for key in [k for k in _cache if isinstance(k, tuple)]:      # field positions have changed
        del _cache[key]
    tooltip("'%s' is ready for Waypoint." % (rename_to or name))
    reconcile()


def open_data_folder():
    for sub in FOLDERS:
        data_dir(sub)
    openFolder(data_dir())


def open_freq_folder():
    openFolder(data_dir("frequency-list"))


# ── while reviewing: mark known, browse same word, highlight ───────────────
def is_managed(card):
    conf = cfg()
    if conf["managed_decks"]:
        name = mw.col.decks.name(card.odid or card.did)
        return any(name == d or name.startswith(d + "::") for d in conf["managed_decks"])
    return card.note_type()["name"] in conf["managed_note_types"]


def unknown_words(card):
    note, field = card.note(), cfg()["unknown_field"]
    if field not in note.keys():
        return []
    text = re.sub(r"<[^>]+>", "", note[field])
    return [w.split(" (")[0].strip() for w in text.split(",") if w.strip()]


def mark_known_and_skip():
    card = mw.reviewer.card
    if mw.state != "review" or not card:
        return
    if not is_managed(card):
        tooltip("This card isn't in one of the decks Waypoint sorts.")
        return
    words = unknown_words(card)
    note = card.note()
    mw.col.add_custom_undo_entry("Mark known and skip")
    step = mw.col.undo_status().last_step
    note.add_tag(KNOWN)
    note.add_tag(HELD)
    mw.col.update_note(note)
    mw.col.sched.suspend_cards([card.id])
    mw.col.merge_undo_entries(step)
    tooltip("Marked known: %s" % (", ".join(words) or "this sentence"))
    mw.reviewer.nextCard()


def browse_same_word():
    card = mw.reviewer.card
    words = unknown_words(card) if card else []
    words = [re.sub(r"[^\w'’-]", "", w) for w in words]
    words = [w for w in words if w]
    if not words:
        tooltip("This card has no unknown word recorded.")
        return
    field = cfg()["unknown_field"]
    query = " or ".join('"%s:re:(^|, )%s($|,| [(])"' % (field, w) for w in words)
    browser = dialogs.open("Browser", mw)
    browser.form.searchEdit.lineEdit().setText(query)
    browser.onSearchActivated()


def on_shortcuts(state, shortcuts):
    if state != "review":
        return
    conf = cfg()
    if conf["shortcut_mark_known"]:
        shortcuts.append((conf["shortcut_mark_known"], mark_known_and_skip))
    if conf["shortcut_browse_same_word"]:
        shortcuts.append((conf["shortcut_browse_same_word"], browse_same_word))


def on_card_show(text, card, kind):
    try:
        conf = cfg()
        if not conf["highlight_unknown_word"]:
            return text
        words = unknown_words(card)
        if not words:
            return text
        style = "<style>.wp-new{color:%s;font-weight:600}</style>" % conf["highlight_color"]
        return style + core.highlight(text, words)
    except Exception:
        return text


def learn_now(browser):
    cids = list(browser.selectedCards())
    if not cids:
        return
    nids = mw.col.db.list("select distinct nid from cards where id in (%s)" % ",".join(str(c) for c in cids))
    held = mw.col.db.list("select c.id from cards c join notes n on n.id = c.nid where c.id in (%s) "
                          "and c.queue = -1 and n.tags like ?" % ",".join(str(c) for c in cids), "%" + HELD + "%")
    mw.col.tags.bulk_add(nids, LEARN_NOW)
    if held:
        mw.col.sched.unsuspend_cards(held)
        mw.col.tags.bulk_remove(nids, HELD)
    reconcile(silent=True)
    tooltip("%d card(s) moved to the front of the new queue" % len(cids))


def on_browser_menu(browser, menu):
    action = menu.addAction("Waypoint: learn now")
    action.triggered.connect(lambda _=False, b=browser: learn_now(b))


def on_webview_menu(webview, menu):
    text = webview.selectedText().strip()
    if not text or len(text) > 60:
        return
    def add():
        with open(names_path(), "a", encoding="utf-8") as f:
            f.write("\n".join(text.split()) + "\n")
        tooltip("Added to names: %s. Takes effect at the next reconcile." % text)
    action = menu.addAction("Waypoint: treat '%s' as a name" % text[:30])
    action.triggered.connect(lambda _=False: add())


# ── toolbar counter, menu, automatic runs ───────────────────────────────────
def on_toolbar(links, toolbar):
    s = load_stats()
    label = "Known: %s words · %s sentences" % (format(s.get("known_words", 0), ","),
                                                format(s.get("known_sentences", 0), ","))
    links.append(toolbar.create_link("waypoint", label, show_stats,
                                     tip="Waypoint: click for all the numbers", id="waypoint"))


def migrate():
    """One-time move from the add-on's earlier name (One Unknown): data folder and tags."""
    try:
        old = os.path.join(mw.pm.profileFolder(), "one-unknown")
        new = os.path.join(mw.pm.profileFolder(), "waypoint")
        if os.path.isdir(old) and not os.path.exists(new):
            os.rename(old, new)
        own = data_dir("frequency-list")
        if not any(not f.startswith(".") for f in os.listdir(own)) and os.path.isfile(legacy_freq()):
            shutil.copy2(legacy_freq(), os.path.join(own, "frequency.txt"))   # a copy; the original stays put
        for old_tag, new_tag in OLD_TAGS.items():
            if mw.col.find_notes("tag:" + old_tag):
                mw.col.tags.rename(old_tag, new_tag)
    except Exception:
        pass


def auto():
    migrate()
    try:
        for sub in FOLDERS:
            data_dir(sub)
        names_path()
    except OSError:
        pass
    if cfg()["run_automatically"]:
        reconcile(silent=True)
    mw.toolbar.draw()


menu = QMenu("PathToFluent Waypoint", mw)
for label, fn in (("Reconcile cards", lambda: reconcile()),
                  ("Add subtitles to the bank...", add_subtitles),
                  ("Rebuild subtitle bank and reconcile", lambda: reconcile(rebuild=True)),
                  ("Show numbers", show_stats),
                  ("Mark this card known and skip", mark_known_and_skip),
                  ("Browse cards with the same unknown word", browse_same_word),
                  ("Prepare a note type for Waypoint...", prepare_note_type),
                  ("Open data folder", open_data_folder),
                  ("Open frequency-list folder", open_freq_folder),
                  ("Settings...", open_settings)):
    a = QAction(label, mw)
    a.triggered.connect(fn)
    menu.addAction(a)
mw.form.menuTools.addMenu(menu)
mw.addonManager.setConfigAction(__name__, open_settings)
gui_hooks.top_toolbar_did_init_links.append(on_toolbar)
gui_hooks.state_shortcuts_will_change.append(on_shortcuts)
gui_hooks.card_will_show.append(on_card_show)
gui_hooks.browser_will_show_context_menu.append(on_browser_menu)
gui_hooks.webview_will_show_context_menu.append(on_webview_menu)
gui_hooks.profile_did_open.append(auto)
gui_hooks.sync_did_finish.append(auto)
