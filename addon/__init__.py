"""
PathToFluent Waypoint - an Anki add-on.

Sorts the new cards of your sentence decks so the next card is always the most
useful sentence containing exactly one word you don't know yet.

  * Read-only decks (e.g. an Assimil deck) are never touched; as you learn their
    cards, their words and sentences count as known.
  * Sorted decks (e.g. your SubDeck decks) are scored, sorted, held back or cleared.

Tools > Waypoint > Settings to choose the decks and files.
It runs when Anki opens, after each sync, and from Tools > Waypoint > Reconcile cards.
"""
import json
import os
import re

from aqt import dialogs, gui_hooks, mw
from aqt.qt import *
from aqt.utils import openFolder, showInfo, showWarning, tooltip

from . import core

VERSION = "0.3.1"
HELD, CLEARED, KNOWN, LEARN_NOW = "waypoint_held", "waypoint_cleared", "waypoint_known", "waypoint_learn_now"
OLD_TAGS = {"ou_held": HELD, "ou_cleared": CLEARED, "ou_known": KNOWN, "ou_learn_now": LEARN_NOW}
FIRST = "(first field)"
DEFAULTS = {
    "source_decks": {},                 # {"Deck name": "Field holding the sentence"}  ("" = first field)
    "managed_decks": [],                # decks whose new cards are sorted
    "managed_note_types": ["PathToFluent Trailblazer", "SubDeck"],  # used only when managed_decks is empty
    "sentence_field": "Sentence",
    "unknown_field": "Unknown Words",
    "labels_field": "Labels",
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


def dbs_dir():
    """<profile>/dbs, the same place MorphMan-style add-ons look for frequency.txt."""
    d = os.path.join(mw.pm.profileFolder(), "dbs")
    os.makedirs(d, exist_ok=True)
    return d


def default_freq():
    """dbs/frequency.txt first, then the first file in waypoint/frequency-list."""
    path = os.path.join(dbs_dir(), "frequency.txt")
    if os.path.isfile(path):
        return path
    folder = data_dir("frequency-list")
    files = sorted(f for f in os.listdir(folder) if not f.startswith("."))
    return os.path.join(folder, files[0]) if files else ""


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


def get_bank(conf, freq, force=False, names=None):
    folder = os.path.expanduser(conf["subtitle_bank_folder"] or "") or data_dir("subtitle-bank")
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
                          "known_manual": KNOWN in tagset, "learn_now": LEARN_NOW in tagset})
    for deck, fld in conf["source_decks"].items():
        for cid, nid, ctype, queue, ivl, mid, flds, tags in rows(mw.col.find_cards("deck:" + quoted(deck))):
            if cid in seen:
                continue
            o = pick_ord(mid, [fld, "Expression", "Sentence"]) if fld else 0
            cards.append({"cid": cid, "nid": nid, "mid": mid, "role": "source",
                          "sentence": flds.split("\x1f")[o or 0], "labels": "", "type": ctype, "ivl": ivl,
                          "known_manual": KNOWN in tags.split()})
    return cards, missing


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
    showInfo(text + "\nFrequency file: %s" % s.get("frequency_file", "(run Reconcile to see)"), title="PathToFluent Waypoint")


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
        self.freq.setPlaceholderText("Blank = dbs/frequency.txt in your profile folder")
        form.addRow("Frequency list file", self.with_button(self.freq, self.pick_file))
        self.bank = QLineEdit(conf["subtitle_bank_folder"])
        self.bank.setPlaceholderText("Blank = the subtitle-bank folder")
        form.addRow("Subtitle bank folder", self.with_button(self.bank, self.pick_folder))

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

    def save(self):
        source, managed = self.checked(self.source), self.checked(self.managed)
        both = sorted(set(source) & set(managed))
        if both:
            showWarning("A deck can't be both read-only and sorted:\n" + "\n".join(both))
            return
        field = self.source_field.currentText()
        conf = cfg()
        conf.update({
            "source_decks": {d: ("" if field == FIRST else field) for d in source},
            "managed_decks": managed,
            "sentence_field": self.sentence_field.currentText(),
            "frequency_list": self.freq.text().strip(),
            "subtitle_bank_folder": self.bank.text().strip(),
            "known_interval_days": self.days.value(),
            "source_known_interval_days": self.source_days.value(),
            "run_automatically": self.auto.isChecked(),
        })
        mw.addonManager.writeConfig(__name__, conf)
        self.accept()
        reconcile()


def open_settings():
    Settings(mw).exec()


def open_data_folder():
    for sub in FOLDERS:
        data_dir(sub)
    openFolder(data_dir())


def open_dbs_folder():
    openFolder(dbs_dir())


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
        dbs_dir()
        names_path()
    except OSError:
        pass
    if cfg()["run_automatically"]:
        reconcile(silent=True)
    mw.toolbar.draw()


menu = QMenu("PathToFluent Waypoint", mw)
for label, fn in (("Reconcile cards", lambda: reconcile()),
                  ("Rebuild subtitle bank and reconcile", lambda: reconcile(rebuild=True)),
                  ("Show numbers", show_stats),
                  ("Mark this card known and skip", mark_known_and_skip),
                  ("Browse cards with the same unknown word", browse_same_word),
                  ("Open data folder", open_data_folder),
                  ("Open dbs folder (frequency.txt goes here)", open_dbs_folder),
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
