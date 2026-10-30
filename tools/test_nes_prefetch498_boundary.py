# SPDX-License-Identifier: MIT
"""498 real plan END decoder + lease; top-level enable/ACK expressions extracted verbatim.
This boundary test does not replace whole exporter/65816/IRQ timing verification.
"""
import argparse,hashlib,json,re,subprocess
from pathlib import Path
TB=r'''module boundary498;
 reg h=0,n=0;always #5 h=~h;always #19 n=~n;
 reg reset=1,stop=0,cb=0,owned=0,valid=0,release_in=0,drained=0,retire=0;
 reg [15:0] gen=0;reg wv=0,seal=0,er=0;reg [7:0] wd=0;reg[15:0] crc=0;
 wire wr,rd,rc,pc,pf,ev,lease,permit,export_ok,waiting,lf,release_out;wire[15:0] saved,eg;wire[31:0] epoch;
 nes_capture_lease201 l(n,reset,stop,cb,owned,valid,gen,release_in,4'd0,1'b1,1'b1,1'b0,32'd7,drained,rc,eg,release_out,lease,permit,export_ok,epoch,saved,waiting,lf);
 nes_plan_batch206 p(.host_clk(h),.nes_clk(n),.reset(reset),.active(1'b1),.stop(stop),.source_fault(1'b0),
 .write_valid(wv),.write_ready(wr),.write_data(wd),.retire(retire),.retire_done(rd),.retire_permitted(permit),.retire_commit(rc),
 .seal(seal),.seal_length(10'd3),.seal_plans(5'd1),.seal_crc(crc),.fault(pf),.lease_valid(lease),.lease_generation(saved),
 .plan_ready(1'b1),.tile_done(1'b0),.end_valid(ev),.end_ready(er),.end_generation(eg),.plan_closed(pc));
 wire export_permitted204=export_ok,lease204=lease,plan_closed204=pc,reader_drained204=drained,direct_nes_fault204=pf;
 wire run_enable,start_ok;reg exreset=1;wire native_export_busy204;wire[3:0] exerror;
 nes_native_export203 #(.MAX_CYCLES(1024)) ex(.clk(n),.reset(reset||exreset),.enable(run_enable),.start_permitted(start_ok),.frame_owned(owned),.geometry_valid(valid),.frame_generation(gen),
 .patch_count(3'd0),.row_count(8'd224),.object_count(8'd0),.exception_count(8'd0),.group_count(6'd1),.palette_count(6'd1),
 .response(1'b0),.hit(1'b0),.data(64'd0),.tx_ready(1'b0),.ack_valid(1'b0),.ack_accept(1'b0),.ack_generation(16'd0),.busy(native_export_busy204),.error(exerror));
 wire[23:0] native_ack_data=24'h010000;
 assign run_enable=ENABLE_EXPR;
 assign start_ok=START_EXPR;
 wire early=run_enable&&(start_ok||native_export_busy204);
 wire accepted=ACK_EXPR;
 task tick;begin @(posedge n);#1;@(negedge n);end endtask
 task boot;begin
 exreset=1;reset=1;stop=0;cb=0;owned=0;valid=0;release_in=0;drained=0;retire=0;wv=0;seal=0;er=0;gen=0;
 repeat(5)tick;reset=0;repeat(5)tick;cb=1;tick;cb=0;owned=1;valid=1;gen=1;release_in=1;tick;release_in=0;owned=0;valid=0;
 if(!lease||saved!=1||export_ok||lf)$fatal(1,"lease initial");
 cb=1;tick;cb=0;owned=1;valid=1;gen=2;tick;
 end endtask
 function[15:0] c16(input[15:0] x,input[7:0] b);reg[15:0] c;integer i;begin c=x^{b,8'd0};for(i=0;i<8;i=i+1)c=c[15]?(c<<1)^16'h1021:c<<1;c16=c;end endfunction
 task bytein(input[7:0] b);begin @(negedge h);while(!wr)@(negedge h);wd=b;wv=1;@(negedge h);wv=0;end endtask
 task endin(input[15:0] g);begin
 bytein(8'h83);bytein(g[7:0]);bytein(g[15:8]);crc=c16(c16(c16(16'hffff,8'h83),g[7:0]),g[15:8]);
 @(negedge h);seal=1;@(negedge h);seal=0;
 end endtask
 task stopped;begin stop=1;repeat(5)tick;if(early||accepted||lease||pc)$fatal(1,"STOP publication");end endtask
 integer i;
 initial begin
 boot;drained=1;tick;if(early)$fatal(1,"drain alone allowed export");if(accepted)$fatal(1,"early COMMIT");
 endin(1);repeat(40)tick;if(!ev||pc||early||pf)$fatal(1,"END must be accepted");
 drained=0;er=1;tick;er=0;if(!pc||early)$fatal(1,"END without drain");exreset=0;drained=1;tick;
 if(!early||accepted||saved!=1||lf||pf)$fatal(1,"early export identity");
 drained=0;tick;if(!native_export_busy204||exerror||!early)$fatal(1,"active export lost on ROM resume");
 exreset=1;drained=1;tick;
 @(negedge h);retire=1;@(negedge h);retire=0;
 repeat(40)tick;if(lease||!export_ok||!accepted||pc||lf||pf)$fatal(1,"retire rearm");
 release_in=1;tick;release_in=0;if(!lease||saved!=2||accepted||early||lf)$fatal(1,"new COMMIT identity");stopped;
 for(i=0;i<3;i=i+1)begin boot;drained=1;if(i>0)begin endin(1);repeat(40)tick;if(i==2)begin er=1;tick;er=0;end end stopped;end
 boot;drained=1;er=1;endin(2);repeat(50)tick;if(!pf||pc||early)$fatal(1,"foreign END accepted");stopped;
 $display("PASS BOUNDARY498 accepted END/drain, old identity, COMMIT gate, retire, STOP, foreign END");$finish;
 end
 initial begin #100000;$fatal(1,"timeout");end
 endmodule'''
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 for k in ['board','bin','out']:p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();a.out.mkdir(exist_ok=False)
 joint=(a.board/'nes_live_joint.sv').read_text()
 enable='(export_permitted204||(lease204&&plan_closed204))&&!direct_nes_fault204'
 start='export_permitted204||reader_drained204'
 ack='native_ack_data[16]&&export_permitted204'
 assert '.enable('+enable+')' in joint and '.ack_accept('+ack+')' in joint and '.start_permitted('+start+')' in joint
 names=['nes_domain_reset124.sv','nes_native_mailbox206.sv','nes_capture_lease201.sv','nes_plan_batch206.sv','nes_native_export203.sv']
 for name in names:(a.out/name).write_bytes((a.board/name).read_bytes())
 def run(name,args):
  with (a.out/(name+'.log')).open('wb')as f:r=subprocess.run([str(a.bin/(args[0]+'.exe')),*args[1:]],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=90)
  log=(a.out/(name+'.log')).read_text(errors='replace');return r.returncode,log
 code,log=run('lib',['vlib','work']);assert code==0,log
 for tag,e,c,z,error in [('normal',enable,ack,start,None),('no_end',enable.replace('&&plan_closed204',''),ack,start,'drain alone allowed export'),('no_commit_gate',enable,'native_ack_data[16]',start,'early COMMIT'),('continuous_drain','('+enable+')&&start_ok',ack,start,'active export lost on ROM resume'),('no_drain',enable,ack,"1'b1",'END without drain')]:
  (a.out/'tb.sv').write_text(TB.replace('ENABLE_EXPR',e).replace('ACK_EXPR',c).replace('START_EXPR',z))
  code,log=run(tag+'-compile',['vlog','-sv',*names,'tb.sv']);assert code==0 and '** Error' not in log,log[-1500:]
  code,log=run(tag,['vsim','-c','boundary498','-do','onerror {quit -code 1}; run -all; quit -f'])
  if error:assert '** Fatal' in log and error in log,log[-1500:]
  else:assert code==0 and 'PASS BOUNDARY498' in log and '** Fatal' not in log,log[-1500:]
 result={'passed':True,'scope':__doc__,'four_mutants_rejected':True,'whole_pipeline':False,'sha256':{n:hashlib.sha256((a.board/n).read_bytes()).hexdigest()for n in names+['nes_live_joint.sv']}}
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
