"""Compile/execute production STM32 binding with a timed GPIO/SPI mock."""
import argparse, json, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--gcc",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    for name in ("config","bits","timer","snes","fpga","fpga_spi","fileops","uart"):
        (a.out/(name+".h")).write_text('#include "h1_stm32_mock.h"\n')
    exe=a.out/"h1-stm32-test.exe"
    cmd=[str(a.gcc),"-std=c11","-D__USE_MINGW_ANSI_STDIO=1","-Wall","-Wextra","-Werror","-O2",
         "-I"+str(a.out),"-I"+str(ROOT/"tests/nes-functional"),
         str(ROOT/"tests/nes-functional/h1_stm32_test.c"),
         str(ROOT/"src/nes/firmware/nes_h1_session.c"),"-o",str(exe)]
    def run(cmd,log):
        result=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        (a.out/log).write_bytes(result.stdout)
        if result.returncode:
            raise RuntimeError(result.stdout.decode(errors="replace"))
    run(cmd,"compile.log")
    run([str(exe),str(a.out/"transactions.tsv")],"test.log")
    lines=(a.out/"test.log").read_text().splitlines()
    passed=[line for line in lines if line.startswith("PASS ")]
    assert len(passed)==11
    (a.out/"result.json").write_text(json.dumps({"candidate":"NES-H1-FIRMWARE-035",
        "passed":passed,"scope":"Production C on host, GPIO/SPI device mock; no hardware execution"},indent=2)+"\n")
    print("\n".join(passed))
if __name__=="__main__":main()
