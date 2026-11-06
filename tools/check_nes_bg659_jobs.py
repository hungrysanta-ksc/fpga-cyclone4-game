import argparse,shutil,struct,subprocess,json
from pathlib import Path

def check(a):
    a.out.mkdir(parents=True,exist_ok=False)
    shutil.copyfile(a.board/"nes_tile205.sv",a.out/"nes_tile205.sv")
    shutil.copyfile(Path(__file__).with_name("nes_bg659_jobs_tb.sv"),a.out/"bench.sv")
    packed={}
    with (a.out/"plans.txt").open("w") as fp:
        for gen in range(905,958):
            for _,r in json.loads((a.plans/f"frame{gen}/plans.json").read_bytes()):
                p=bytes.fromhex(r);g,slot,tag,kind,mask=struct.unpack_from("<HHHBB",p)
                if kind!=0:continue
                assert p[8:24]==bytes(i//2 for i in range(16)) and p[24:]==b"\xff"*16
                print(g,slot,tag,file=fp);packed[g,slot]=tag
    for tool,args in (("vlib",["work"]),("vlog",["-sv","nes_tile205.sv","bench.sv"]),("vsim",["-c","-quiet","jobs_tb","-do","onerror {quit -code 1}; onbreak {quit -code 1}; run -all; quit -code 0"])):
        with (a.out/(tool+".log")).open("wb") as log:
            subprocess.run([a.bin/(tool+".exe"),*args],cwd=a.out,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=50)
    assert "PASS659" in (a.out/"vsim.log").read_text()
    rows={}
    for r in (a.out/"descriptors.txt").read_text().splitlines():
        g,s,h=r.split();tag=packed[int(g),int(s)];lo=tag*16&65535;bank=0x50+(tag>>12)
        assert bytes.fromhex(h)==struct.pack("<HBBHHHHHBB",lo,bank,0xd6,lo^65535,int(g),int(s),int(g)^65535,int(s)^65535,bank^255,0x29)
        rows[f"{g}/{s}"]=h
    assert len(rows)==268;(a.out/"jobs.json").write_text(json.dumps(rows,indent=2)+"\n")
if __name__=="__main__":
    p=argparse.ArgumentParser()
    for n in ("plans","board","out","bin"):p.add_argument("--"+n,type=Path,required=True)
    check(p.parse_args())
