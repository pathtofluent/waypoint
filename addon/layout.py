"""PathToFluent Waypoint - the card layout Waypoint can install on a note type.

This is the same layout PathToFluent Trailblazer gives its cards. Keep the two in step: if one changes,
change the other (trailblazer.py: CARD_FRONT, CARD_BACK, CARD_CSS, FIELDS).

Front: the scene's snapshot and audio. Back: the sentence, the new word, and its definition.
Which definition shows is decided by a tag on the card:
  waypoint_bilingual    the definition in the learner's own language
  waypoint_monolingual  the definition in the language being learned, with the other behind a button
"""

# Fields a note type needs for everything Waypoint can do, in the order they are added.
FIELDS = ["Unknown Words", "Labels", "Lemma", "Definition", "Definition Monolingual", "Dictionary Link"]

FRONT = """<div class="sd">
{{#Snapshot}}<div class="img">{{Snapshot}}</div>{{/Snapshot}}
<div class="audio">{{Audio}}</div>
{{^Audio}}{{^Snapshot}}<div class="sentence">{{Sentence}}</div>{{/Snapshot}}{{/Audio}}
</div>"""

BACK = """<div class="sd wp" data-tags="{{Tags}}">
{{#Snapshot}}<div class="img">{{Snapshot}}</div>{{/Snapshot}}
<div class="audio">{{Audio}}</div>
<div class="sentence">{{Sentence}}</div>
{{#Unknown Words}}<div class="new">New: {{Unknown Words}}{{#Lemma}} <span class="lemma">({{Lemma}})</span>{{/Lemma}}</div>
{{#Definition Monolingual}}<div class="def mono">{{Definition Monolingual}}</div>{{/Definition Monolingual}}
{{#Definition}}<div class="def bi">{{Definition}}</div>
<button class="trbtn enbtn" onclick="var d=this.previousElementSibling,s=d.style.display==='block';d.style.display=s?'none':'block';this.textContent=s?'Show English':'Hide English';">Show English</button>{{/Definition}}
{{#Dictionary Link}}<div class="dict">{{Dictionary Link}}</div>{{/Dictionary Link}}{{/Unknown Words}}
{{#Translation}}<button class="trbtn" onclick="var t=this.nextElementSibling,s=t.style.display==='block';t.style.display=s?'none':'block';this.textContent=s?'Show translation':'Hide translation';">Show translation</button>
<div class="tr">{{Translation}}</div>{{/Translation}}
{{#Notes}}<div class="notes">{{Notes}}</div>{{/Notes}}
<div class="src">{{Source}}</div>
</div>"""

CSS = """.card{font-family:-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;font-size:22px;
text-align:center;color:#1c1c1e;background:#fafafa;margin:0;padding:16px}
.nightMode.card,.night_mode.card{color:#ececec;background:#1e1e20}
.sd img{max-width:100%;max-height:45vh;border-radius:10px}
.sentence{font-size:1.25em;line-height:1.4;margin:18px 6px}
.trbtn{font-size:.7em;padding:8px 18px;border-radius:999px;border:1px solid #8884;background:transparent;
color:inherit;cursor:pointer;margin:4px}
.tr{display:none;margin:14px 6px;font-size:.9em;opacity:.8}
.new{font-size:.75em;margin:0 6px 10px;color:#2f6f5e;font-weight:600}
.lemma{font-weight:400;opacity:.75}
.def{margin:8px 10px 12px;font-size:.85em;line-height:1.45}
.wp .def.mono,.wp .enbtn{display:none}
.wp[data-tags~="waypoint_monolingual"] .def.mono{display:block}
.wp[data-tags~="waypoint_monolingual"] .def.bi{display:none}
.wp[data-tags~="waypoint_monolingual"] .enbtn{display:inline-block}
.dict{font-size:.6em;margin:4px 0 12px}.dict a{color:inherit;opacity:.6}
.notes{font-size:.8em;margin-top:10px}.src{font-size:.5em;opacity:.45;margin-top:18px}"""
