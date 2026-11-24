"""Build sources for the actual Cortex-M4 sender against the 978 queue."""
import shutil
from pathlib import Path
from nes_hdma990 import BASE
from nes_raw506 import once

WORK = BASE.parent/"nes-sparse995"
CODE = Path(__file__).with_name("sparse995.c")

if __name__ == "__main__":
    root = WORK/"link"
    shutil.copytree(BASE/"link", root)
    f = root/"src/nes_sink_window184.c"
    s = f.read_text()
    anchor = "static bool send(struct nes_sink_window184"
    s = once(s, anchor, CODE.read_text()+"\n"+anchor)
    f.write_text(once(s, "memcpy(tx+1,p,n);", "n=packet_body995(tx+1,p,n);"), newline="\n")
