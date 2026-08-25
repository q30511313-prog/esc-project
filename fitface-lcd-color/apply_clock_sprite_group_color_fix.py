#!/usr/bin/env python3
from pathlib import Path
import sys

root = Path(sys.argv[1]).resolve()
path = root / "core/format/src/main/kotlin/dev/fitface/studio/core/format/FaceEditor.kt"
text = path.read_text()

old = '''            val pool = FaceRecordParser.sharedFrameClosure(
                target,
                records,
                imagesByRelativeOffset,
            )
'''

new = '''            // Samsung face 00003 style0 stores hour/minute and seconds in two
            // physically separate glyph pools even though they form one logical clock.
            // Only opt into grouped recoloring when the complete six-field digital clock
            // signature is present exactly once; every other Sprite keeps the original
            // selected/shared-pool behavior.
            val clockSequenceIds = setOf(2, 3, 10, 11, 14, 15)
            val clockSprites = if (target.sequenceId in clockSequenceIds) {
                clockSequenceIds.mapNotNull { clockSequenceId ->
                    records.singleOrNull {
                        it.widgetType == WIDGET_SPRITE &&
                            it.sequenceId == clockSequenceId
                    }
                }.takeIf { it.size == clockSequenceIds.size }
            } else {
                null
            }
            val pool = if (clockSprites != null) {
                clockSprites.flatMap { clockSprite ->
                    FaceRecordParser.sharedFrameClosure(
                        clockSprite,
                        records,
                        imagesByRelativeOffset,
                    )
                }.toSet()
            } else {
                FaceRecordParser.sharedFrameClosure(
                    target,
                    records,
                    imagesByRelativeOffset,
                )
            }
'''

count = text.count(old)
if count != 1:
    raise SystemExit(f"FaceEditor.kt: expected one Sprite pool anchor, found {count}")

path.write_text(text.replace(old, new, 1))
print("clock Sprite group recolor fix applied")
