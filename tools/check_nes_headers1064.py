"""Exercise the shared classifier in both final ARM links and the SD launch path."""
import json
from pathlib import Path
from hashlib import sha256
from check_cart_state1059 import state
from check_ff3_sd1043 import Machine, fat16
from check_nes_retail_return1054 import run
from prepare_nes_headers1064 import OUT, ROOT

def check(folder):
    moai=(folder/"Moai Kun (K).nes").read_bytes()
    ax=(folder/"Battletoads v1.0 (K).nes").read_bytes()
    cases=[]
    def case(name,header,size,expected):
        cases.append((name,bytes(header),size,expected))
    for file,board in (("Moai Kun (K).nes",0x81),("Tetris (j).nes",0x81),
                       ("WaiwaiWorld 2 (K).nes",0x83),("Battletoads v1.0 (K).nes",0x82),
                       ("Dragon Quest IV (K1.2).nes",0x84)):
        image=(folder/file).read_bytes()
        case(file,image[:16],len(image),board)
    for glob,board in (("Hoshi no Kirby*.nes",0x7c),("Final Fantasy III*rel.DWYN*.nes",0x7d),
                       ("Zelda no Densetsu*nes",0x85),("Metal Max*nes",0),("Mother (*nes",0),
                       ("Final Fantasy 1 & 2*nes",0),("Akumajou Densetsu*nes",0)):
        matches=list(folder.glob(glob))
        assert matches
        for path in matches:
            case(path.name,path.read_bytes()[:16],path.stat().st_size,board)
    h=bytearray(moai[:16]); h[7:16]=b"DiskDude!"
    diskdude=bytes(h)+moai[16:]
    case("known archaic signature",h,len(moai),0x81)
    h[15]^=1
    case("ambiguous old signature",h,len(moai),0)
    h=bytearray(moai[:16]);h[7:9]=bytes((8,16))
    for prg_exp in (False,True):
        for chr_exp in (False,True):
            h[4]=60 if prg_exp else 2
            h[5]=60 if chr_exp else 4
            h[9]=(15 if prg_exp else 0)|(240 if chr_exp else 0)
            case("CNROM NES2",h,len(moai),0x81)
    encoded=bytes(h)+moai[16:]
    for cut in (-512,-1,1,512):case("payload size",h,len(moai)+cut,0)
    for offset,value in ((6,0x35),(6,0x39),(7,9),(7,10),(7,11),(8,0x11),(8,32),
                         (4,128),(4,125),(4,255),(5,255),(10,7),(11,7),(12,2),
                         (13,1),(14,1),(15,2),(15,64)):
        bad=h.copy();bad[offset]=value
        case("header guard",bad,len(moai)+(512 if offset==6 and value==0x35 else 0),0)
    case("UNIF",b"UNIF"+bytes(12),len(moai),0)
    case("FDS",b"FDS\x1a"+bytes(12),len(moai),0)
    h=bytearray(ax[:16]);h[7:12]=bytes((8,16,15,0,7));h[4]=19*4
    case("AxROM exponent",h,len(ax),0x82)
    zelda=bytearray((folder/"Zelda no Densetsu 1 (K).nes").read_bytes()[:16])
    zelda[7:12]=bytes((8,0,0,0x70,7))
    case("MMC1B NES2",zelda,262160,0x85)
    for offset,value in ((8,0x50),(6,0x16),(10,0x90),(11,0),(4,32)):
        bad=zelda.copy();bad[offset]=value
        case("unsupported MMC1 wiring",bad,16+bad[4]*16384+(512 if bad[6]&4 else 0),0)
    for mode in ("debug","release"):
        src=OUT/mode/"link/src"
        m=Machine(src,fat16())
        for name,header,length,expected in cases:
            m.u.mem_write(0x0807fc00,header)
            result=m.call("nes_image_id",0x0807fc00,length)
            assert result==expected,(mode,name,header.hex(),result,expected)
    launches={}
    for name,image in (("moai_nes2_exponent",encoded),("moai_archaic",diskdude)):
        launches[name]=run(0x81,OUT,1,raw=image,image="/sd2snes/nes-m3.bi3",expected_prg_bytes=32768)
    for n in (1,2):
        data=(folder/f"Zelda no Densetsu {n} (K).nes").read_bytes()
        launches[f"zelda_{n}"]=run(0x85,OUT,1,raw=data,image="/sd2snes/nes-m1.bi3",expected_prg_bytes=262144)
    flash={mode:(OUT/mode/"link/src/obj-nes-100/firmware.stm").stat().st_size for mode in ("debug","release")}
    assert max(flash.values())<=212992
    battery_state=state(0x85,0xdf472057,262144,21264,root=OUT)
    hashes={mode:sha256((OUT/mode/"link/src/obj-nes-100/firmware.stm").read_bytes()).hexdigest() for mode in flash}
    report=dict(firmware_sha256=hashes,checkpoint_bytes=battery_state,battery_roundtrip_bytes=8192,cases_per_link=len(cases),flash_bytes=flash,release_fatfs_launches=launches)
    (ROOT/"analysis/nes-headers1064.json").write_bytes((json.dumps(report,indent=2)+"\n").encode())
    print(report)

if __name__=="__main__":
    import argparse
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("folder",type=Path)
    check(cli.parse_args().folder)
