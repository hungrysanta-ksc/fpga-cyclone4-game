import argparse,shutil,struct,subprocess,json
from pathlib import Path
from check_nes_fault641 import digest,evidence

def run(a):
    a.out.mkdir(parents=True,exist_ok=False)
    names=["nes_rom_loader.sv","nes_rom_physical.sv","nes_rom_boot.sv","nes_bg_window659.sv","nes_sink_bus165.sv"]
    for n in names:shutil.copyfile(a.board/n,a.out/n)
    shutil.copyfile(a.board/"sink-program.hex",a.out/"sink-program.hex")
    shutil.copyfile(Path(__file__).with_name("nes_bg659_tb.sv"),a.out/"bench.sv")
    assert digest(a.game)==evidence("mmc480-verification.json")["live_functional"]["rom_sha256"]
    data=a.game.read_bytes()[16:];assert len(data)==393216
    (a.out/"game.hex").write_text("".join(f"{v:02x}\n" for v in data))
    with (a.out/"tiles.txt").open("w") as f:
        for g in (954,955):
            for _,v in json.loads((a.plans/f"frame{g}/plans.json").read_bytes()):
                q=bytes.fromhex(v)
                if q[6]==0:print(g,struct.unpack_from("<H",q,4)[0],file=f)
    for tool,args in (("vlib",["work"]),("vlog",["-sv",*names,"bench.sv"]),("vsim",["-c","-quiet","bg659_tb","-do","onerror {quit -code 1}; onbreak {quit -code 1}; run -all; quit -code 0"])):
        with (a.out/(tool+".log")).open("wb") as log:
            subprocess.run([a.bin/(tool+".exe"),*args],cwd=a.out,stdout=log,stderr=subprocess.STDOUT,timeout=650,check=True)
    assert "PASS659" in (a.out/"vsim.log").read_text()

if __name__=="__main__":
    p=argparse.ArgumentParser()
    for n in ("board","out","bin","game","plans"):p.add_argument("--"+n,type=Path,required=True)
    run(p.parse_args())
