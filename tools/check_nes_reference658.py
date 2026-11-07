"""Compare v2.19 release assets and immutable CHR direct-copy eligibility offline."""
import argparse
import hashlib
import json
import struct
import zipfile
from collections import Counter
from pathlib import Path

RELEASE="bb86ee8782181a2daecfc79f79a937fc0e8b9664f4628577f5e7bedf40bdf895"
FILES=("nes_snes.bin","fpga_nes.bi3","fpga_nes_mmc3.bi3","fpga_nes_k.bi3","fpga_nes_mmc5.bi3","firmware.stm")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def compare(a):
    assert sha(a.release.read_bytes())==RELEASE
    assets={}
    with zipfile.ZipFile(a.release) as archive:
        for name in FILES:
            entry,=[i for i in archive.namelist() if i.split("/")[-1]==name]
            data=(a.local/name).read_bytes()
            assert data==archive.read(entry)
            assets[name]=dict(bytes=len(data),sha256=sha(data))
    game=a.game.read_bytes()
    assert game[:4]==b"NES\x1a" and ((game[6]>>4) | (game[7]&240))==4
    known=Path(__file__).resolve().parents[1]/"analysis/mmc480-verification.json"
    assert sha(game)==json.loads(known.read_bytes())["live_functional"]["rom_sha256"]
    offset=16+(512 if game[6]&4 else 0)+game[4]*16384
    chr_rom=game[offset:offset+game[5]*8192]
    assert len(chr_rom)==131072
    schedules=[json.loads((d/"obj-phases.json").read_bytes()) for d in (a.phase1,a.phase2)]
    frames={};total=Counter();plan_hash=hashlib.sha256()
    for g in range(905,958):
        raw=(a.plans/f"frame{g}/plans.json").read_bytes()
        plan_hash.update(hashlib.sha256(raw).digest());plans=json.loads(raw);windows=set()
        count=Counter();expected=[]
        for _,hex_plan in plans:
            p=bytes.fromhex(hex_plan)
            generation,slot,tag,kind,mask=struct.unpack_from("<HHHBB",p)
            assert generation==g and len(p)==40
            if kind not in (0,1):
                assert kind==2
                continue
            orig=chr_rom[16*tag:16*tag+16]
            prepared=bytes(orig[(i%2)*8+i//2] for i in range(16))+bytes(16*kind)
            output=bytearray()
            alt=struct.unpack_from("<8H",p,24)
            direct=True
            for i in range(16):
                if kind==1 and not mask&(1<<(i//2)):
                    output.append(0);direct=False;continue
                selected=tag if i%2 or alt[i//2]==65535 else alt[i//2]
                row=p[8+i]
                address=selected*16+8*(i%2)+row
                expected.append((kind,address))
                output.append(chr_rom[address])
                direct &= row==i//2 and selected==tag
            output.extend(bytes(16*kind))
            if kind==0:windows.add(tag//64)
            label="BG" if kind==0 else "OBJ"
            count[label+"_plans"]+=1
            if direct:
                assert output==prepared
                count[label+"_direct"]+=1
                count["direct_output_B"]+=len(output)
            else:
                count[label+"_fallback"]+=1
                count["whole_tile_wrong_for_game"]+=int(output!=prepared)
        # Some early frames have no request/entry at all. Check the physical
        # source address multiset, including capture hits, in both replays.
        for phases in schedules:
            actual=[(row[0],row[1]) for row in phases[str(g)].get("cache611",[])]
            assert Counter(actual)==Counter(expected),(g,len(actual),len(expected))
        frames[str(g)]=dict(count)
        frames[str(g)]["BG_distinct_1KiB_windows"]=len(windows)
        frames[str(g)]["BG_ROM_reads_by_phase"]=[sum(r[0]==0 and r[5]=="ROM" for r in q[str(g)].get("cache611",[])) for q in schedules]
        total.update(count)
    return dict(release=RELEASE,source_commit="6867510aba14693543577a87fa161595e1422b42",assets=assets,
                game_sha256=sha(game),plan_files_digest=plan_hash.hexdigest(),
                phase_trace_hashes=[sha((d/"obj-phases.json").read_bytes()) for d in (a.phase1,a.phase2)],
                CHR_ROM_B=len(chr_rom),extra_preconverted_B=len(chr_rom)*3,
                total=dict(total),frames=frames,scope="Structural tile eligibility and CHR bytes, not elapsed time, DMA bus arbitration, whole FIT, or physical FPS.")


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    for name in ("local","release","game","plans","phase1","phase2","out"):parser.add_argument("--"+name,type=Path,required=True)
    a=parser.parse_args();r=compare(a);a.out.write_text(json.dumps(r,indent=2)+"\n",newline="\n")
