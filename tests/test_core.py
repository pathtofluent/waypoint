"""Tests for Waypoint's scoring core. No Anki needed.   Run:  python3 tests/test_core.py"""
import os, sys, tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "addon"))
import core

CONF = dict(known_interval_days=21, source_known_interval_days=21, count_learning_as_known=False,
            word_weight=1.0, sentence_weight=1.0, exact_sentence_weight=0.5, chunk_weight=0.5)


def card(cid, role, sentence, type=0, ivl=0, **extra):
    return dict(cid=cid, nid=cid, role=role, sentence=sentence, labels=extra.pop("labels", ""),
                type=type, ivl=ivl, **extra)


SEED = [card(1, "source", "No lo sé.", 2, 30), card(2, "source", "Vamos a la casa.", 2, 25),
        card(3, "source", "Quiero ir.", 2, 5)]          # quiero, ir are still being learned


def plan(*cards, names=None, freq=None):
    return core.analyse(SEED + list(cards), CONF, freq, None, names)


def ids(items):
    return [x[1] for x in items]


def test_one_unknown_is_ready():
    p = plan(card(10, "managed", "Vamos a la playa."))
    assert ids(p["ready"]) == [10] and p["unknown_field"][10] == "playa"


def test_same_target_only_one_released():
    p = plan(card(10, "managed", "Vamos a la playa."), card(11, "managed", "No, vamos a la playa."))
    assert len(p["ready"]) == 1 and len(p["hold"]) == 1


def test_learning_word_holds_card():
    assert plan(card(12, "managed", "Quiero ir a la playa."))["hold"] == [12]


def test_seen_sentence_is_cleared():
    assert plan(card(13, "managed", "No lo sé."))["clear"] == [13]


def test_all_known_unseen_comes_after():
    assert ids(plan(card(14, "managed", "Lo sé, vamos."))["fallback"]) == [14]


def test_two_unknowns_hold():
    assert plan(card(15, "managed", "El murciélago no."))["hold"] == [15]


def test_names_are_ignored():
    # A name that opens the sentence is only recognised when a frequency list is loaded and lacks it.
    freq = {w: 0.5 for w in "no lo sé vamos a la casa de quiero ir".split()}
    p = plan(card(16, "managed", "Juan, vamos a la casa de María."), freq=freq)
    assert p["unknown_field"][16] == "de"


def test_labels_make_a_separate_sense():
    p = plan(card(17, "managed", "Vamos a la casa.", labels="casa=casa#company"))
    assert p["unknown_field"][17] == "casa (company)"


def test_user_suspended_is_left_alone():
    p = plan(card(18, "managed", "Vamos a la playa.", suspended=True))
    assert not p["ready"] and not p["hold"]


def test_marked_known_counts_as_known():
    p = plan(card(19, "managed", "Vamos a la playa.", known_manual=True, suspended=True, held=True),
             card(20, "managed", "La playa no."))
    assert "playa" in p["lists"]["known_words"] and ids(p["fallback"]) == [20]


def test_learn_now_goes_first():
    p = plan(card(21, "managed", "Vamos a la playa."), card(22, "managed", "El murciélago raro.", learn_now=True))
    assert ids(p["ready"]) == [22, 21]


def test_names_file():
    p = plan(card(23, "managed", "rocinante no vamos."), names={"rocinante"})
    assert ids(p["fallback"]) == [23]


def test_frequency_list_rank_order():
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "frequency.txt")
        open(path, "w", encoding="utf-8").write("de\nla\nque\nplaya\n")
        f = core.load_freq(path)
    assert f["de"] == 1.0 and f["de"] > f["la"] > f["que"] > f["playa"] > 0


def test_bank_counts_names_as_one_sentence():
    with tempfile.TemporaryDirectory() as d:
        open(os.path.join(d, "a.srt"), "w", encoding="utf-8").write(
            "1\n00:00:01,000 --> 00:00:02,000\nVen aquí, Juan.\n\n2\n00:00:03,000 --> 00:00:04,000\nVen aquí, María.\n")
        b = core.Bank.build(d)
    assert b.sents["ven aquí <name>"] == 2


def test_highlight_skips_tags_and_scripts():
    out = core.highlight('<div class="playa">La PLAYA</div><script>var playa=1</script>', ["playa (beach)"])
    assert out == '<div class="playa">La <span class="wp-new">PLAYA</span></div><script>var playa=1</script>'


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
