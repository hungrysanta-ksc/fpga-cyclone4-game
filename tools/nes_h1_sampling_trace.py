# SPDX-License-Identifier: MIT
# Trace retained043 primitive outputs with all SDF notifiers enabled.
import sys,json
from pathlib import Path
import nes_h1_qualified_gate as base
signals=[('meta','addr_meta',23,0),('sync','addr_sync',23,0),('latched','read_address',23,0),('rd','rd_sync',1,0),('sel','sel_sync',1,0),('event','event_cause',6,0),('error','frontend_error',3,0)]
def tap(name):return 'dut.'+chr(92)+'boundary|link|transport|frontend|'+name+' '
scalars=['rd_previous','read_seen','read_issued','output_valid']
fields=['$time','read_count','SNES_ADDR_IN','SNES_READ_IN','SNES_ROMSEL_IN']+[tap(name)+f'[{high}:{low}]' for _,name,high,low in signals]+[tap(name+'~q') for name in scalars]+[tap('pending')+'[1:0]']
fmt=['%0t','%0d','%h','%b','%b']+['%b']*(len(fields)-5)
header=['time_ps','reads','raw_addr','raw_rd','raw_sel']+[n for n,_,_,_ in signals]+scalars+['pending']
monitor=chr(10).join([
' integer trace_fd;reg tracing=0;',
' initial begin',
' trace_fd=$fopen("sample-trace.txt","w");',
' $fdisplay(trace_fd,"'+' '.join(header)+'");',
' end',
' always @(negedge dut.'+chr(92)+'pll|altpll_component|auto_generated|wire_pll1_clk[0]~clkctrl_outclk )',
' if(tracing)$fdisplay(trace_fd,"'+' '.join(fmt)+'",'+','.join(fields)+');'])
base.TB=base.TB.replace(' task automatic dump;',monitor+chr(10)+' task automatic dump;').replace('  #(PHASE);','  tracing=1;#(PHASE);')
if __name__=='__main__':
 protocol='43'
 if '--protocol' in sys.argv:
  at=sys.argv.index('--protocol');protocol=sys.argv[at+1];del sys.argv[at:at+2]
 assert protocol in ('43','44')
 base.TB=base.TB.replace("8'h43","8'h"+protocol)
 out=Path(sys.argv[sys.argv.index('--out')+1]);net=Path(sys.argv[sys.argv.index('--netlist')+1]).read_text()
 for _,name,hi,lo in signals:
  for bit in range(lo,hi+1):
   needle='.q('+chr(92)+'boundary|link|transport|frontend|'+name+' ['+str(bit)+'])'
   assert needle in net,(name,bit)
 for name in scalars:assert '.q('+chr(92)+'boundary|link|transport|frontend|'+name+'~q )' in net,name
 base.main()
 rows=(out/'sample-trace.txt').read_text().splitlines();keys=rows[0].split();first={}
 for row in rows[1:]:
  data=dict(zip(keys,row.split()))
  for key in ('meta','sync','event','error'):
   if key not in first and any(c in data[key].lower() for c in 'xz'):first[key]=data
 (out/'trace-result.json').write_text(json.dumps({'retained_q_taps_checked':True,'rows':len(rows)-1,'first_unknown':first},indent=2)+chr(10))
 print(json.dumps({'trace_rows':len(rows)-1,'first_unknown':first},indent=2))
