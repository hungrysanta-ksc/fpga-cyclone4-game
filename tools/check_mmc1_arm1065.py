"""Execute 1065 ARM file selection, full preload and geometry-specific SD journals."""
import json
import sys
from pathlib import Path
from zlib import crc32
from check_nes_retail_return1054 import run
from check_ff3_sd1043 import Machine,fat16
from check_cart_state1059 import state
from prepare_sxrom1065 import OUT

def check():
    folder=Path.home()/"Downloads/test"
    rom=(folder/"Final Fantasy 1 & 2 (J) [!].nes").read_bytes()
    assert crc32(rom)==0x6f8906ad and crc32(rom[16:])==0xc9556b36
    h=bytearray(rom[:16]);n=len(rom)
    for mode in ("debug","release"):
        m=Machine(OUT/mode/"link/src",fat16())
        def classify(header,length):
            m.u.mem_write(0x0807fc00,bytes(header))
            return m.call("nes_image_id",0x0807fc00,length)
        assert classify(h,n)==0x86 and not classify(h,n-1)
        for ram,expected in ((1,0),(2,0),(4,0x86)):
            t=h.copy();t[8]=ram
            assert classify(t,n)==expected
        t=h.copy();t[7]=8;t[10]=0x90;t[11]=7
        assert classify(t,n)==0x86
        for pos,val in ((8,0x10),(10,0x70),(10,0x99),(11,8),(12,1)):
            u=t.copy();u[pos]=val
            assert not classify(u,n)
    result={}
    if "state" in sys.argv:
        result["checkpoint"]=state(0x86,crc32(rom),n-16,45840,root=OUT,battery_bytes=32768)
        name="fat-state"
    elif "zelda" in sys.argv:
        for n in (1,2):
            raw=(folder/f"Zelda no Densetsu {n} (K).nes").read_bytes()
            result[str(n)]=run(0x85,OUT,1,raw=raw,image="/sd2snes/nes-m1.bi3",expected_prg_bytes=262144)
        name="fat-zelda"
    else:
        image="/sd2snes/nes-sx.bi3"
        result["ff12"]=run(0x86,OUT,1,raw=rom,image=image,expected_prg_bytes=524288)
        bad=bytearray(rom);bad[16]^=1
        result["ambiguous_other_rom"]=run(0x86,OUT,1,raw=bytes(bad),image=image,reject_crc=True)
        archaic=bytearray(rom);archaic[7:16]=b"DiskDude!"
        result["archaic_unknown_RAM"]=run(0x86,OUT,1,raw=bytes(archaic),image=image,reject_crc=True)
        name="fat-launch"
    (OUT/(name+".json")).write_text(json.dumps(result,indent=2))
    print(result)

if __name__=="__main__":check()
