# Changelog

## 0.4.0 (2026-11-26)
- Added Tools > PathToFluent Waypoint > Add subtitles to the bank: pick a folder, and subtitle files in your language at any depth are copied into the bank. Originals are untouched and nothing already in the bank is overwritten.
- Added a "Language of the subtitle bank" setting.
- Show numbers now lists the files in each folder of the bank.
- Added `tools/gather_subtitles.py` for filling the bank without opening Anki.
- The frequency list now lives in `waypoint/frequency-list/`. Waypoint no longer creates a `dbs` folder; an existing `dbs/frequency.txt` is copied in once and otherwise only read as a fallback.

## 0.3.1 (2026-11-26)
- Display names now read "PathToFluent Waypoint".
- Recognises the note type "PathToFluent Trailblazer" as well as "SubDeck" when no decks are chosen.

## 0.3.0 (2026-11-26)
- Renamed from One Unknown. Tags are now `waypoint_held`, `waypoint_cleared`, `waypoint_known`, `waypoint_learn_now`; the data folder is `<profile>/waypoint/`. Old tags and the old `one-unknown` folder are migrated on first run.
- Reads `dbs/frequency.txt` from the profile folder by default.
- Added: mark known and skip (K), browse same unknown word (L), learn now (browser right-click), highlighting of the unknown word, `names.txt`, right-click "treat as a name".
- Cards are the source of truth; the list files are rewritten each run.
- Settings window with deck pickers; toolbar counter next to Sync.
- Sorted decks accept either a `Sentence` or an `Expression` field.

## 0.1.0 (2026-11-21)
- First version: scoring core, ready / waiting / review-only / cleared, subtitle bank index, Unknown Words field.

## Known gaps
- A name at the start of a sentence is only recognised if the frequency list lacks it; use `names.txt` or K meanwhile.
- Word meanings (the `Labels` field) are not filled in yet; the labelling job is still to build.
- The whole subtitle bank is re-indexed whenever the folder changes.
- No automated tests for the code that runs inside Anki.
