"""Prepare the 769 diagnostic screen ROM and a 707D board with host-clock timestamp latches."""
from pathlib import Path
from argparse import ArgumentParser
from shutil import copyfile
from unittest.mock import patch
import json

from prepare_nes_trial763 import PROBES, ROOT, digest
from build_nes_static751 import codec, pack

CLOCK = 0x1b00
FIRST = CLOCK+1


def client(out, variant):
    base = PROBES/("nes-complete685/client01" if variant==763 else "nes-static751/sharedfast")
    expected = json.loads((ROOT/"analysis/trial763-package.json").read_bytes())["variants"]["763" if variant==763 else "765"]["ROM_SHA256"]
    assert digest(base/"sink165.sfc") == expected
    body = bytearray((base/"body.bin").read_bytes())
    def absolute(op, addr):
        return bytes([op])+addr.to_bytes(2,"little")
    def hook(at, old, code):
        i = at-codec.DEST
        assert body[i:i+len(old)] == old
        entry = codec.DEST+len(body)
        body[i:i+len(old)] = absolute(0x20,entry)+bytes([0xea])*(len(old)-3)
        body.extend(code + b"\x60")
    # Enable native NMI only after a known counter, consume a pending old edge.
    hook(0x211a,bytes.fromhex("a9018d0042"),
         absolute(0x9c,CLOCK)+bytes.fromhex("ad1042a9818d0042"))
    # SEAL dispatch with A16. Low generation byte joins the measured ARM row.
    hook(0x264e,bytes.fromhex("ad0012"),bytes.fromhex("e220ad08128d0470")+
         absolute(0xad,CLOCK)+bytes.fromhex("8d0570a9ff8d0670")+absolute(0x8d,FIRST)+bytes.fromhex("c220ad0012"))
    # First post-SEAL PPU DMA: both upload loop and final CGRAM/OAM loop.
    dma = bytes.fromhex("8d0b42")
    start = codec.DEST+len(body)
    code = absolute(0xad,FIRST)+bytes.fromhex("f009")+absolute(0x9c,FIRST)+absolute(0xad,CLOCK)+bytes.fromhex("8d0670a901")+dma
    hook(0x2c04,dma,code)
    assert body[0x2cd5-codec.DEST:0x2cd8-codec.DEST] == dma
    body[0x2cd5-codec.DEST:0x2cd8-codec.DEST] = absolute(0x20,start)
    # Stamp immediately before the successful final ACK publication only.
    hook(0x27e7,bytes.fromhex("a9a58d1c60"),
         bytes.fromhex("ad0012c903d006")+absolute(0xad,CLOCK)+bytes.fromhex("8d0770a9a58d1c60"))
    raw = PROBES/"nes-reuse635/client04"
    with patch.object(codec,"pack",pack):
        codec.build(raw,out,edit_body=lambda *_:bytes(body),allow_extension=True,
                    prefix_sizes=[512,256,128,64],medium_pages=True,boot_bytes=320,fast_backrefs=True)
    meta=json.loads((out/"build.json").read_bytes())
    rom=bytearray((out/"sink165.sfc").read_bytes())
    # Bank 00 handler, preserve interrupted DBR, A (including B) and P.
    nmi=bytes.fromhex("e220488b4bab")+absolute(0xee,CLOCK)+bytes.fromhex("ad1042ab6840")
    entry=meta["loader_B"]
    assert entry+len(nmi)<=320 and rom[0x7fea:0x7fec] == bytes.fromhex("0080")
    rom[entry:entry+len(nmi)]=nmi
    rom[0x7fea:0x7fec]=(0x8000+entry).to_bytes(2,"little")
    (out/"sink165.sfc").write_bytes(rom)
    (out/"sink-program.hex").write_text("".join(f"{b:02x}\n" for b in rom[:5056]+rom[-64:]),newline="\n")
    copyfile(base/"labels.json",out/"labels.json")


def board(source,out,client_dir):
    pins=json.loads((ROOT/"analysis/bg707-verification.json").read_bytes())["inputs"]
    out.mkdir(parents=True,exist_ok=False)
    for name,h in {**pins["base"],**pins["changed"]}.items():
        if name=="sink-program.hex":continue
        assert digest(source/name)==h,name
        dest=out/name
        dest.parent.mkdir(parents=True,exist_ok=True)
        copyfile(source/name,dest)
    copyfile(client_dir/"sink-program.hex",out/"sink-program.hex")
    p=out/"nes_screen_status151.sv"
    s=p.read_text()
    def replace(a,b):
        nonlocal s
        assert s.count(a)==1,a
        s=s.replace(a,b)
    replace(" reg [15:0] frames;", " reg [15:0] frames;\n reg [7:0] trace769[0:3];")
    replace("address==24'h007001;", "address==24'h007001 || address[23:2]==22'h001c01;")
    replace("command==8'h73&&", "(command==8'h73||command==8'h78)&&")
    replace("stage<=0;error_code<=0;", "for(integer i=0;i<4;i=i+1)trace769[i]<=0;\n   stage<=0;error_code<=0;")
    replace("    seen<=1;", "    seen<=1;\n    if(addr_previous[23:2]==22'h001c01)trace769[addr_previous[1:0]]<=data_previous;")
    replace("       snapshot<=", "       if(incoming==8'h78) snapshot<={8'h78,trace769[0],trace769[1],trace769[2],trace769[3],8'h5a,8'ha5};\n       else snapshot<=")
    # Stage 6 frame counter belongs to an older ROM. Both fixed sinks only
    # write stages 2, 3 and 0x7e in RUN. Remove its incrementer on this
    # diagnostic profile; normal stage/error/STOP and reset handling remain.
    replace("     if(data_previous==8'd6 && frames!=16'hffff)frames<=frames+1'b1;", "")
    p.write_text(s,newline="\n")
    # Free the auxiliary post-STOP button-history recorder. Invalid signature
    # explicitly marks the history unavailable; live input and STOP stay wired.
    observer = out/"nes_run_observer134.sv"
    rtl = observer.read_text()
    start = rtl.index(" nes_pad_trace156 trace(")
    end = rtl.index(" reg [7:0] reply;", start)
    observer.write_text(rtl[:start]+" assign pad_page = 56'd0;\n"+rtl[end:],newline="\n")
    # arg and its complement finish on wire bytes 4/5. Latch their
    # predicates before the tail/SS edge; length and CRC still use that edge.
    p=out/"nes_rom_spi.sv"
    s=p.read_text()
    arg="command>8'h6a || (command!=8'h61 && command!=8'h68 && ((command==8'h60)?arg!=2:arg!=0))"
    inv="arg_not!=~arg"
    replace(" reg [3:0] pending_command,pending_header_error;",
            " reg bad_arg769,bad_inverse769;\n always @(posedge mem_clk)begin\n"+
            "  bad_arg769<="+arg+";bad_inverse769<="+inv+";\n end\n reg [3:0] pending_command,pending_header_error;")
    replace("else if("+arg+")pending_header_error","else if(bad_arg769)pending_header_error")
    replace("tail!=8'ha5 || "+inv+")pending_header_error","tail!=8'ha5 || bad_inverse769)pending_header_error")
    p.write_text(s,newline="\n")
    for f in ("report_nes_oe612.tcl","report_nes_reader661.tcl","report_nes_word660.tcl"):
        copyfile(source/f,out/f)


if __name__=="__main__":
    a=ArgumentParser()
    a.add_argument("variant",type=int,choices=(763,767))
    for key in ("client","source","board"):a.add_argument(key,type=Path)
    o=a.parse_args()
    client(o.client,o.variant)
    board(o.source,o.board,o.client)
