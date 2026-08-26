# FitFace layout packaging decision

Approved packaging: **one watch face with four styles**.

- `style0` = design 1
- `style1` = design 2
- `style2` = design 3
- `style3` = design 4

All four styles share the same live semantic contract (date, weekday, AM/PM, hour/minute, seconds, battery, weather state, temperature) while keeping background artwork, coordinates, sizes, and weather-frame composition style-scoped.

Implementation remains staged: prove all remapped live semantics on a Golden Layout in `style0` first; only after real Fit3 validation is the same compiler applied to `style1`–`style3`.

The approved LCD colour calibration is immutable during layout work:

- logical/UI target `#B8B8AD`
- Fit3 optical payload `#B5B6BD`
- RGB565 `0xB5B7`
