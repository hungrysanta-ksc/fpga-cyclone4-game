"""Build on the exact 727 sender with 733's short padding representation."""
from argparse import ArgumentParser
from pathlib import Path
from shutil import copytree, ignore_patterns

from nes_raw506 import once, sha


def prepare(base, out, after_obj=False):
    assert sha(base / "src/obj-nes-100/firmware.stm") in {
        "523be6b648b23be88e888dd0c119788e164cd42c66306368ed4f77d07fd90655",
        "3196a512124899531abbcb45f545cb01186779326b47c0e811d61209b1f2f386",
    }
    copytree(base, out, ignore=ignore_patterns("obj-*", ".dep-*", "*.log"))
    path = out / "src/nes_native_sink165.c"
    source = once(path.read_text(), "if(op==2 && data && n>=4 && !(n&1)){\n  unsigned i=2;while(i<n && data[i]==data[i&1])i++;",
                  "if(op==2 && n>=4 && !(n&1)){\n  unsigned i=n;\n  if(data){i=2;while(i<n && data[i]==data[i&1])i++;}")
    source = once(source, "if(n)memcpy(b+16,data,n)", "if(n && data)memcpy(b+16,data,n)")
    source = once(source, "zero[240]", "zero[2]")
    source = once(source, "offset,zero,n)", "offset,NULL,n)")
    source = once(source, "if(n>240){n&=~1u;if(!packet_wire", """if(n>240){
    /* Padding and raw CHR are consecutive bytes in the same section.
     * Extend the fixed-source transfer only across verified zero words. */
    if(!(n&1) && !raw[0] && !raw[1]){
     unsigned prefix=repeat_bytes(raw,packed);
     n+=prefix;raw+=prefix;packed-=prefix;
    }
    n&=~1u;if(!packet_wire""")
    source = once(source, "if(!span(s,5,offset,raw,packed))", "if(packed && !span(s,5,offset,raw,packed))")
    if after_obj:
        # Preserve the cold and map-only schedules. Only arbitrate a shorter
        # post-OBJ tail after an actual OBJ issue and certified OAM reuse.
        reuse = "same&&s->displayed&&s->ack635[r->target]&&s->ack635[1-r->target]"
        source = once(source, "bool same=same635(s,p);", "bool same=same635(s,p);\n bool reuse="+reuse+";")
        source = once(source, "if("+reuse+")", "if(reuse)")
        source = once(source, "if(!(n&1) && !raw[0]", "if(reuse && s->obj_next && !(n&1) && !raw[0]")
    path.write_text(source, encoding="utf8", newline="\n")


if __name__ == "__main__":
    p = ArgumentParser()
    p.add_argument("base", type=Path)
    p.add_argument("out", type=Path)
    p.add_argument("--after-obj",action="store_true")
    args = p.parse_args()
    prepare(args.base, args.out, args.after_obj)
