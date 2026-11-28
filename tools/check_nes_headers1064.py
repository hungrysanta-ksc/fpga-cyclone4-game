"""Exercise the shared classifier in both final ARM links and the SD launch path."""
import json
from pathlib import Path
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
                       ("Zelda no Densetsu*nes",0),("Metal Max*nes",0),("Mother (*nes",0),
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
    flash={mode:(OUT/mode/"link/src/obj-nes-100/firmware.stm").stat().st_size for mode in ("debug","release")}
    assert max(flash.values())<=212992
    report=dict(cases_per_link=len(cases),flash_bytes=flash,release_fatfs_launches=launches)
    (ROOT/"analysis/nes-headers1064.json").write_bytes((json.dumps(report,indent=2)+"\n").encode())
    print(report)

if __name__=="__main__":
    import argparse
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("folder",type=Path)
    check(cli.parse_args().folder)
