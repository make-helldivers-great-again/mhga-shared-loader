# MHGA artwork

`banner.png` (2172x724, README banner) and `thumbnail.png` (1254x1254, the box icon in Arsenal and HD2MM, selected
by `icon` in [`../../branding.json`](../../branding.json) and packaged as `thumbnail.png`) for **MHGA Shared Loader**.

They follow the visual system of the upstream Bingus Shared Loader artwork (see [`../ARTWORK.md`](../ARTWORK.md)): pure
typography on a distressed charcoal ground, wide heavy cream and yellow block type, clipped yellow border rules, three
yellow hazard slashes, yellow wear in the corners and a small letter-spaced footer. Palette: ground `#121110`, cream
`#f0e8d6`, yellow `#fdd00c`.

Upstream's were made with an image generator. These are **drawn in code** by `art.py`, so they can be regenerated
and edited: `python art.py banner` and `python art.py icon` (need Pillow, NumPy, SciPy; deterministic). The footer is
`--footer "..."`; by default it credits the upstream project. They are close recreations, not pixel matches.

Fonts in `fonts/` are SIL Open Font License: Archivo Black (title, squeezed horizontally) and Barlow Condensed
SemiBold (footer). License texts are alongside. Upstream's own `../banner.png` and `../thumbnail.png` are left untouched.
