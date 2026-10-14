# SPDX-License-Identifier: MIT
"""Render completed model pixels for scene identification, not CRT color proof."""
from pathlib import Path
import argparse
from PIL import Image, ImageDraw
from build_nes_game164 import RGB


def render(root, frames, output):
    assert not output.exists()
    colors = [tuple(bytes.fromhex(v)) for v in RGB]
    canvas = Image.new('RGB', (512 * 2, 504 * ((len(frames) + 1) // 2)))
    draw = ImageDraw.Draw(canvas)
    for i, frame in enumerate(frames):
        values = [int(v, 16) for v in (root / f'game-{frame}.hex').read_text().split()]
        assert len(values) == 256 * 240 and all(0 <= v < 512 for v in values)
        picture = Image.new('RGB', (256, 240))
        picture.putdata([colors[v & 63] for v in values])
        x, y = (i % 2) * 512, (i // 2) * 504
        canvas.paste(picture.resize((512, 480), Image.Resampling.NEAREST), (x, y + 24))
        draw.text((x + 8, y + 4), f'Model frame {frame} (emphasis omitted)', fill='white')
    canvas.save(output)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('root', type=Path)
    p.add_argument('--frames', type=int, nargs='+', required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    render(a.root, a.frames, a.out)
