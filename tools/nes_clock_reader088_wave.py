# SPDX-License-Identifier: MIT
"""Replay actual C GPIO writes and every consumed MISO bit against frozen CF87."""
from pathlib import Path
import argparse,json,os,re,shutil
from nes_clock_observation087 import materialize
from nes_spi_boot import ROOT,put,run,sha

def main():
 p=argparse.ArgumentParser()
 for n in ['out','host','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
 p.add_argument('--mutation',choices=['wrong-divider','live-snapshot'])
 a=p.parse_args();assert re.fullmatch(r'18000@(?:localhost|127\.0\.0\.1)',os.environ.get('SALT_LICENSE_SERVER',''))
 out=a.out.resolve();host=a.host.resolve();out.mkdir(parents=True,exist_ok=False);assert str(out).isascii()
 h=json.loads((host/'result.json').read_text());assert h['candidate']=='NES-CLOCK-READER-088' and sha(host/'wave.txt')==h['wave_sha256']
 for n in ['nes_clock_reader088.c','nes_clock_reader088.h']:assert sha(ROOT/'src/nes/firmware'/n)==h['sources'][n]
 shutil.copy2(host/'wave.txt',out/'wave.txt');shutil.copy2(__file__,out/'executed-driver.py')
 files=materialize(out);production={n:sha(out/n) for n in files}
 if a.mutation=='wrong-divider':
  pth=out/'nes_clock_observation087.sv';put(pth,pth.read_text().replace('ref_sync[0],divider[3]','ref_sync[0],divider[2]'))
 if a.mutation=='live-snapshot':
  pth=out/'nes_clock_observation087.sv';s=pth.read_text().replace('reg [127:0] snapshot=0;',"wire [127:0] snapshot={8'd0,8'd16,32'(WINDOW),published_count,window_sequence,4'b0,published_gap,ever_gap,live,valid,8'h87};")
  s=re.sub(r"      if\(\{shift\[6:0\],mosi_sync\[1\]\}==8'hc0\).*?8'h87\};",'',s,flags=re.S);put(pth,s)
 tb=(ROOT/'tests/nes-functional/clock_observation087_tb.sv').read_text()
 tb=tb[:tb.index(' task automatic begin_spi;')]
 tb=tb.replace('module clock_observation087_tb;','module clock_reader088_tb;')
 if h.get('trace_mode','active')=='active':tb=tb.replace('ref_enable=0','ref_enable=1')
 tb=tb.replace(' always @(negedge CLKIN)parked();','')
 tb+=''' integer f,rc,event_id,value,checked=0,rows=0;longint unsigned stamp;real delta;
 initial begin
  f=$fopen("wave.txt","r");if(!f)$fatal(1,"MISSING_WAVE");
  while(!$feof(f))begin
   rc=$fscanf(f,"%d %d %d\\n",stamp,event_id,value);
   if(rc!=3)$fatal(1,"BAD_WAVE_ROW");
   delta=stamp-$realtime;if(delta<0)$fatal(1,"TIME_REGRESSION");#(delta);
   case(event_id)
    0:SPI_SS=value;
    1:SPI_SCK=value;
    2:SPI_MOSI=value;
    3:begin
     if(SPI_MISO!==value[0])$fatal(1,"C_MISO_MISMATCH row=%0d t=%0t got=%b expected=%b",rows,$time,SPI_MISO,value[0]);
     checked=checked+1;
    end
    default:$fatal(1,"BAD_EVENT");
   endcase
   rows=rows+1;parked();
  end
  #2000;parked();if(!SPI_SS||SPI_MISO!==1'bz)$fatal(1,"FINAL_CS_NOT_RELEASED");
  $display("PASS C_READER088 checked=%0d rows=%0d end_ns=%0d",checked,rows,stamp);$finish;
 end
 initial begin #4000000000.0;$fatal(1,"TIMEOUT");end
endmodule
'''
 put(out/'tb.sv',tb)
 for tool,args in [('vlib',['work']),('vlog',['-sv',*files,'tb.sv'])]:run([a.questa_bin/(tool+'.exe'),*args],out,tool)
 try:log=run([a.questa_bin/'vsim.exe','-c','clock_reader088_tb','-do','onerror {quit -code 1}; run -all; quit -f'],out,'simulation',900)
 except RuntimeError:
  if not a.mutation:raise
  log=(out/'simulation.log').read_text(errors='replace')
 if a.mutation:
  assert '** Fatal:' in log and 'C_MISO_MISMATCH' in log
  result=dict(expected_failure='C_MISO_MISMATCH')
 else:
  m=re.search(r'PASS C_READER088 checked=(\d+) rows=(\d+) end_ns=(\d+)',log);assert m and '** Fatal:' not in log
  assert int(m[1])==16+(h['normal_frames']-1)*136
  result=dict(checked_bits=int(m[1]),rows=int(m[2]),end_ns=int(m[3]))
 result.update(candidate='NES-CLOCK-READER-088',mutation=a.mutation,trace_mode=h.get('trace_mode','active'),production_sources=production,host_result_sha256=sha(host/'result.json'),wave_sha256=sha(out/'wave.txt'),hardware_execution=False,installable=False)
 put(out/'result.json',json.dumps(result,indent=2)+'\n');print(result,flush=True)

if __name__=='__main__':main()
