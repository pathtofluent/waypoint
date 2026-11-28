# Changelog

## 0.7.3 (2026-11-28)
- Labels hand-off: a sentence that sits on several cards is now listed once in `waypoint_to_label.json`. When the answer comes back, its labels, rating and definition are given to every other card with exactly the same sentence that still lacks them. A card that was answered itself, or labelled by hand, is never overridden.
- Show numbers reports how many cards received a shared answer on the last run.

## 0.7.2 (2026-11-27)
- New setting `filler_words`: hesitation and reaction sounds such as "mm", "uh" and "eh" are no longer counted as words to learn. Longer spellings ("mmmm", "uhh") and written laughter ("jajaja") are covered. The default list suits Spanish and can be edited in the add-on's config.
- A card with nothing to learn at all (only sounds, names or numbers) is now cleared, so it never comes up. Before, it was queued after the ready cards.
- Labelling instructions: an earlier answer may be reused only by matching the sentence's text, since card ids change when a deck is imported again.
- The bank index rebuilds once on the next run.

## 0.7.1 (2026-11-27)
- Fixed: captions for the hard of hearing in round brackets and capitals, such as (MUJER), (SOLLOZANDO) or (MÚSICA SUAVE), were counted as words, on cards and in the subtitle bank. They are now ignored, like [square brackets] already were. Brackets holding lower-case text are kept as speech. The bank index rebuilds once on the next run.
- Changed: right-click "treat as a name" now marks the word as a name on that card only, in its Labels field, and works only on a card being reviewed. It no longer writes to `names.txt`, which hides a word on every card. `names.txt` still works and is edited by hand.
- Labelling instructions (`HOW-TO-LABEL.md`): a name label applies to one card, so a nickname that is also an ordinary word stays a word elsewhere; no definition is sent for a name; no meaning labels inside an institution's title.

## 0.7.0 (2026-11-26)
- The ready-to-install add-on file is now kept in the repository at `download/pathtofluent_waypoint.ankiaddon`, linked from the README. (Packaging only; the add-on itself is unchanged.)
- New optional setting "Daily numbers folder". When a folder is chosen, each run keeps that day's line in `waypoint_stats.json` there: known words, words being learned, known sentences, cards studied, cards ready, cards waiting. A second run on the same day replaces the line. Off unless a folder is chosen.
- A damaged numbers file is renamed aside, never overwritten. A problem writing the numbers never stops the sorting; Show numbers reports it.

## 0.6.0 (2026-11-26)
- The hand-off now carries definitions for cards with one unknown word: its dictionary form, a definition in your language and one in the language you're learning, plus a dictionary link. Validated on the way in (plain text, right word, sensible length).
- New setting "New cards show": bilingual or monolingual. Recorded as a tag per card; studied cards keep the mode they were learned in.
- New menu item "Prepare a note type for Waypoint": adds the fields Waypoint uses to an existing note type and, for Trailblazer cards, updates the layout. No re-import needed.
- Cards already checked are offered again only for the part they still lack.
- "Prepare a note type" also renames a note type still called SubDeck (Trailblazer's earlier name) and its tag.

## 0.5.0 (2026-11-26)
- Added the optional labels hand-off: choose a folder in Settings, and Waypoint writes the cards worth checking for names and second meanings, then reads the answers back into each card's Labels field. Off unless a folder is chosen.
- Labels are validated on the way in: only `word#gloss` or `NAME`, only for words in the sentence.
- The hand-off also carries a 1-5 usefulness rating per sentence, stored as a tag (`waypoint_useful_1` to `_5`) and added to the score with its own weight. The goal it is judged against is a setting.
- New tag `waypoint_labelled`. Show numbers reports the hand-off's progress.
- Changed: a capitalised word that opens a sentence is no longer guessed to be a name. Before, an ordinary word missing from the frequency list ("Mírela.") was silently dropped as a name. Now an opening name counts as a word until `names.txt`, the right-click "treat as a name", K, or a label says otherwise.

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
- A name that opens a sentence shows up as an unknown word until it is named (see 0.5.0).
- Set phrases are not yet treated as one unit.
- The whole subtitle bank is re-indexed whenever the folder changes.
- No automated tests for the code that runs inside Anki.
