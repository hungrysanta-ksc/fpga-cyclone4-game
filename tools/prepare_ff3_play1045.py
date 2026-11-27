"""Derive the FF3 interactive ARM image from 1044; preserve the checkpoint ABI."""
import argparse
from pathlib import Path

from prepare_ff3_play1043 import play
from prepare_nes_kirby1023 import edit


def prepare(out):
    play(out, interactive=True)
    src = out / 'src'
    # A validated LOAD can end a live session during a static/blank opening.
    # Only the two presentation liveness checks depend on the exit reason.
    # Checkpoint integrity, ordered E0, observer STOP and base transfer keep
    # their original checks. The slot is consumed before the new session.
    edit(src, 'nes_runtime_board165.inc',
         ('if(!native_runtime165.frames&&!nes_run136.first_error)',
          'if(!ff3_next_slot&&!native_runtime165.frames&&!nes_run136.first_error)'))
    edit(src, 'nes_run136.inc',
         ('if(!nes_boot_probe798 && !nes_run136.first_error && (!nes_run136.first',
          'if(!ff3_next_slot && !nes_boot_probe798 && !nes_run136.first_error && (!nes_run136.first'))
    for name, expected in [('nes_checkpoint112.c', 1), ('nes_menu_diagnostic.c', 2)]:
        path = src / name
        text = path.read_text()
        assert text.count('ff31044') == expected
        path.write_text(text.replace('ff31044', 'ff31045'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('out', type=Path)
    prepare(parser.parse_args().out)
