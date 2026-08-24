#!/usr/bin/env python3
from pathlib import Path
import sys

root = Path(sys.argv[1]).resolve()
p = root / "core/format/src/main/kotlin/dev/fitface/studio/core/format/FaceRecords.kt"
text = p.read_text()
old = '''            val pairColor = it.words.firstOrNull()?.takeIf { word ->
                word ushr 24 == 0xFFL
            }?.toInt()
            val pairBindingIndex = if (it.widgetType == WIDGET_PAIR) {
                it.words.getOrNull(1)?.toInt()?.and(0xFF)
            } else {
                null
            }
            val canEditPair = it.widgetType == WIDGET_PAIR && pairMatches == 1 &&
                pairColor != null
'''
new = '''            val pairColor = it.words.firstOrNull()?.takeIf { word ->
                word ushr 24 == 0xFFL
            }?.toInt()
            val canEditPair = it.widgetType == WIDGET_PAIR && pairMatches == 1 &&
                pairColor != null
            val pairBindingIndex = if (it.widgetType == WIDGET_PAIR) {
                it.words.getOrNull(1)?.toInt()?.and(0xFF)
            } else {
                null
            }
'''
if text.count(old) != 1:
    raise SystemExit(f"expected one Pair color/binding block, found {text.count(old)}")
p.write_text(text.replace(old, new, 1))
print("normalized Pair color/binding patch order")
