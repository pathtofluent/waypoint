"""PathToFluent Waypoint - the labels hand-off. Pure Python, no Anki imports.

Waypoint writes TO_LABEL (cards whose words need a second look) into a folder the user chooses.
Something else - a person, a script, an AI assistant - writes ANSWERS beside it.
Waypoint reads the answers the next time it runs and stores them in each card's Labels field.
"""
import json, re
from urllib.parse import quote

TO_LABEL, ANSWERS, IMPORTED, HOWTO = ("waypoint_to_label.json", "waypoint_labels.json",
                                      "waypoint_labels.imported.json", "HOW-TO-LABEL.md")
WORD = re.compile(r"[^\W\d_]+(?:['’\-][^\W\d_]+)*")
SENSE = re.compile(r"[a-z0-9][a-z0-9\-]{0,29}")
LEMMA = re.compile(r"[^\W\d_]+(?:[ '’\-][^\W\d_]+){0,4}")
MAX_DEFINITION = 400

DEFAULT_GOAL = ("Everyday conversation: carrying on day-to-day conversations with ease and expressing "
                "one's thoughts at the level of a university-educated adult.")

HOWTO_TEXT = """# How to label Waypoint cards

Waypoint tracks words by their spelling. Two things spelling can't tell it:

1. **Names.** "Juan" or "Zaragoza" should not count as words to learn.
2. **Second meanings.** "banco" can be a bench or a bank. Knowing one is not knowing the other.

`waypoint_to_label.json` lists cards to check. For each card, read the sentence and decide:

- If a word is the name of a person, place, brand or title, label it `NAME`.
- A label belongs to this card only. An ordinary word used as a nickname ("Oye, Flaco") is `NAME`
  here, and stays an ordinary word on every other card. Judge each sentence on its own.
- Inside the full name of an institution, company, work or place ("Fábrica Nacional de Moneda y
  Timbre"), do not give any word a `word#gloss` label. If the title's first word opens the sentence,
  label that word `NAME`; leave the rest alone.
- If a word has more than one clearly different meaning, and this sentence uses a meaning OTHER than
  the word's most common one, label it `word#gloss`, where gloss is a short lower-case English hint
  (letters, digits, hyphens; 30 characters at most), for example `banco#bank` or `banco#river-bank`.
- If a word is used in its most common meaning, do not label it. Most words need no label.
- Check `senses` first: it lists the glosses already in use for each word. Reuse one if it fits,
  so the same meaning always gets the same label.
- Label the exact form that appears in the sentence: `bancos` gets `bancos#bank`, not `banco#bank`.

## Usefulness

Also rate each sentence from 1 to 5 for how useful it is to learn, judged against the learner's
goal. The goal is given as `goal` in `waypoint_to_label.json`.

- **5** A complete, natural sentence the learner could plausibly say or hear in the situations the
  goal describes, and reuse widely.
- **4** Natural and reusable, but tied to a more specific situation.
- **3** Ordinary. Fine to learn, nothing special, or it leans on context to make sense.
- **2** A fragment, mostly interjection, or tied to a narrow setting such as police procedure,
  fantasy or technical jargon.
- **1** Not worth learning from: a bare exclamation, a name being called, a cut-off or garbled line,
  a song lyric.

Rate the sentence itself, not how common its words are; Waypoint already counts that. Use the whole
scale, and hold the same standard from one batch to the next.

## Definitions

Some cards list `"definition"` under `needs`. Each of those has exactly one word in `unknown`: the
word the card will teach. For that word, as it is used in this sentence, give:

- `word`: the word exactly as it appears in `unknown`.
- `lemma`: its dictionary form (the infinitive of a verb, the singular of a noun), so it can be
  looked up. For a set phrase, the phrase's usual dictionary form.
- `en`: a short definition in English for THIS meaning. A gloss or a few words is ideal; add a brief
  note only if the form itself needs one ("you plural, informal").
- `es`: a short definition written in the language being learned, in plain words a learner at this
  stage could follow, for THIS meaning. Write it yourself. Do not copy a dictionary's entry.

Keep each to one or two lines, 400 characters at most, plain text with no formatting.
If the word in `unknown` is a name, label it `NAME` and send no definition for that card.
If a card needs only a definition, you don't need to send its labels or rating again.

## Answers

Write your answers to `waypoint_labels.json` in the same folder, in this shape:

```json
{
  "labels": {
    "1700000000001": {"banco": "banco#bank", "Juan": "NAME"},
    "1700000000002": {}
  },
  "usefulness": {
    "1700000000001": 4,
    "1700000000002": 2
  },
  "definitions": {
    "1700000000001": {"word": "banco", "lemma": "banco",
                      "en": "bank (where money is kept)",
                      "es": "Lugar donde la gente guarda su dinero y pide préstamos."}
  }
}
```

- The keys are the card `id` values from `waypoint_to_label.json`, as text.
- Include every card you checked in `labels`. Use `{}` when nothing needs a label; that tells
  Waypoint the card has been looked at, so it is not sent again.
- `usefulness` is a whole number from 1 to 5 per card. Leave a card out if you can't judge it.
- `definitions` holds the cards whose `needs` includes `"definition"`.
- A card whose `needs` is only `["definition"]` has been labelled already: leave it out of `labels`.
- Do not change `waypoint_to_label.json`. Waypoint rewrites it each time it runs.
- A sentence that sits on several cards is listed once. Waypoint gives your answer to the others.
- Card ids change when a deck is imported again. If you reuse an earlier answer for a sentence you
  have seen before, match it by the sentence's exact text, never by any part of the id.

Waypoint ignores any label that names a word not in the sentence or that is not in one of the
two forms above.
"""


def words_of(sentence):
    return {m.group().lower() for m in WORD.finditer(sentence or "")}


def add_names(existing, selection, sentence):
    """Mark the selected words as names on one card. existing: the card's Labels field as stored
    ('a=a#x; b=NAME'). Only words present in the sentence count.
    Returns (new field text, the words marked)."""
    present = words_of(sentence)
    picked = []
    for m in WORD.finditer(selection or ""):
        w = m.group().lower()
        if w in present and w not in picked:
            picked.append(w)
    parts = {}
    text = re.sub(r"<[^>]+>", "", re.sub(r"<br\s*/?>|</div>", "\n", existing or "", flags=re.I))
    for part in re.split(r"[;\n]", text):
        if "=" in part:
            k, v = (x.strip() for x in part.split("=", 1))
            if k and v:
                parts[k.lower()] = v
    for w in picked:
        parts[w] = "NAME"
    return "; ".join("%s=%s" % kv for kv in parts.items()), picked


def senses_in_use(label_maps):
    """label_maps: iterable of dicts as produced by core.parse_labels. Returns {word: [glosses]}."""
    out = {}
    for labels in label_maps:
        for word, value in labels.items():
            if "#" in value:
                base, gloss = value.split("#", 1)
                if base == word and gloss and gloss not in out.setdefault(word, []):
                    out[word].append(gloss)
    return {w: sorted(g) for w, g in sorted(out.items())}


def build_export(cards, senses, language, limit, goal=DEFAULT_GOAL):
    """cards: dicts with id, sentence, unknown (list of words), in priority order."""
    waiting = len(cards)
    batch = [{"id": str(c["id"]), "sentence": c["sentence"], "unknown": list(c.get("unknown") or []),
              "needs": list(c.get("needs") or ["labels"])}
             for c in cards[:max(0, int(limit))]]
    return {"version": 1, "language": language, "instructions": "See %s in this folder." % HOWTO,
            "answers_file": ANSWERS, "goal": goal or DEFAULT_GOAL, "waiting_in_total": waiting, "cards": batch, "senses": senses}


def one_per_sentence(cards):
    """cards: dicts with sentence and needs, in priority order. Keeps the first card for each distinct
    sentence and need, so the same line is never sent twice. The answer is shared out on the way in."""
    kept, taken = [], set()
    for c in cards:
        key = (c["sentence"].strip(), tuple(c.get("needs") or ()))
        if key not in taken:
            taken.add(key)
            kept.append(c)
    return kept


def share_answers(data, sentences, wants):
    """Give each answer to the other cards that hold exactly the same sentence.
    sentences: {note id (int): plain sentence} for every sorted note.
    wants: {note id: set of 'labels', 'usefulness', 'definitions'} - what that note still lacks.
    A card that was answered itself is never overridden. Returns (data with the extra entries, cards added)."""
    if not isinstance(data, dict):
        return data, 0
    by_text = {}
    for nid, text in sentences.items():
        by_text.setdefault(text.strip(), []).append(nid)
    out, added = dict(data), set()
    for name in ("labels", "usefulness", "definitions"):
        table = data.get(name)
        if not isinstance(table, dict):
            continue
        grown = dict(table)
        for key, value in table.items():
            try:
                nid = int(key)
            except (TypeError, ValueError):
                continue
            for twin in by_text.get(sentences.get(nid, "\0").strip(), ()):
                if twin != nid and str(twin) not in grown and name in wants.get(twin, ()):
                    grown[str(twin)] = value
                    added.add(twin)
        out[name] = grown
    return out, len(added)


def clean_label(word, value, sentence_words):
    """Return the label in stored form ('word#gloss' or '<name marker>'), or None if it isn't valid."""
    if not isinstance(word, str) or not isinstance(value, str):
        return None
    word, value = word.strip().lower(), value.strip()
    if not WORD.fullmatch(word) or word not in sentence_words:
        return None
    if value.upper() == "NAME":
        return "NAME"
    base, _, gloss = value.lower().partition("#")
    if base == word and SENSE.fullmatch(gloss or ""):
        return "%s#%s" % (word, gloss)
    return None


def parse_answers(data, sentences):
    """data: the parsed answers file. sentences: {card id (int): sentence}.
    Returns ({card id: 'a=a#x; b=NAME' or ''}, number of labels rejected, number of unknown card ids)."""
    out, rejected, strangers = {}, 0, 0
    table = data.get("labels") if isinstance(data, dict) else None
    if not isinstance(table, dict):
        return out, rejected, strangers
    for key, labels in table.items():
        try:
            cid = int(key)
        except (TypeError, ValueError):
            strangers += 1
            continue
        if cid not in sentences:
            strangers += 1
            continue
        present, parts = words_of(sentences[cid]), []
        for word, value in sorted((labels or {}).items()) if isinstance(labels, dict) else []:
            good = clean_label(word, value, present)
            if good is None:
                rejected += 1
            else:
                parts.append("%s=%s" % (word.strip().lower(), good))
        out[cid] = "; ".join(parts)
    return out, rejected, strangers


def load_answers(path):
    with open(path, encoding="utf-8-sig") as f:
        return json.load(f)


def parse_usefulness(data, known_ids):
    """Returns ({card id: rating 1-5}, number of ratings rejected). Only whole numbers 1 to 5 count."""
    out, rejected = {}, 0
    table = data.get("usefulness") if isinstance(data, dict) else None
    if not isinstance(table, dict):
        return out, rejected
    for key, value in table.items():
        try:
            cid = int(key)
        except (TypeError, ValueError):
            rejected += 1
            continue
        if cid in known_ids and isinstance(value, int) and not isinstance(value, bool) and 1 <= value <= 5:
            out[cid] = value
        else:
            rejected += 1
    return out, rejected


def base_word(text):
    """'banco (bank)' or 'banco#bank' -> 'banco'."""
    return re.split(r"\s*\(|#", (text or "").strip().lower(), 1)[0].strip()


def _clean_text(value):
    if not isinstance(value, str):
        return None
    value = re.sub(r"\s+", " ", value).strip()
    return value if 0 < len(value) <= MAX_DEFINITION and "<" not in value and ">" not in value else None


def parse_definitions(data, targets):
    """targets: {card id: the card's single unknown word}. Returns ({card id: {word, lemma, en, es}}, rejected).
    A definition is kept only if it is for that card's unknown word, has a usable lemma, and gives at
    least one of en / es as plain text of reasonable length."""
    out, rejected = {}, 0
    table = data.get("definitions") if isinstance(data, dict) else None
    if not isinstance(table, dict):
        return out, rejected
    for key, entry in table.items():
        try:
            cid = int(key)
        except (TypeError, ValueError):
            rejected += 1
            continue
        if cid not in targets or not isinstance(entry, dict):
            rejected += 1
            continue
        word = entry.get("word")
        lemma = entry.get("lemma")
        lemma = re.sub(r"\s+", " ", lemma).strip().lower() if isinstance(lemma, str) else ""
        en, es = _clean_text(entry.get("en")), _clean_text(entry.get("es"))
        if not isinstance(word, str) or base_word(word) != base_word(targets[cid]) or not base_word(word) \
                or not LEMMA.fullmatch(lemma) or len(lemma) > 60 or not (en or es) \
                or (entry.get("en") is not None and en is None) or (entry.get("es") is not None and es is None):
            rejected += 1
            continue
        out[cid] = {"word": base_word(word), "lemma": lemma, "en": en or "", "es": es or ""}
    return out, rejected


def dictionary_link(pattern, name, lemma):
    """An HTML link to the lemma's dictionary page, or '' if no pattern is set."""
    if not pattern or "{lemma}" not in pattern or not pattern.lower().startswith(("https://", "http://")):
        return ""
    url = pattern.replace("{lemma}", quote(lemma, safe=""))
    label = "%s: %s" % (name, lemma) if name else lemma
    return '<a href="%s">%s</a>' % (url.replace('"', "%22"), label.replace("<", "").replace(">", ""))
