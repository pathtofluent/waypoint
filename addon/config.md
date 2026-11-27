The easy way to change these is **Tools > Waypoint > Settings**.

**source_decks**: decks that feed the known lists and are never sorted. Give each deck's exact name and the field holding the sentence, e.g. `{"Assimil Spanish": "Front"}`. An empty field name means the first field.

**managed_decks**: decks whose new cards are scored and sorted.

**managed_note_types**: only used if managed_decks is empty.

**sentence_field / unknown_field / labels_field**: field names on the managed note type.

**known_interval_days**: a word counts as known once a card containing it reaches this interval. **source_known_interval_days** is the same for source decks.

**count_learning_as_known**: if true, a word you are still learning does not hold other cards back.

**word_weight / sentence_weight**: how much the unknown word's frequency and the sentence's commonness count towards the score.

**exact_sentence_weight / chunk_weight**: inside the sentence score, how much an exact repeat counts versus common two- and three-word chunks.

**frequency_list**: leave blank to use the file in `waypoint/frequency-list/` in your Anki profile folder (one word per line, most common first). Or give a full path to another file.

**subtitle_bank_folder**: full path to a folder of subtitle files (.srt, .vtt, .ass, .txt). Re-indexed automatically when its contents change.

**bank_language**: the language kept by Tools > PathToFluent Waypoint > Add subtitles to the bank (es, en, fr, pt, it, de).

**filler_words**: hesitation and reaction sounds that are not words to learn ("mm", "uh", "eh"). They never count as unknown, and a card made only of them, names and numbers is cleared. Longer spellings are covered automatically ("mm" also matches "mmmm"), as is written laughter ("jajaja"). The list suits Spanish; change it for another language, where "ja" or "um" may be a real word.

**labels_folder**: folder for the labels hand-off (see the README). Blank turns labelling off. Set it in Settings with the Browse button.

**labels_batch_size**: how many cards are offered for labelling at a time.

**stats_folder**: folder where Waypoint keeps `waypoint_stats.json`, one line of numbers per day (known words, words being learned, cards studied, cards waiting). Blank turns it off. Set it in Settings with the Browse button.

**usefulness_weight**: how much a card's 1-5 usefulness rating from the labels hand-off counts towards its score (0 turns it off). Unrated cards count as the middle of the scale.

**usefulness_goal**: what "useful" means for you, in a sentence. Passed to whoever does the rating. Blank = everyday conversation at an educated adult's level.

**card_mode**: what the back of new cards shows, "bilingual" or "monolingual". Set it in Settings.

**dictionary_url / dictionary_name**: where the Dictionary Link points; `{lemma}` is replaced by the word's dictionary form. Empty url = no link.

**lemma_field / definition_field / definition_mono_field / dictionary_field**: field names for definitions.

**run_automatically**: reconcile when Anki opens and after each sync.

Tags used: `waypoint_held` (waiting, suspended by the add-on) and `waypoint_cleared` (sentence already known).

**highlight_unknown_word / highlight_color**: colour the card's unknown word wherever it appears on the card (desktop only).

**shortcut_mark_known / shortcut_browse_same_word**: keys used while reviewing. Leave empty to turn one off.

More tags: `waypoint_bilingual` / `waypoint_monolingual` (which definition the card shows), `waypoint_useful_1` to `waypoint_useful_5` (usefulness rating), `waypoint_labelled` (the card has been checked for names and second meanings), `waypoint_known` (you marked the card's words as known) and `waypoint_learn_now` (pulled to the front by hand).
