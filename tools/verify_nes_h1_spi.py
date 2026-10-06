# SPDX-License-Identifier: MIT
from pathlib import Path
import hashlib,json,re
from nes_h1_spi import fixed_boundary
from nes_h1_spi_resource import decode_rle
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 raw=ROOT/"analysis/local-h1-spi-036"
 prior=json.loads((ROOT/"analysis/h1-firmware-artifacts.json").read_text())
 count=0
 for group in ("sources","status_files","evidence"):
  for e in prior[group]:
   p=(raw/"baseline-status" if group=="status_files" else ROOT)/e["path"]
   assert p.stat().st_size==e["bytes"] and sha(p)==e["sha256"],e["path"]
   count+=1
 legacy=raw/"rtl/legacy";fixed=raw/"rtl/fixed";fit=raw/"resource"
 assert "SPI sample mismatch sample=8 expected=1 got=0" in (legacy/"wave.log").read_text()
 assert "SPI queryf0 got4b expecteda5" in (legacy/"board.log").read_text()
 assert "PASS C SPI WAVE samples=224 verified=88 rows=942" in (fixed/"wave.log").read_text()
 assert "PASS NES H1 BOARD checks=6 rombytes=65536 payloadbytes=8192" in (fixed/"board.log").read_text()
 for n in ("wave.log","board.log"):
  assert not re.search(r"\*\* (?:Fatal|Error):",(fixed/n).read_text())
 assert (fixed/"nes_h1_board_bus.sv").read_text()==fixed_boundary()
 expected=sha(fixed/"nes_h1_board_bus.sv")
 assert sha(fixed/"nes_h1_board_bus.sv")==sha(fit/"nes_h1_board_bus.sv")==expected
 m=json.loads((fit/"result.json").read_text())
 assert m["compiled_boundary_sha256"]==expected
 assert m["phases"]==dict(map=0,fit=0,sta=0,asm=0)
 assert sha(raw/"resource-driver-first.py")==m["driver_sha256"]
 assert sha(raw/"resource-finalizer-used.py")==m["finalizer_driver_sha256"]
 assert sha(fit/"board.sdc")==sha(ROOT/"analysis/local-h1-board-034/resource/board.sdc")
 for n in ("board.qsf",):
  original=(ROOT/"analysis/local-h1-board-034/resource"/n).read_text()
  current=(fit/n).read_text()
  allowed={'set_global_assignment -name GENERATE_RBF_FILE ON','set_global_assignment -name LAST_QUARTUS_VERSION "25.1std.0 Standard Edition"'}
  assert [line for line in current.splitlines() if line and line not in allowed]==[line for line in original.splitlines() if line]
 assert sha(fit/"fpga_nh1.bi3")==m["bi3_sha256"]
 assert decode_rle((fit/"fpga_nh1.bi3").read_bytes())==(fit/"output_files/board.rbf").read_bytes()
 assert sha(fit/"output_files/board.rbf")==m["rbf_sha256"]
 decoder=json.loads((raw/"decoder/result.json").read_text())
 assert decoder["passed"] and decoder["bytes"]==m["rbf_bytes"] and decoder["bi3_sha256"]==m["bi3_sha256"]
 summary=(fit/"output_files/board.sta.summary").read_text()
 slack={}
 for kind,value in re.findall(r"Type\s*:\s*([^\n]+)\nSlack\s*:\s*([-\d.]+)",summary):
  name=kind.split(" Model ",1)[1].split(" '",1)[0]
  slack[name]=min(slack.get(name,999),float(value))
 assert len(slack)==5 and min(slack.values())>0
 fittext=(fit/"output_files/board.fit.rpt").read_text(encoding="latin-1")
 assert re.search(r"Total LABs:.*?104 / 963",fittext) and re.search(r"M9Ks\s*; 44 / 56",fittext)
 warnings={n:sorted(set(re.findall(r"Warning \((\d+)\)",(fit/(n+".log")).read_text(encoding="latin-1")))) for n in ("map","fit","sta","asm")}
 delays={line.split("\t")[0]:float(line.split("\t")[2]) for line in (fit/"io-audit/delays.tsv").read_text().splitlines()[1:]}
 result={"candidate":"NES-H1-SPI-036","previous035_entries_verified":count,
  "legacy_failure":"A5 identity reads as4B at STM32 +2us sample; first meaningful replay mismatch sample8",
  "C_read_samples":224,"meaningful_response_bits":88,"waveform_rows":942,
  "board_cases":6,"rom_bytes_exact":65536,"payload_bytes_exact":8192,
  "compiled_boundary_sha256":expected,"physical_fit":{"LE":1302,"LAB":104,"M9K":44,"pins":135,"virtual_pins":0,"registers":825,"PLLs":1},
  "minimum_internal_slack_ns":slack,"warning_codes":warnings,
  "external_delay_model":"Slow 1200mV 85C","external_longest_ns":delays,
  "unconstrained":{"input_ports":38,"input_paths":804,"output_ports":11,"output_paths":895},
  "rbf_bytes":m["rbf_bytes"],"rbf_sha256":m["rbf_sha256"],"bi3_bytes":m["bi3_bytes"],"bi3_sha256":m["bi3_sha256"],
  "MCU_stream_decoder_exact":True,"hardware_ready":False,"hardware_executed":False,
  "scope":"C delay/GPIO waveform replay into real RTL, full physical compile/ASM and image decoding; not instruction-timed MCU simulation or external IO signoff."}
 (ROOT/"analysis/h1-spi-verification.json").write_text(json.dumps(result,indent=2)+"\n")
 print(json.dumps(result,indent=2))
if __name__=="__main__":main()
