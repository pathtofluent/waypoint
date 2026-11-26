"""PathToFluent Waypoint - scoring logic. Pure Python, no Anki imports, so it can be tested on its own."""
import hashlib, html, math, os, pickle, re
from collections import Counter

WORD = re.compile(r"[^\W\d_]+(?:['’\-][^\W\d_]+)*|\d+(?:[.,]\d+)*")
SOUND, TAGS = re.compile(r"\[sound:[^\]]*\]"), re.compile(r"<[^>]+>")
CLOZE = re.compile(r"\{\{c\d+::(.*?)(?:::[^}]*)?\}\}")
NAME, NUM = "<name>", "<num>"
SUB_EXT = (".srt", ".vtt", ".ass", ".ssa", ".txt")


def plain(text):
    """Field or subtitle text -> plain sentence."""
    text = SOUND.sub(" ", text or "")
    text = CLOZE.sub(r"\1", text)
    text = re.sub(r"\{\\[^}]*\}", "", text)
    text = TAGS.sub(" ", text)
    text = re.sub(r"\[[^\]]*\]|[♪♫]", " ", html.unescape(text))
    return re.sub(r"\s+", " ", text).strip()


def parse_labels(text):
    """'banco=banco#bank; Juan=NAME' -> {'banco': 'banco#bank', 'juan': '<name>'}"""
    out = {}
    text = TAGS.sub("", re.sub(r"<br\s*/?>|</div>", "\n", html.unescape(text or ""), flags=re.I))
    for part in re.split(r"[;\n]", text):
        if "=" in part:
            k, v = (x.strip().lower() for x in part.split("=", 1))
            if k and v:
                out[k] = NAME if v == "name" else v
    return out


def keys(sentence, freq=None, labels=None, names=None):
    """Sentence -> list of word keys. Names and numbers become placeholders; labels override."""
    out, pos, labels = [], 0, labels or {}
    for m in WORD.finditer(sentence):
        gap, surface = sentence[pos:m.start()], m.group()
        pos, low = m.end(), m.group().lower()
        at_start = not out or bool(re.search(r"[.!?¿¡…:]|(^|\s)[-–—]\s*$", gap))
        if low in labels:
            out.append(labels[low])
        elif names and low in names:
            out.append(NAME)
        elif surface[0].isdigit():
            out.append(NUM)
        elif surface[0].isupper() and not (surface.isupper() and len(surface) > 1) and \
                ((not at_start) or (freq and low not in freq)):
            out.append(NAME)       # capitalised mid-sentence, or an opening word no dictionary knows
        else:
            out.append(low)
    return out


def content(ks):
    return [k for k in ks if k not in (NAME, NUM)]


def show(key):
    return "%s (%s)" % tuple(key.split("#", 1)) if "#" in key else key


# ── frequency list ──────────────────────────────────────────────────────────
def load_freq(path):
    """Accepts 'word count', 'word<TAB>count', 'word,count' or one word per line in rank order.
    Returns {word: weight between 0 and 1}."""
    rows = []
    with open(path, encoding="utf-8-sig", errors="replace") as f:
        for line in f:
            parts = [p for p in re.split(r"[\s,;]+", line.strip()) if p]
            if not parts:
                continue
            word = next((p for p in parts if not re.fullmatch(r"[\d.]+", p)), None)
            num = next((p for p in parts if re.fullmatch(r"\d+(\.\d+)?", p)), None)
            if word:
                rows.append((word.lower(), float(num) if num else None))
    if not rows:
        return {}
    counted = sum(1 for _, n in rows if n is not None) > len(rows) * 0.8
    values = [n for _, n in rows if n is not None]
    # a 'rank word' file has small ascending numbers; a 'word count' file has large descending ones
    is_count = counted and len(values) > 1 and values[0] >= values[-1] and max(values) > len(rows)
    out, top = {}, max(values) if is_count else 0
    for i, (w, n) in enumerate(rows):
        if w in out:
            continue
        out[w] = (math.log1p(n or 0) / math.log1p(top)) if is_count else 1 - math.log1p(i) / math.log1p(len(rows))
    return out


# ── subtitle bank ───────────────────────────────────────────────────────────
CUE = re.compile(r"(?:\d+:)?\d{1,2}:\d{1,2}[.,]\d{1,3}\s*-->")


def read_lines(path):
    data = open(path, "rb").read()
    for enc in ("utf-8-sig", "utf-16", "cp1252"):
        try:
            text = data.decode(enc)
            break
        except (UnicodeDecodeError, UnicodeError):
            continue
    else:
        text = data.decode("utf-8", "replace")
    ext, out, cur = os.path.splitext(path)[1].lower(), [], None
    for line in text.replace("\r", "").split("\n"):
        s = line.strip()
        if ext in (".ass", ".ssa"):
            if s.lower().startswith("dialogue:"):
                out.append(re.sub(r"\\[Nnh]", " ", s.split(",", 9)[-1]))
        elif ext == ".txt":
            if s:
                out.append(s)
        elif CUE.search(s):
            cur = []
            out.append(cur)
        elif not s:
            cur = None
        elif cur is not None:
            cur.append(s)
    return [plain(" ".join(x) if isinstance(x, list) else x) for x in out]


def folder_signature(folder):
    h = hashlib.sha1()
    for root, _, files in sorted(os.walk(folder)):
        for f in sorted(files):
            if f.lower().endswith(SUB_EXT):
                st = os.stat(os.path.join(root, f))
                h.update(("%s|%d|%d;" % (os.path.join(root, f), st.st_size, int(st.st_mtime))).encode())
    return h.hexdigest()


class Bank:
    def __init__(self):
        self.sig, self.files, self.total = "", 0, 0
        self.words, self.sents, self.bi, self.tri = Counter(), Counter(), Counter(), Counter()

    def add(self, sentence, freq=None, names=None):
        ks = keys(sentence, freq, None, names)
        if not ks:
            return
        self.total += 1
        self.sents[" ".join(ks)] += 1
        self.words.update(content(ks))
        self.bi.update(zip(ks, ks[1:]))
        self.tri.update(zip(ks, ks[1:], ks[2:]))

    def finish(self):
        for name in ("sents", "bi", "tri"):       # singletons carry no signal and are most of the size
            setattr(self, name, Counter({k: v for k, v in getattr(self, name).items() if v > 1}))
        self.mx = {n: max(getattr(self, n).values(), default=0) for n in ("words", "sents", "bi", "tri")}

    @classmethod
    def build(cls, folder, freq=None, tick=None, names=None):
        b = cls()
        b.sig = cls.signature(folder, names)
        for root, _, files in sorted(os.walk(folder)):
            for f in sorted(files):
                if f.lower().endswith(SUB_EXT):
                    b.files += 1
                    if tick:
                        tick(b.files, f)
                    try:
                        for line in read_lines(os.path.join(root, f)):
                            b.add(line, freq, names)
                    except OSError:
                        pass
        b.finish()
        return b

    @staticmethod
    def signature(folder, names=None):
        return folder_signature(folder) + hashlib.sha1("|".join(sorted(names or ())).encode()).hexdigest()[:8]

    @classmethod
    def load_or_build(cls, folder, index_path, freq=None, force=False, tick=None, names=None):
        if not folder or not os.path.isdir(folder):
            return None
        if not force and os.path.exists(index_path):
            try:
                b = pickle.load(open(index_path, "rb"))
                if b.sig == cls.signature(folder, names):
                    return b
            except Exception:
                pass
        b = cls.build(folder, freq, tick, names)
        pickle.dump(b, open(index_path, "wb"), protocol=4)
        return b

    @staticmethod
    def _lw(count, top):
        return math.log1p(count) / math.log1p(top) if count > 0 and top > 0 else 0.0

    def word(self, key):
        return self._lw(self.words.get(key, 0), self.mx["words"])

    def sentence(self, ks, exact_weight=0.5, chunk_weight=0.5):
        exact = self._lw(self.sents.get(" ".join(ks), 0), self.mx["sents"])
        grams = [self._lw(self.bi.get(g, 0), self.mx["bi"]) for g in zip(ks, ks[1:])] + \
                [self._lw(self.tri.get(g, 0), self.mx["tri"]) for g in zip(ks, ks[1:], ks[2:])]
        chunk = sum(grams) / len(grams) if grams else exact
        return exact_weight * exact + chunk_weight * chunk


# ── the decision ────────────────────────────────────────────────────────────
def analyse(cards, conf, freq=None, bank=None, names=None):
    """cards: dicts with cid, nid, role ('source'|'managed'), sentence, labels, type (0 = new),
    ivl (days), suspended, held, cleared, known_manual, learn_now.
    The cards are the source of truth: known and learning words are worked out from them on every run.
    Returns the plan for the managed cards."""
    freq = freq or {}
    known, learning, seen, known_sents, parsed = set(), set(), set(), set(), {}
    for c in cards:
        ks = keys(plain(c["sentence"]), freq, parse_labels(c.get("labels", "")), names)
        parsed[c["cid"]] = ks
        need = conf["source_known_interval_days"] if c["role"] == "source" else conf["known_interval_days"]
        if c.get("known_manual") or (c["type"] == 2 and c["ivl"] >= need):
            known.update(content(ks))                        # mature, or marked known by hand
            known_sents.add(" ".join(ks))
            seen.add(" ".join(ks))
        elif c["type"] != 0:                                 # studied, not yet mature
            learning.update(content(ks))
            seen.add(" ".join(ks))
    learning -= known

    def word_weight(key):
        base = key.split("#", 1)[0]
        if base in freq:
            return freq[base]
        return bank.word(base) if bank else 0.0

    def sent_weight(ks):
        return bank.sentence(ks, conf["exact_sentence_weight"], conf["chunk_weight"]) if bank else 0.0

    ready, fallback, hold, clear, field, forced = [], [], [], [], {}, []
    for c in cards:
        if c["role"] != "managed" or c["type"] != 0 or c.get("cleared") or c.get("known_manual") or \
                (c.get("suspended") and not c.get("held")):
            continue
        ks = parsed[c["cid"]]
        uniq = list(dict.fromkeys(content(ks)))
        unknown = [k for k in uniq if k not in known and k not in learning]
        in_progress = [] if conf.get("count_learning_as_known") else [k for k in uniq if k in learning]
        field[c["nid"]] = ", ".join(show(k) for k in unknown)
        s = sent_weight(ks)
        if c.get("learn_now"):
            forced.append((99.0, c["cid"], "learn now"))
        elif len(unknown) == 1 and not in_progress:
            score = conf["word_weight"] * word_weight(unknown[0]) + conf["sentence_weight"] * s
            ready.append((score, c["cid"], unknown[0]))
        elif not unknown and not in_progress:
            (clear if " ".join(ks) in seen else fallback).append((s, c["cid"], " ".join(ks)))
        else:
            hold.append(c["cid"])

    def best_per(items):                                     # one card per target word / per sentence
        kept, taken = [], set()
        for score, cid, what in sorted(items, key=lambda x: (-x[0], x[1])):
            if what in taken:
                hold.append(cid)
            else:
                taken.add(what)
                kept.append((score, cid, what))
        return kept

    ready, fallback = forced + best_per(ready), best_per(fallback)
    return {"ready": ready, "fallback": fallback, "hold": hold, "clear": [cid for _, cid, _ in clear],
            "unknown_field": field,
            "lists": {"known_words": sorted(known), "learning_words": sorted(learning),
                      "known_sentences": sorted(known_sents)},
            "stats": {"known_words": len(known), "learning_words": len(learning), "known_sentences": len(known_sents), "seen_sentences": len(seen),
                      "ready": len(ready), "fallback": len(fallback), "held": len(hold), "cleared": len(clear)}}


# ── highlighting ────────────────────────────────────────────────────────────
def highlight(page, words, css_class="wp-new"):
    """Wrap each of `words` in a span wherever it appears as visible text in an HTML page."""
    words = [w.split(" (")[0].split("#")[0].strip() for w in words]
    words = sorted({w for w in words if w}, key=len, reverse=True)
    if not words:
        return page
    pattern = re.compile(r"(?<![^\W\d_])(%s)(?![^\W\d_])" % "|".join(re.escape(w) for w in words), re.I)
    out, skipping = [], False
    for part in re.split(r"(<[^>]*>)", page):
        if part.startswith("<"):
            tag = part[1:9].lower()
            if tag.startswith(("script", "style")):
                skipping = True
            elif tag.startswith(("/script", "/style")):
                skipping = False
            out.append(part)
        else:
            out.append(part if skipping else pattern.sub(r'<span class="%s">\1</span>' % css_class, part))
    return "".join(out)
