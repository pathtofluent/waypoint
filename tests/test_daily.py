"""Tests for Waypoint's daily numbers file. No Anki needed.   Run:  python3 tests/test_daily.py"""
import datetime, json, os, sys, tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "addon"))
import daily

D = datetime.date
STATS = {"known_words": 312, "learning_words": 40, "known_sentences": 150, "ready": 25, "held": 604, "cleared": 3}


def days_in(folder):
    return json.load(open(os.path.join(folder, daily.STATS_FILE), encoding="utf-8"))["days"]


def test_a_day_line_holds_the_numbers():
    line = daily.day_line(STATS, 480, "es", D(2026, 11, 26))
    assert line == {"date": "2026-11-26", "language": "es", "known_words": 312, "learning_words": 40,
                    "known_sentences": 150, "cards_studied": 480, "cards_ready": 25, "cards_waiting": 604}
    assert daily.day_line({}, 0, "es", D(2026, 1, 1))["known_words"] == 0


def test_same_day_replaces_the_line():
    with tempfile.TemporaryDirectory() as d:
        for known in (300, 305, 312):
            daily.write(d, daily.day_line(dict(STATS, known_words=known), 480, "es", D(2026, 11, 26)))
        days = days_in(d)
        assert len(days) == 1 and days[0]["known_words"] == 312


def test_days_add_up_in_date_order_and_languages_stay_apart():
    with tempfile.TemporaryDirectory() as d:
        daily.write(d, daily.day_line(STATS, 480, "es", D(2026, 11, 26)))
        daily.write(d, daily.day_line(STATS, 470, "es", D(2026, 11, 24)))
        daily.write(d, daily.day_line(STATS, 10, "fr", D(2026, 11, 26)))
        daily.write(d, daily.day_line(STATS, 11, "fr", D(2026, 11, 26)))
        assert [(x["date"], x["language"], x["cards_studied"]) for x in days_in(d)] == [
            ("2026-11-24", "es", 470), ("2026-11-26", "es", 480), ("2026-11-26", "fr", 11)]


def test_a_damaged_file_is_set_aside_not_overwritten():
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, daily.STATS_FILE)
        open(path, "w").write("{ not json")
        note = daily.write(d, daily.day_line(STATS, 480, "es", D(2026, 11, 26)))
        assert daily.UNREADABLE in note
        assert open(os.path.join(d, daily.UNREADABLE)).read() == "{ not json"
        assert len(days_in(d)) == 1
        assert daily.write(d, daily.day_line(STATS, 481, "es", D(2026, 11, 27))) == ""
        for bad in ('{"days": "x"}', '{"days": [{"date": "yesterday"}]}', '[1, 2]'):
            open(path, "w").write(bad)
            try:
                daily.read(path)
                raise AssertionError("expected ValueError for " + bad)
            except ValueError:
                pass


def test_missing_file_is_no_days_and_no_temp_file_is_left():
    with tempfile.TemporaryDirectory() as d:
        assert daily.read(os.path.join(d, daily.STATS_FILE)) == []
        daily.write(d, daily.day_line(STATS, 1, "es", D(2026, 11, 26)))
        assert os.listdir(d) == [daily.STATS_FILE]


def test_old_days_are_trimmed():
    days = [{"date": (D(2010, 1, 1) + datetime.timedelta(days=n)).isoformat(), "language": "es"} for n in range(daily.KEEP_DAYS + 5)]
    out = daily.merge(days, {"date": "2026-11-26", "language": "es"})
    assert len(out) == daily.KEEP_DAYS and out[-1]["date"] == "2026-11-26"


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
