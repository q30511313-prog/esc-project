#!/usr/bin/env python3
from pathlib import Path
import sys

root = Path(sys.argv[1]).resolve()
ui = root / "feature/editor/src/main/kotlin/dev/fitface/studio/feature/editor/EditorScreen.kt"
text = ui.read_text()
old = "LCD Gray #9F9E99"
new = "LCD Gray #B8B8AD"
count = text.count(old)
if count != 2:
    raise SystemExit(f"EditorScreen.kt: expected two {old} labels, found {count}")
ui.write_text(text.replace(old, new))
print("bright LCD labels #B8B8AD applied to both controls")
