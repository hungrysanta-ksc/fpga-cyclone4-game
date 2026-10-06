# SPDX-License-Identifier: MIT
"""039 diagnostic-only first-fault SPI snapshot and paired MCU reader."""
from pathlib import Path
import argparse,hashlib,json,subprocess,sys
from nes_h1_spi import fixed_boundary,replace
from nes_h1_runtime import source as runtime_source
ROOT=Path(__file__).resolve().parents[1]
def boundary():
 s=fixed_boundary()
 decl=""" reg [31:0] run_cycles=0;
 reg [87:0] fault_snapshot=0;
"""
 s=replace(s,' wire [7:0] reply=',decl+' wire [7:0] reply=')
 s=replace(s,"command==8'hf1 ?8'h34:","command==8'hf1 ?8'h39:")
 mux='\n'+''.join("  command==8'h%02x ?fault_snapshot[%d:%d]:\n"%(0xf5+i,i*8+7,i*8) for i in range(11))+"  8'd0;"
 s=replace(s,"command==8'hf4 ?generation[15:8]:8'd0;","command==8'hf4 ?generation[15:8]:"+mux)
 s=replace(s,' assign diagnostic_fault=fault||producer_fault||(|bus_error)||(|frontend_error);',""" assign diagnostic_fault=fault||producer_fault||(|bus_error)||(|frontend_error);
 // Capture the first observed aggregate error. This monitors the existing
 // error signals; no error qualification or bus-output behavior is relaxed.
 // Captured address/control are at this sampling edge, not a reconstructed
 // offending transaction. Retain until STOP/reset; MCU reads before STOP.
 always @(posedge clock84 or posedge control_reset) begin
  if(control_reset)begin run_cycles<=0;fault_snapshot<=0;end
  else if(!running)begin run_cycles<=0;fault_snapshot<=0;end
  else begin
   run_cycles<=run_cycles+1'b1;
   if(!fault_snapshot[7] && diagnostic_fault)
    fault_snapshot<={published[7:0],run_cycles,SNES_ADDR_IN,
      3'b0,SNES_ROMSEL_IN,producer_error,frontend_error,bus_error,
      1'b1,producer_fault,fault,exhausted,busy,ready,SNES_READ_IN,SNES_WRITE_IN};
  end
 end""")
 return s

def session():
 s=(ROOT/'src/nes/firmware/nes_h1_session.c').read_text()
 return replace(s,'if(id!=0x34)','if(id!=0x39)')

def source():
 s=runtime_source().replace('NES-H1-RUNTIME-038','NES-H1-FAULT-039').replace('nes-h1-last-038.txt','nes-h1-last-039.txt')
 s=replace(s,'unsigned status,uint32_t polls,uint16_t epoch,tick_t elapsed)', 'unsigned status,uint32_t polls,uint16_t epoch,tick_t elapsed,\n                           bool detail_ok,const uint8_t detail[14])')
 s=replace(s,' char text[384];',' char text[512],hex[29];\n static const char digits[]="0123456789abcdef";\n for(unsigned i=0;i<14;i++){hex[i*2]=digits[detail[i]>>4];hex[i*2+1]=digits[detail[i]&15];}\n hex[28]=0;')
 s=replace(s,'elapsed_ticks_10ms=%lu\\nbase_restored=1\\n",','elapsed_ticks_10ms=%lu\\ndetail_ok=%u\\ndetail_hex=%s\\nbase_restored=1\\n",')
 s=replace(s,'epoch,(unsigned long)elapsed);','epoch,(unsigned long)elapsed,(unsigned)detail_ok,hex);')
 s=replace(s,' uint8_t last_status=255;',' uint8_t last_status=255,detail[14]={0};\n bool detail_ok=false;')
 s=replace(s,' snes_reset(1);\n if(gpio_owned)',""" snes_reset(1);
 // Hold CPU while reading retained FPGA error snapshot, before STOP clears it.
 if(gpio_owned && start_result==NES_H1_OK) {
  detail_ok=true;
  for(unsigned i=0;i<14;i++) {
   uint8_t tx[2]={(uint8_t)(i<3?0xf0+i:0xf5+i-3),0},rx[2]={0,0};
   if(!slow_transaction(0,tx,rx,2)){detail_ok=false;break;}
   detail[i]=rx[1];
  }
 }
 if(gpio_owned)""")
 s=replace(s,'last_status,polls,epoch,elapsed);','last_status,polls,epoch,elapsed,detail_ok,detail);')
 return s

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--upstream',type=Path,required=True);a=p.parse_args()
 subprocess.run([sys.executable,'-B','-X','utf8',str(ROOT/'tools/prepare_nes_h1_firmware.py'),'--out',str(a.out),'--upstream',str(a.upstream)],check=True)
 (a.out/'src/nes_h1_stm32.c').write_text(source(),newline='\n');(a.out/'src/nes_h1_session.c').write_text(session(),newline='\n')
 (a.out/'fault-preparation.json').write_text(json.dumps({'candidate':'NES-H1-FAULT-039','protocol_hex':'39','files':{n:hashlib.sha256((a.out/'src'/n).read_bytes()).hexdigest() for n in ('nes_h1_stm32.c','nes_h1_session.c')}},indent=2))
if __name__=='__main__':main()
