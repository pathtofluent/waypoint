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

**run_automatically**: reconcile when Anki opens and after each sync.

Tags used: `waypoint_held` (waiting, suspended by the add-on) and `waypoint_cleared` (sentence already known).

**highlight_unknown_word / highlight_color**: colour the card's unknown word wherever it appears on the card (desktop only).

**shortcut_mark_known / shortcut_browse_same_word**: keys used while reviewing. Leave empty to turn one off.

More tags: `waypoint_known` (you marked the card's words as known) and `waypoint_learn_now` (pulled to the front by hand).
