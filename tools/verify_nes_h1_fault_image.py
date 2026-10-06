# SPDX-License-Identifier: MIT
"""Validate BI3 using the pinned firmware's actual stream decoder on the host."""
from pathlib import Path
import argparse,hashlib,json,shutil,subprocess
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser()
 for n in ("fit","firmware-tree","gcc","out"):p.add_argument("--"+n,type=Path,required=True)
 a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
 for n in ("rle.c","rle.h"):shutil.copy2(a.firmware_tree/"src"/n,a.out/n)
 (a.out/"fileops.h").write_text("#include <stdint.h>\nextern int file_status,file_res;\nuint8_t file_getc(void);\n")
 cmd=[str(a.gcc),"-std=c11","-Wall","-Wextra","-Werror","-O2","-I"+str(a.out),
      str(ROOT/"tests/nes-functional/h1_image_decode_test.c"),str(a.out/"rle.c"),"-o",str(a.out/"test.exe")]
 for name,args in [("compile",cmd),("decode",[str(a.out/"test.exe"),str(a.fit/"fpga_nh1.bi3"),str(a.fit/"output_files/board.rbf")])]:
  cp=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
  (a.out/(name+".log")).write_bytes(cp.stdout)
  assert cp.returncode==0,(name,cp.stdout)
 text=(a.out/"decode.log").read_text()
 size=(a.fit/'output_files/board.rbf').stat().st_size
 assert f'PASS MCU rle_file_getc exact bytes={size} and EOF' in text
 result={"passed":True,"bytes":size,"scope":"Pinned MCU decoder host execution; no FPGA hardware configuration",
   "source_sha256":{n:hashlib.sha256((a.out/n).read_bytes()).hexdigest() for n in ("rle.c","rle.h")},
   "bi3_sha256":hashlib.sha256((a.fit/"fpga_nh1.bi3").read_bytes()).hexdigest()}
 (a.out/"result.json").write_text(json.dumps(result,indent=2)+"\n")
 print(text.strip())
if __name__=="__main__":main()
