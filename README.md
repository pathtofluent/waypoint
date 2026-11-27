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
- **Score** = frequency of the unknown word + how common the sentence is in your subtitle bank + (optionally) how useful the sentence is, rated 1 to 5 through the labels hand-off.
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
| `waypoint/names.txt` | Names to ignore on every card, one per line. Edited by hand only; right-click marks a name on one card |
| `waypoint/lists/` | The three readable word and sentence lists |

Waypoint keeps everything in that one `waypoint` folder and uses no database. If you have a `dbs/frequency.txt` left by MorphMan or a similar add-on, Waypoint copies it into `waypoint/frequency-list/` the first time it runs and leaves the original alone.

## Names, second meanings and usefulness (optional)

Waypoint tracks words by spelling, so on its own it can't tell that "Juan" is a name or that "banco" the bench and "banco" the bank are different things to learn. The labels hand-off fixes that, and it is entirely optional: Waypoint sorts the same way without it.

1. In Settings, choose a **Labels hand-off folder**. Any folder you like.
2. Each time Waypoint runs it writes `waypoint_to_label.json` there: the next cards worth checking, most useful first, plus `HOW-TO-LABEL.md` explaining the format.
3. Something fills in `waypoint_labels.json` in the same folder. That can be you, a script, or an AI assistant pointed at the folder and told to follow `HOW-TO-LABEL.md`.
4. The next time Waypoint runs it reads the answers, stores them in each card's `Labels` field, tags the card `waypoint_labelled`, and re-sorts. The answers file is renamed to `waypoint_labels.imported.json`.

The same hand-off carries a **usefulness rating** from 1 to 5 for each sentence, judged against a goal you can set (`usefulness_goal`; by default, everyday conversation at an educated adult's level). It is stored as a tag, `waypoint_useful_1` to `waypoint_useful_5`, and added to the card's score with its own weight (`usefulness_weight`, 0.25 by default; the other two factors weigh 1.0 each). At that setting the gap between a 1 and a 5 is about the same as the gap between the 1,000th and the 10,000th most common word, so a rating can reorder cards whose words are similarly common but won't lift a rare word over a common one. Unrated cards count as the middle of the scale. Counting can't see that a common line is a throwaway exclamation or that a rare one is a perfect everyday phrase; a rating can.

### Definitions, and going monolingual

For a card with exactly one unknown word, the hand-off also asks for that word's **dictionary form**, a **definition in your own language**, and a **definition written in the language you're learning**, each for the meaning used in that sentence. Waypoint stores them in the card's `Lemma`, `Definition` and `Definition Monolingual` fields, and puts a link to the word's dictionary page in `Dictionary Link` (the RAE's dictionary by default; change `dictionary_url` for another language).

**New cards show** in Settings decides which definition a card's back displays:

- *Bilingual*: the definition in your own language.
- *Monolingual*: the definition in the language you're learning, with the other one behind a Show English button.

The choice is recorded as a tag (`waypoint_bilingual` or `waypoint_monolingual`), so it works on your phone. Flipping the setting changes cards you haven't studied yet; a card you have studied keeps the mode it was learned in.

Cards need the fields above. **Tools > PathToFluent Waypoint > Prepare a note type** adds whichever are missing to a note type you already use, and for Trailblazer cards also updates the layout so the definitions show. Adding fields makes Anki ask for a one-time full sync; nothing on your cards is lost and nothing needs re-importing.

Waypoint only accepts a label for a word that is in the sentence, in the form `word#gloss` or `NAME`; anything else is ignored. Cards need a `Labels` field (Trailblazer cards have one). Waypoint never contacts any service itself.

## Daily numbers (optional)

Choose a "Daily numbers folder" in Settings and Waypoint keeps one line per day in `waypoint_stats.json` there: known words, words being learned, known sentences, cards studied, cards ready and cards waiting. Running again the same day replaces that day's line. It is a plain file for any tool that wants to show progress over time; [PathToFluent Logbook](https://github.com/pathtofluent/logbook) reads it. Leave the setting blank and nothing is written.

## Install and set up

1. Download **[pathtofluent_waypoint.ankiaddon](https://github.com/pathtofluent/waypoint/raw/main/download/pathtofluent_waypoint.ankiaddon)**.
2. Double-click it, or in Anki: Tools > Add-ons > Install from file. Then restart Anki.
3. Tools > PathToFluent Waypoint > Settings: tick your read-only decks and the decks to sort.

Needs Anki 25.09 or newer. Do not run it alongside AnkiMorphs or MorphMan on the same decks.

## Building

```
python3 tests/test_core.py     # scoring tests
python3 tests/test_gather.py   # subtitle gathering tests
python3 tests/test_labels.py   # labels hand-off tests
python3 tests/test_daily.py    # daily numbers file tests
python3 tools/build.py         # writes download/pathtofluent_waypoint.ankiaddon
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
| [Logbook](https://github.com/pathtofluent/logbook) | Logs your time with a language and tracks hours, known words and milestones |

## Licence

GNU AGPL v3 or later. See `LICENSE`.
