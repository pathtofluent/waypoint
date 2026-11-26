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
| Names detected by capitalisation | Spanish rarely capitalises ordinary words mid-sentence |
| AI labelling done by a separate scheduled job, not by the add-on | No API key or extra bill; labelling isn't urgent |
| Everything Waypoint needs lives in its own `waypoint` folder; no database, no shared folders | Standalone: works with no other add-on installed, and removing another add-on cannot break it |
| Never overwrite a bank file, even when the source copy has changed | Safe to point at the same folder repeatedly; a changed file can be replaced by hand |
| Drop sentences and chunks that occur once from the bank index | They carry no signal and are most of the size |

## 9. Open questions
- [ ] (me) Exact name of the Assimil deck and which field holds the sentence.
- [ ] (me) Paths to the frequency list and subtitle folder on the machine that runs Anki.
- [ ] (Claude) Does Anki keep the card order handed to it when repositioning? Check on first real run.
- [ ] (me) Should a word drop back from known to learning if its card lapses below 21 days?
- [ ] (me) Should source decks use a lower threshold than 21 days?

## 10. Build stages
- [x] **Stage 1:** Scoring core: word states, scoring, ready / held / review-only / cleared, bank index.
- [x] **Stage 2:** Anki side: read cards, apply order, suspend and tag, fill the field, menu, automatic runs.
- [ ] **Stage 3:** First run in real Anki with the Assimil deck and one imported episode. Fix what breaks.
- [ ] **Stage 4:** The nightly labelling job through AnkiConnect.
- [ ] **Stage 5:** "New meaning" button on the card for manual override.
- [ ] **Later:** set phrases treated as one unit; French; optional direct API labelling.

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
- 2026-11-26: 0.4.0. Subtitle gathering built into the add-on (rules 21-23), with tests. Gathering logic tested; the menu item and its windows untested inside Anki.
- 2026-11-21: Designed in chat. Stages 1 and 2 written; core tested on sample data, Anki side untested. SubDeck updated to 1.2 with the two new fields. Next: stage 3 at home.
