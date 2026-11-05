#!/usr/bin/env python3
# Builds ~/.fonts/ScratchpadIcons.ttf for the waybar scratchpad buttons:
#   U+E000  Claude Code's Clawd mascot (square pixels)
#   U+E001  md-square_rounded_outline from JetBrainsMono Nerd Font
# Both are scaled to the exact height and vertical position of the Nerd Font Wi-Fi icon,
# keeping their own proportions, so they sit at the same size as the bar's other icons.
import os

from fontTools import subset
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont

NERD = '/usr/share/fonts/TTF/JetBrainsMonoNerdFont-Regular.ttf'
GRID = [               # 12x8 square-pixel Clawd
    "..########..",
    "..#.####.#..",
    "############",
    "############",
    "..########..",
    "..########..",
    "..#.#..#.#..",
    "..#.#..#.#..",
]
MARGIN = 60            # side bearing each side, in font units

nerd = TTFont(NERD)
nerd_glyphs, cmap = nerd.getGlyphSet(), nerd.getBestCmap()
def bounds(cp):
    bp = BoundsPen(nerd_glyphs); nerd_glyphs[cmap[cp]].draw(bp); return bp.bounds
_, BOTTOM, _, TOP = bounds(0xF1EB)    # target: the Wi-Fi icon's vertical extent
HEIGHT = TOP - BOTTOM

f = TTFont(NERD)
opts = subset.Options(); opts.name_IDs = ['*']; opts.notdef_outline = True; opts.glyph_names = True
sub = subset.Subsetter(opts); sub.populate(unicodes=[0x20]); sub.subset(f)

def add(name, cp, glyph, width):
    f['glyf'].glyphs[name] = glyph
    f.setGlyphOrder(f.getGlyphOrder() + [name])
    f['hmtx'][name] = (round(width + 2 * MARGIN), MARGIN)
    for t in f['cmap'].tables:
        if t.isUnicode():
            t.cmap[cp] = name
    f['glyf'][name].recalcBounds(f['glyf'])

# Clawd: one uniform pixel size, so its proportions stay true
px = HEIGHT / len(GRID)
pen = TTGlyphPen(None)
for r, row in enumerate(GRID):
    y1 = TOP - r * px; y0 = y1 - px
    c = 0
    while c < len(row):
        if row[c] == "#":
            e = c
            while e + 1 < len(row) and row[e + 1] == "#":
                e += 1
            x0, x1 = MARGIN + c * px, MARGIN + (e + 1) * px
            x0, x1, y0r, y1r = round(x0), round(x1), round(y0), round(y1)
            pen.moveTo((x0, y0r)); pen.lineTo((x0, y1r)); pen.lineTo((x1, y1r)); pen.lineTo((x1, y0r)); pen.closePath()
            c = e + 1
        else:
            c += 1
add('clawd', 0xE000, pen.glyph(), len(GRID[0]) * px)

# Scratchpad square: the Nerd glyph scaled evenly to the same height
sx0, sy0, sx1, sy1 = bounds(0xF14FC)
k = HEIGHT / (sy1 - sy0)
pen = TTGlyphPen(None)
nerd_glyphs[cmap[0xF14FC]].draw(TransformPen(pen, (k, 0, 0, k, MARGIN - sx0 * k, BOTTOM - sy0 * k)))
add('square', 0xE001, pen.glyph(), (sx1 - sx0) * k)

f['maxp'].numGlyphs = len(f.getGlyphOrder())
for rec in f['name'].names:
    if rec.nameID in (1, 16): rec.string = 'Scratchpad Icons'
    elif rec.nameID == 4: rec.string = 'Scratchpad Icons Regular'
    elif rec.nameID == 6: rec.string = 'ScratchpadIcons-Regular'
f.save(os.path.expanduser('~/.fonts/ScratchpadIcons.ttf'))
for n in ('clawd', 'square'):
    g = f['glyf'][n]; print(n, 'height', g.yMax - g.yMin, 'width', g.xMax - g.xMin, 'y', g.yMin, g.yMax)
