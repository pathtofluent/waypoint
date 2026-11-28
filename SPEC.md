---
project: Waypoint
status: testing
owner: PathToFluent
type: Anki add-on
created: 2026-11-21
updated: 2026-11-21
---

# Waypoint

## 1. Goal
When I study sentence cards made from Spanish TV subtitles, the next card should always be the most useful sentence that contains exactly one word I don't know yet. AnkiMorphs does something similar but carries far more than I need. "Working" means I open my SubDeck deck and every new card teaches me one new word, most valuable words and sentences first, with no manual sorting.

## 2. How I'll use it
1. I study my Assimil deck for about 100 days. Nothing in it is reordered, but the words and sentences I learn there are recorded as known.
2. I import episodes with SubDeck. The new cards land in Anki.
3. Anki opens or syncs, and the add-on sorts the new cards by itself.
4. I study. Each new card shows "New: *word*" on the back.
5. Overnight, a scheduled AI job labels any new cards (word meanings, names) and the order is refreshed.
6. When I add more subtitles to my subtitle folder, the scores recalculate on their own.

## 3. Rules
1. A word is one exact written form. *hablo* and *hablaron* are different words.
2. A word is **known** once a card containing it has an interval of 21 days or more.
3. A word is **learning** if a card containing it has been studied but is under 21 days.
4. Every other word is **unknown**. The known list starts empty.
5. Source decks (Assimil) are never sorted, suspended or changed. They only feed the known and learning lists.
6. A new SubDeck card is **ready** if it has exactly one unknown word and no learning words.
7. A card with a learning word is held back, because another card is already teaching that word.
8. Rule 7 does not apply when the card uses the word in a different meaning. Meanings come from the card's Labels field (`banco=banco#bank`).
9. A card with two or more unknown words is held back until it qualifies.
10. If several ready cards would teach the same word, only the best-scoring one is shown. The others are held back.
11. Ready cards are ordered by score: frequency of the unknown word, plus commonness of the sentence.
12. Sentence commonness counts exact repeats in the subtitle bank and how common the sentence's two- and three-word chunks are.
13. Names and numbers are replaced with placeholders before counting, so "Juan, ven aquí" and "María, ven aquí" are the same sentence.
14. A card with no unknown and no learning words comes after all ready cards, ordered by sentence commonness.
15. Exception to rule 14: if that sentence has already been studied on another card, the card is cleared.
16. Held and cleared cards are suspended and tagged (`waypoint_held`, `waypoint_cleared`), never deleted. Held cards are released automatically when they qualify.
17. Cards I suspended myself are left alone.
18. Each new card's "Unknown Words" field is filled in automatically. Once a card has been studied, that field is no longer changed.
19. The add-on runs when Anki opens, after each sync, and from the Tools menu.
20. When the subtitle folder's contents change, the bank is re-indexed on the next run.
21. "Add subtitles to the bank" copies subtitle files from a chosen folder, at any depth, into the bank under that folder's name, keeping its subfolders.
22. It keeps only files in the bank's language and reports how many it skipped in other languages.
23. It never moves or changes the originals, and never overwrites a file already in the bank. An identical file is skipped; a different file with the same name and place is left alone and counted.
24. Labelling is optional and off until a hand-off folder is chosen in Settings. Sorting never waits for it.
25. On each run Waypoint first reads `waypoint_labels.json` from that folder, if present, then writes `waypoint_to_label.json` with the unchecked new cards: ready cards first in score order, then review-only cards, then waiting cards with the fewest unknown words, up to the batch size.
26. A label is accepted only for a word present in the card's sentence, as `word#gloss` (lower-case letters, digits, hyphens; 30 characters at most) or `NAME`. Anything else is ignored and counted.
27. Every card named in the answers is tagged `waypoint_labelled` and not offered again, including cards with nothing to label.
28. Waypoint never contacts any service; whatever writes the answers is outside the add-on.
29. The answers may also give each card a usefulness rating, a whole number from 1 to 5, judged against the goal in the settings. It is stored as a tag, `waypoint_useful_1` to `waypoint_useful_5`.
30. The rating is a third part of the score: its weight (0.25 by default) times the rating scaled to 0-1. An unrated card counts as the middle of the scale.
31. The default goal is everyday conversation: carrying on day-to-day conversations with ease and expressing one's thoughts at the level of a university-educated adult.
32. For a new card with exactly one unknown word, the hand-off also asks for that word's dictionary form and two definitions of the meaning used in the sentence: one in the learner's language, one in the language being learned. A definition is accepted only if it names the card's unknown word and is plain text of 400 characters or fewer.
33. Definitions are written by whoever does the labelling, never copied from a dictionary. The card links to the dictionary's page for the word.
34. "New cards show" is a setting with two values, bilingual and monolingual. Each sorted card carries the matching tag. Changing the setting re-tags cards not yet studied; a studied card keeps its tag.
35. A card already labelled is offered again only for a definition it lacks.
36. "Prepare a note type" adds any missing Waypoint fields to a chosen note type and, for a Trailblazer note type, installs the current layout after saving the old one.
37. When a "Daily numbers folder" is chosen, each run keeps one line for that day in `waypoint_stats.json` there: known words, words being learned, known sentences, cards studied so far, cards ready, cards waiting. A later run the same day replaces the line. With no folder chosen, nothing is written.
38. A numbers file that can't be read is renamed aside and a new one started. A failure to write the numbers never stops the sorting.
39. Text in round brackets whose letters are all capitals, such as (MUJER) or (SOLLOZANDO), is a caption and is ignored when counting, on cards and in the subtitle bank. Brackets holding lower-case text are kept.
40. Marking a name while reviewing (right-click) applies to that card only, through its Labels field. `names.txt` hides a word on every card and is changed only by hand.
41. Sounds listed in the `filler_words` setting ("mm", "uh", "eh"), in any drawn-out spelling, and written laughter are not words: they are never unknown, never learned, and count as one placeholder in the subtitle bank.
42. A new card with no words to learn at all (only sounds, names or numbers) is cleared.
43. In the hand-off, a sentence that sits on several cards is listed once. Its answer (labels, rating, definition) is given to every other card with exactly the same sentence that still lacks that part. A card answered itself, or labelled by hand, is never overridden.

## 4. Examples
Known words: no, lo, sé, vamos, a, la, casa. Learning words: quiero, ir.

| # | Given (new SubDeck card) | Expected |
|---|--------------------------|----------|
| 1 | "Vamos a la playa." | Ready. Unknown word: playa. |
| 2 | "No, vamos a la playa." | Held. Example 1 already teaches playa and scores higher. |
| 3 | "Quiero ir a la playa." | Held. Contains learning words quiero and ir. |
| 4 | "No lo sé." (already studied in Assimil) | Cleared. |
| 5 | "Lo sé, vamos." (not studied anywhere) | Shown after all ready cards. |
| 6 | "El murciélago no." | Held. Two unknown words. |
| 7 | "Juan, vamos a la casa de María." | Ready. Names ignored; unknown word: de. |
| 8 | "Vamos al banco." with label `banco=banco#bank` | Held. Two unknowns: al, and banco in the "bank" sense. |
| 9 | A card I suspended by hand | Untouched. |

## 5. Not doing
- No dictionary forms or conjugation grouping.
- No changes to source decks.
- No deleting cards.
- No calls to an AI service from inside the add-on.
- French, until Spanish works.

## 6. Inputs and outputs
- **Reads:** cards in the source decks; SubDeck cards (Sentence, Labels fields); a frequency list file; a folder of subtitle files (.srt, .vtt, .ass, .txt).
- **Writes:** the order of new SubDeck cards; the "Unknown Words" field; tags `waypoint_held` and `waypoint_cleared`; a bank index file inside the add-on's folder.
- **Settings I can change:** source deck names and sentence fields, the 21-day thresholds, score weights, file paths, automatic running on or off.

## 7. Where it runs
- Anki desktop, version 2.1.50 or newer, on my Mac for now and the home lab box later.
- No extra software. Plain Python inside Anki.
- Cards come from SubDeck 1.2 or newer (it adds the Unknown Words and Labels fields).
- On my phone the sorted order arrives through sync; the add-on itself only runs on desktop.

## 8. Decisions made
| Decision | Why |
|----------|-----|
| Flat words, no dictionary forms | Simpler, and I may not actually know every conjugation |
| Known at 21 days | Reasonable starting point; adjustable |
| Known and learning lists are worked out fresh from the cards each run | Nothing to get out of step; self-corrects if a card lapses |
| Hold cards by suspending and tagging | Reversible; keeps them out of the new queue |
| Blank start, seeded by the Assimil deck | I'll spend about 100 days there first |
| Names detected by capitalisation inside a sentence only | Spanish rarely capitalises ordinary words mid-sentence, but every sentence opens with a capital. Guessing there hid real words; showing a name as a word is the visible, fixable mistake |
| AI labelling done by a separate scheduled job, not by the add-on | No API key or extra bill; labelling isn't urgent |
| Everything Waypoint needs lives in its own `waypoint` folder; no database, no shared folders | Standalone: works with no other add-on installed, and removing another add-on cannot break it |
| Definitions are written for the sentence, not pulled from a dictionary | A dictionary lists every sense for native speakers and its text is the publisher's; a one-line definition of this meaning serves a learner better, with the dictionary one tap away |
| Studied cards keep the mode they were learned in | Flipping to monolingual should change what comes next, not rewrite what has been learned |
| Labels travel through two files in a folder the user chooses | No extra software, no open port, works with Anki closed, and any person or tool can do the labelling |
| Usefulness weighs 0.25 against 1.0 for each counted factor | A rating is a judgement and varies; the counts are the same every time. At 0.25 the gap between a 1 and a 5 is about the gap between the 1,000th and 10,000th most common word: enough to reorder similar cards, not enough to lift a rare word over a common one. At 0.5 it outweighed word frequency for most words outside the top thousand |
| An unlabelled word means its most common meaning; only other meanings get a label | Matches decks that have no labels at all, such as the read-only ones |
| Never overwrite a bank file, even when the source copy has changed | Safe to point at the same folder repeatedly; a changed file can be replaced by hand |
| Filler sounds are a list in the settings, not built in | "ja" and "um" are sounds in Spanish and real words in German and Portuguese. The default suits Spanish |
| A name is marked per card; nothing is added to `names.txt` automatically | Many names are also ordinary words ("Río", a nickname like "Flaco"). A list that applies everywhere would hide the real word on every other card |
| Drop sentences and chunks that occur once from the bank index | They carry no signal and are most of the size |

## 9. Open questions
- [ ] (me) Exact name of the Assimil deck and which field holds the sentence.
- [ ] (me) Paths to the frequency list and subtitle folder on the machine that runs Anki.
- [ ] (Claude) Does Anki keep the card order handed to it when repositioning? Check on first real run.
- [ ] (me) Should a word drop back from known to learning if its card lapses below 21 days?
- [ ] (me) Should source decks use a lower threshold than 21 days?
- [ ] (me) **Choose a card for a word** (idea, 2026-11-28). A "Choose this one" action on a card. Once used, every other card that teaches the same new word in the same meaning (same label, or no label) is retired, so the deck trims itself. Until a card is chosen, nothing is retired: the first card shown may have a poor clip or sentence. Open: does retire mean suspend and tag (`waypoint_retired`, reversible, keeps the media), or delete to free space? If delete, when (for example once the chosen card reaches 21 days) and with what way back? Does a chosen card that later lapses bring its siblings back?
- [ ] (me) **Staging deck to main deck** (idea, 2026-11-28). New cards are imported into a staging deck; once a card is chosen or learned, Waypoint moves it to the main deck, so nothing is moved by hand. Open: which event moves a card (chosen, first review, or known at 21 days); one main deck or one per source; what happens to its retired siblings.

## 10. Build stages
- [x] **Stage 1:** Scoring core: word states, scoring, ready / held / review-only / cleared, bank index.
- [x] **Stage 2:** Anki side: read cards, apply order, suspend and tag, fill the field, menu, automatic runs.
- [ ] **Stage 3:** First run in real Anki with the Assimil deck and one imported episode. Fix what breaks.
- [x] **Stage 4:** The labels hand-off through a chosen folder (the add-on's side).
- [ ] **Stage 5:** "New meaning" button on the card for manual override.
- [ ] **Later:** set phrases treated as one unit; French; optional direct API labelling; choosing a card for a word, and moving cards from a staging deck to the main deck (see Open questions).

## 11. How to check it works
- Tested: the scoring core, against the examples in section 4, on a small made-up frequency list and subtitle bank.
- Not tested: anything inside Anki.
- First real check: install, set the three config values, run Tools → Waypoint → Reconcile cards, then Show numbers. In the card browser, search `tag:waypoint_held` and `tag:waypoint_cleared`, and sort new SubDeck cards by due position to see the order.

## 12. Instructions for Claude
- Read this whole file before writing anything.
- Build only the next unchecked stage, then stop and tell me what to test.
- If a rule is unclear or two rules conflict, ask me before building. For small details not covered here, decide, and record the choice under "Decisions made".
- Check the examples in section 4 against the code and tell me which pass.
- Keep the scoring core free of Anki imports so it can be tested without Anki.
- Tell me plainly what you could not test.
- When done, update: status, the stage checkboxes, "Decisions made", and the log.

## 13. Log
- 2026-11-28: Two ideas recorded for later: choosing a card for a word so the others teaching it are retired, and moving cards from a staging deck to the main deck. Not specced or built.
- 2026-11-28: 0.7.3. Repeated sentences sent once and the answer shared (rule 43). Choosing and sharing tested; reading the notes and writing to them inside Anki untested.
- 2026-11-27: 0.7.2. Filler sounds (rules 41-42) and the match-by-text rule for reused answers. Counting tested; the new setting inside Anki untested. 0.7.1's right-click name confirmed working by the owner.
- 2026-11-27: 0.7.1. Captions in capitals inside round brackets ignored (rule 39); right-click name is per card (rule 40); labelling instructions updated. Counting and the label merge tested; the right-click action is untested inside Anki.
- 2026-11-26: 0.7.0. Daily numbers file (rules 37-38) for PathToFluent Logbook or any other tool, with tests for the file handling. The setting and the write at reconcile are untested inside Anki.
- 2026-11-26: 0.6.0. Definitions, bilingual/monolingual tags and "Prepare a note type" built (rules 32-36), with tests for the definition format. All of the Anki side untested. Planned path: primer deck (~2,000 cards), bilingual (~2,000), then monolingual towards 10,000.
- 2026-11-26: 0.5.0. Labels hand-off built (rules 24-31, including the usefulness rating), with tests for the format and validation. Reading and writing cards inside Anki untested.
- 2026-11-26: 0.4.0. Subtitle gathering built into the add-on (rules 21-23), with tests. Gathering logic tested; the menu item and its windows untested inside Anki.
- 2026-11-21: Designed in chat. Stages 1 and 2 written; core tested on sample data, Anki side untested. SubDeck updated to 1.2 with the two new fields. Next: stage 3 at home.
