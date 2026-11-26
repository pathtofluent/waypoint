"""Tests for Waypoint's subtitle gatherer. No Anki needed.   Run:  python3 tests/test_gather.py"""
import os, sys, tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "addon"))
import gather

ES = ["No lo sé, pero creo que es muy tarde.", "¿Qué vamos a hacer ahora con todo esto?",
      "Yo no quiero ir a la casa de ella.", "Está bien, pero tengo que hablar con él.",
      "Si me lo dices, te lo voy a dar."] * 6
EN = ["I don't know what you want me to do.", "We have to get out of here right now.",
      "This is not what I was looking for.", "Do you know where they are going?",
      "He was there with all of them."] * 6
PT = ["Eu não sei o que você quer de mim.", "Ele está aqui com a minha mãe agora.",
      "Isso não é o que eu estava a dizer.", "Vamos para casa, mas não muito tarde.",
      "Você tem que falar com ele já."] * 6
FR = ["Je ne sais pas ce que vous voulez.", "Il est dans la maison avec nous.",
      "Tu as bien fait, mais ce n'est pas tout.", "On va faire ça pour toi et moi.",
      "Qui est avec elle dans la voiture ?"] * 6


def srt(lines):
    return "".join("%d\n00:00:%02d,000 --> 00:00:%02d,500\n%s\n\n" % (i + 1, i % 60, i % 60, l)
                   for i, l in enumerate(lines))


def write(path, text, encoding="utf-8"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding=encoding) as f:
        f.write(text)


def tree(root):
    src = os.path.join(root, "Shows")
    write(os.path.join(src, "A", "S01", "ep1.es.srt"), srt(ES))
    write(os.path.join(src, "A", "S01", "ep1.en.srt"), srt(EN))
    write(os.path.join(src, "A", "S01", "ep2.srt"), srt(ES), "cp1252")
    write(os.path.join(src, "A", "S01", "ep2.fr.srt"), srt(FR))
    write(os.path.join(src, "B", "Spanish.srt"), srt(ES), "utf-16")
    write(os.path.join(src, "B", "Portuguese.srt"), srt(PT))
    write(os.path.join(src, "B", "tiny.srt"), "1\n00:00:01,000 --> 00:00:02,000\nSí.\n")
    write(os.path.join(src, "B", ".hidden", "x.srt"), srt(ES))
    write(os.path.join(src, "B", "notes.txt"), "hola")
    return src, os.path.join(root, "bank")


def test_language_detection_across_encodings():
    with tempfile.TemporaryDirectory() as d:
        src, _ = tree(d)
        assert gather.language_of(os.path.join(src, "A", "S01", "ep1.es.srt")) == "es"
        assert gather.language_of(os.path.join(src, "A", "S01", "ep2.srt")) == "es"       # cp1252
        assert gather.language_of(os.path.join(src, "B", "Spanish.srt")) == "es"          # utf-16
        assert gather.language_of(os.path.join(src, "A", "S01", "ep1.en.srt")) == "en"
        assert gather.language_of(os.path.join(src, "B", "Portuguese.srt")) == "pt"
        assert gather.language_of(os.path.join(src, "A", "S01", "ep2.fr.srt")) == "fr"
        assert gather.language_of(os.path.join(src, "B", "tiny.srt")) == ""


def test_scan_keeps_only_the_language_and_the_folder_layout():
    with tempfile.TemporaryDirectory() as d:
        src, bank = tree(d)
        plan = gather.scan(src, bank)
        assert plan["found"] == 7 and len(plan["to_copy"]) == 3
        assert plan["other"] == {"en": 1, "fr": 1, "pt": 1} and plan["unknown"] == 1
        assert not os.path.exists(bank)                                   # scanning writes nothing
        copied, failed = gather.copy(plan)
        assert copied == 3 and not failed
        assert os.path.isfile(os.path.join(bank, "Shows", "A", "S01", "ep2.srt"))
        assert os.path.isfile(os.path.join(bank, "Shows", "B", "Spanish.srt"))


def test_rerun_copies_nothing_and_new_files_are_picked_up():
    with tempfile.TemporaryDirectory() as d:
        src, bank = tree(d)
        gather.copy(gather.scan(src, bank))
        again = gather.scan(src, bank)
        assert not again["to_copy"] and again["already"] == 3
        write(os.path.join(src, "A", "S02", "ep1.srt"), srt(ES))
        more = gather.scan(src, bank)
        assert len(more["to_copy"]) == 1 and more["already"] == 3


def test_never_overwrites_a_different_file_with_the_same_name():
    with tempfile.TemporaryDirectory() as d:
        src, bank = tree(d)
        gather.copy(gather.scan(src, bank))
        kept = os.path.join(bank, "Shows", "B", "Spanish.srt")
        before = open(kept, "rb").read()
        write(os.path.join(src, "B", "Spanish.srt"), srt(ES + ES), "utf-16")   # the source copy changes
        plan = gather.scan(src, bank)
        assert plan["name_clash"] == 1 and not plan["to_copy"]
        gather.copy(plan)
        assert open(kept, "rb").read() == before


def test_keep_all_and_other_language():
    with tempfile.TemporaryDirectory() as d:
        src, bank = tree(d)
        assert len(gather.scan(src, bank, keep_all=True)["to_copy"]) == 7
        assert len(gather.scan(src, bank, lang="fr")["to_copy"]) == 1


def test_inside_guard():
    assert gather.inside("/a/bank/x", "/a/bank") and not gather.inside("/a/other", "/a/bank")


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
