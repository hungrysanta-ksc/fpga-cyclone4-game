"""Use CRC-checked board SPI replies and their production time in the linked MMC826 replay."""
import argparse
import json
import sys
from pathlib import Path
from unittest.mock import patch

from replay_nes_output822 import MirrorLink
from replay_nes_tile821 import main, WORK
from test_nes_sender652 import gates


def observe_held_frame(template, generation):
    anchor = " for _,c in ipairs(captures)do if not c.done and st.frameCount>c.frame then"
    assert template.count(anchor) == 1
    monitor = """
 if completedFrame==%d and st.frameCount>shown then
  local pixels=emu.getScreenBuffer()
  local f=assert(io.open(ROOT..'/held-'..st.frameCount..'.rgb','wb'))
  for y=0,238 do
   local row={}
   for x=0,255 do
    local b=pixels[y*256+x+1]
    row[#row+1]=string.char((b>>16)&255,(b>>8)&255,b&255)
   end
   f:write(table.concat(row))
  end
  f:close()
  local log=assert(io.open(ROOT..'/held.csv','a'))
  log:write(string.format('%%d,%%d,%%d,%%d,%%d\\n',st.frameCount,st.masterClock,
    word(0x1032),word(0x1248),word(0x124a)))
  log:close()
 end
""" % generation
    return template.replace(anchor,monitor+anchor)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("data", "sender", "hits", "budget", "temp"):
        p.add_argument(name, type=Path)
    p.add_argument("phase", type=int, choices=(1, 2))
    p.add_argument("tag")
    p.add_argument("--observe-held", type=int, metavar="GENERATION")
    variants = p.add_mutually_exclusive_group()
    variants.add_argument("--reference837", action="store_true")
    variants.add_argument("--arm", type=Path, help="alternate fully linked ARM src directory")
    args = p.parse_args()
    replies = json.loads((args.sender / "sender.json").read_text())
    verified = json.loads((args.sender / "verified.json").read_text())
    work = json.loads((args.data / "work.json").read_text())
    assert [(w["source_frame"], w["g"]) for w in work] == [
        (f["source"], f["generation"]) for f in verified["frames"]]
    argv = ["replay", "", "", "", "", "", args.tag, str(args.budget)]
    reference = dict(arm=WORK.parent / "nes-output823/link-826/src")
    if args.arm:
        reference["arm"] = args.arm.resolve()
    if args.observe_held is not None:
        reference["adapt_template"] = lambda s: observe_held_frame(s,args.observe_held)
    if args.reference837:
        reference.update(arm=WORK.parent / "nes-output823/link-837palette/src",
                         client=WORK.parent / "nes-window837/client-sticky",
                         client_hash="9ec7bf85cb733a6b624ddbe554604601e7e2a00deb3900dd9b270a3b220fe623")
    with patch.object(sys, "argv", argv), patch.object(MirrorLink, "lookup_file", args.hits), gates(replies, True):
        main(args.data.parent, args.data.name, "jointmirror", args.phase, args.temp,
             link_class=MirrorLink, packet_source=replies, **reference)
