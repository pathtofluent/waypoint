# PathToFluent Waypoint

An Anki add-on. It sorts your new sentence cards so the next one is always the most useful sentence containing exactly one word you don't know yet.

Status: early. The scoring logic has tests; the parts that run inside Anki have had only light hands-on use.

## How it works

- **Read-only decks** (for example a course deck you already study) are never changed. The words and sentences you learn there count as known.
- **Sorted decks** hold your sentence cards. Each new card is one of:
  - *ready*: exactly one unknown word and no words still being learned. Shown first, best score first.
  - *waiting*: more than one unknown word, or a word another card is already teaching. Suspended and tagged `waypoint_held` until it qualifies.
  - *review-only*: every word known, sentence new. Shown after the ready cards.
  - *cleared*: every word known and the sentence already studied. Suspended and tagged `waypoint_cleared`.
- **Score** = frequency of the unknown word + how common the sentence is in your subtitle bank.
- A word is **known** once a card containing it reaches an interval of 21 days (adjustable). The cards are the record; `known_words.txt`, `learning_words.txt` and `known_sentences.txt` are rewritten on every run as readable copies.
- While reviewing: **K** marks the card's words known and skips it, **L** browses cards with the same unknown word. The unknown word is highlighted on the card.
- In the card browser: right-click > **Waypoint: learn now** pulls cards to the front.

## Filling the subtitle bank

**Tools > PathToFluent Waypoint > Add subtitles to the bank** lets you pick any folder. Every subtitle file inside it, at any depth, is checked, and the ones in your language are copied into the bank under the name of the folder you chose, keeping its subfolders.

- Originals are never moved or changed.
- Nothing already in the bank is overwritten, so you can point it at the same folder again after adding files to it and only the new ones are copied.
- Files in other languages are skipped; the language is set in Settings.
- Show numbers lists how many files each folder of the bank holds.

To do the same without opening Anki: `python3 tools/gather_subtitles.py` (add `--dry-run` to preview).

## Files

All inside your Anki profile folder:

| Path | Purpose |
|------|---------|
| `waypoint/frequency-list/` | Your frequency list: one file, one word per line, most common first |
| `waypoint/subtitle-bank/` | Subtitle files (.srt, .vtt, .ass, .txt), subfolders allowed |
| `waypoint/names.txt` | Names to ignore, one per line |
| `waypoint/lists/` | The three readable word and sentence lists |

Waypoint keeps everything in that one `waypoint` folder and uses no database. If you have a `dbs/frequency.txt` left by MorphMan or a similar add-on, Waypoint copies it into `waypoint/frequency-list/` the first time it runs and leaves the original alone.

## Install and set up

1. Build the add-on (below) or download it from Releases.
2. In Anki: Tools > Add-ons > Install from file, then restart.
3. Tools > PathToFluent Waypoint > Settings: tick your read-only decks and the decks to sort.

Needs Anki 25.09 or newer. Do not run it alongside AnkiMorphs or MorphMan on the same decks.

## Building

```
python3 tests/test_core.py     # scoring tests
python3 tests/test_gather.py   # subtitle gathering tests
python3 tools/build.py         # writes dist/pathtofluent_waypoint.ankiaddon
```

`SPEC.md` holds the rules, examples and decisions behind the behaviour.

## Credits

The feature set owes a lot to [AnkiMorphs](https://github.com/mortii/anki-morphs) and MorphMan. The code here is written from scratch.

## The PathToFluent tools

| Tool | What it does |
|------|--------------|
| [Trailblazer](https://github.com/pathtofluent/trailblazer) | Turns a video and its subtitles into an Anki deck |
| [Waypoint](https://github.com/pathtofluent/waypoint) | Sorts sentence cards so the next one has exactly one unknown word |
| [Checkpoint](https://github.com/pathtofluent/checkpoint) | A single Complete button for chapter and lesson cards |
| [Scout](https://github.com/pathtofluent/scout) | Finds Netflix titles by country and original language |

## Licence

GNU AGPL v3 or later. See `LICENSE`.
