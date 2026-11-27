"""Tests for Waypoint's labels hand-off. No Anki needed.   Run:  python3 tests/test_labels.py"""
import os, sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "addon"))
import core, labels

SENTENCES = {1: "Juan se sienta en el banco.", 2: "Vamos al banco a por dinero.", 3: "No lo sé."}


def test_valid_labels_are_kept_in_stored_form():
    out, rejected, strangers = labels.parse_answers(
        {"labels": {"1": {"Juan": "NAME"}, "2": {"banco": "banco#bank"}, "3": {}}}, SENTENCES)
    assert out == {1: "juan=NAME", 2: "banco=banco#bank", 3: ""} and rejected == 0 and strangers == 0


def test_checked_cards_with_nothing_to_label_are_recorded():
    out, _, _ = labels.parse_answers({"labels": {"3": {}}}, SENTENCES)
    assert out == {3: ""}


def test_bad_labels_are_rejected():
    bad = {"labels": {"2": {
        "playa": "playa#beach",                 # word not in the sentence
        "banco": "bank",                        # not word#gloss
        "dinero": "dinero#<script>alert(1)",    # characters outside the allowed set
        "vamos": "van#go",                      # gloss attached to a different word
        "al": 7,                                # not text
    }}}
    out, rejected, _ = labels.parse_answers(bad, SENTENCES)
    assert out == {2: ""} and rejected == 5


def test_unknown_cards_and_junk_are_ignored():
    out, _, strangers = labels.parse_answers({"labels": {"99": {"x": "NAME"}, "abc": {}}}, SENTENCES)
    assert out == {} and strangers == 2
    assert labels.parse_answers(["not", "a", "dict"], SENTENCES)[0] == {}
    assert labels.parse_answers({"labels": "nope"}, SENTENCES)[0] == {}


def test_stored_form_is_understood_by_the_scoring_core():
    out, _, _ = labels.parse_answers({"labels": {"1": {"Juan": "NAME", "banco": "banco#bench"}}}, SENTENCES)
    parsed = core.parse_labels(out[1])
    assert parsed == {"juan": core.NAME, "banco": "banco#bench"}
    assert core.keys(SENTENCES[1], None, parsed) == [core.NAME, "se", "sienta", "en", "el", "banco#bench"]


def test_senses_in_use():
    maps = [core.parse_labels("banco=banco#bank; juan=NAME"), core.parse_labels("banco=banco#river-bank"),
            core.parse_labels("banco=banco#bank")]
    assert labels.senses_in_use(maps) == {"banco": ["bank", "river-bank"]}


def test_export_respects_the_limit_and_reports_the_backlog():
    cards = [{"id": i, "sentence": "s%d" % i, "unknown": ["w"]} for i in range(10)]
    doc = labels.build_export(cards, {"banco": ["bank"]}, "es", 3)
    assert [c["id"] for c in doc["cards"]] == ["0", "1", "2"] and doc["waiting_in_total"] == 10
    assert doc["senses"] == {"banco": ["bank"]} and doc["language"] == "es"


def test_usefulness_accepts_only_whole_numbers_one_to_five():
    data = {"usefulness": {"1": 5, "2": 1, "3": 0, "99": 4, "abc": 3}}
    out, rejected = labels.parse_usefulness(data, {1, 2, 3})
    assert out == {1: 5, 2: 1} and rejected == 3
    assert labels.parse_usefulness({"usefulness": {"1": "5", "2": 2.5, "3": True}}, {1, 2, 3}) == ({}, 3)
    assert labels.parse_usefulness({}, {1}) == ({}, 0)


def test_usefulness_moves_a_card_up_without_overriding_the_counts():
    conf = dict(known_interval_days=21, source_known_interval_days=21, count_learning_as_known=False,
                word_weight=1.0, sentence_weight=1.0, exact_sentence_weight=0.5, chunk_weight=0.5,
                usefulness_weight=0.25)
    card = lambda cid, s, **k: dict(cid=cid, nid=cid, role="managed", sentence=s, labels="", type=0, ivl=0, **k)
    seed = [dict(cid=1, nid=1, role="source", sentence="Vamos a la casa.", labels="", type=2, ivl=30)]
    freq = {"playa": 0.50, "mesa": 0.45, "raro": 0.05, "silla": 0.30}
    order = lambda *cards: [c for _, c, _ in core.analyse(seed + list(cards), conf, freq)["ready"]]
    # equal otherwise: the higher-rated sentence goes first, and an unrated one sits in the middle
    assert order(card(10, "Vamos a la playa.", usefulness=1), card(11, "Vamos a la mesa.", usefulness=5)) == [11, 10]
    assert order(card(10, "Vamos a la playa.", usefulness=2), card(11, "Vamos a la mesa.")) == [11, 10]
    # a top rating does not lift a rare word over a common one...
    assert order(card(10, "Vamos a la playa.", usefulness=1), card(12, "Vamos a la raro.", usefulness=5)) == [10, 12]
    # ...but it does lift a somewhat less common word over a somewhat more common one
    assert order(card(10, "Vamos a la playa.", usefulness=1), card(13, "Vamos a la silla.", usefulness=5)) == [13, 10]


def test_export_carries_the_goal():
    assert labels.build_export([], {}, "es", 5)["goal"] == labels.DEFAULT_GOAL
    assert labels.build_export([], {}, "es", 5, "Reading novels")["goal"] == "Reading novels"


def test_definitions_are_kept_only_for_the_cards_unknown_word():
    targets = {1: "banco", 2: "banco (bank)", 3: "sé"}
    data = {"definitions": {
        "1": {"word": "banco", "lemma": "banco", "en": "bench", "es": "Asiento largo para varias personas."},
        "2": {"word": "banco", "lemma": "banco", "en": "bank"},                       # es may be left out
        "3": {"word": "saber", "lemma": "saber", "en": "to know"},                     # not this card's word
    }}
    out, rejected = labels.parse_definitions(data, targets)
    assert out[1] == {"word": "banco", "lemma": "banco", "en": "bench", "es": "Asiento largo para varias personas."}
    assert out[2]["es"] == "" and 3 not in out and rejected == 1


def test_bad_definitions_are_rejected():
    targets = {1: "banco"}
    bad = [
        {"word": "banco", "lemma": "banco", "en": "<b>bank</b>"},                      # markup
        {"word": "banco", "lemma": "banco", "en": "x" * 401},                          # too long
        {"word": "banco", "lemma": "banco"},                                           # no definition at all
        {"word": "banco", "lemma": "ban<co", "en": "bank"},                            # lemma isn't a word
        {"word": "banco", "lemma": "banco", "en": "bank", "es": 7},                    # not text
        "bank",                                                                         # not an entry
    ]
    for entry in bad:
        assert labels.parse_definitions({"definitions": {"1": entry}}, targets) == ({}, 1), entry
    assert labels.parse_definitions({"definitions": {"9": {"word": "x", "lemma": "x", "en": "y"}}}, targets) == ({}, 1)
    assert labels.parse_definitions({}, targets) == ({}, 0)


def test_phrase_lemmas_and_dictionary_links():
    out, _ = labels.parse_definitions(
        {"definitions": {"1": {"word": "cuenta", "lemma": "Darse  cuenta", "en": "to realise"}}}, {1: "cuenta"})
    assert out[1]["lemma"] == "darse cuenta"
    link = labels.dictionary_link("https://dle.rae.es/{lemma}", "RAE", "darse cuenta")
    assert link == '<a href="https://dle.rae.es/darse%20cuenta">RAE: darse cuenta</a>'
    assert labels.dictionary_link("https://dle.rae.es/{lemma}", "RAE", "niño") == \
        '<a href="https://dle.rae.es/ni%C3%B1o">RAE: niño</a>'
    assert labels.dictionary_link("", "RAE", "x") == "" and labels.dictionary_link("javascript:{lemma}", "", "x") == ""


def test_export_says_what_each_card_needs():
    cards = [{"id": 1, "sentence": "a", "unknown": ["w"], "needs": ["labels", "definition"]},
             {"id": 2, "sentence": "b", "unknown": ["w", "v"]}]
    doc = labels.build_export(cards, {}, "es", 10)
    assert [c["needs"] for c in doc["cards"]] == [["labels", "definition"], ["labels"]]


def test_add_names_marks_this_card_only():
    assert labels.add_names("", "Flaco", "Oye, Flaco, ven aquí.") == ("flaco=NAME", ["flaco"])
    assert labels.add_names("banco=banco#bank", "Río", "Río va al banco.") == ("banco=banco#bank; río=NAME", ["río"])
    assert labels.add_names("flaco=flaco#thin", "Flaco", "Oye, Flaco.") == ("flaco=NAME", ["flaco"])
    assert labels.add_names("banco=banco#bank", "Madrid", "Vamos al banco.") == ("banco=banco#bank", [])


def test_label_for_a_caption_word_is_rejected():
    import core
    out, rejected, _ = labels.parse_answers({"labels": {"1": {"mujer": "NAME"}}}, {1: core.plain("(MUJER) Hola.")})
    assert out == {1: ""} and rejected == 1


if __name__ == "__main__":
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_")]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print("ok    ", name)
        except AssertionError as e:
            failed += 1
            print("FAILED", name, e)
    print("%d passed, %d failed" % (len(tests) - failed, failed))
    sys.exit(1 if failed else 0)
