# SPDX-License-Identifier: MIT
"""Check the actual E8 bytes and measure the qualification-to-start edges on the selected top."""
import argparse
import json
from pathlib import Path
import re
import subprocess
from nes_raw506 import once,sha
from test_nes_raw506_joint import crc


def main():
    p=argparse.ArgumentParser()
    for k in ('rtl','bin','out'):p.add_argument('--'+k,type=Path,required=True)
    modes=p.add_mutually_exclusive_group()
    modes.add_argument('--shared-campaign',action='store_true');modes.add_argument('--local-campaign',action='store_true')
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    bench=Path(__file__).resolve().parents[1]/'tests/nes-functional'
    root=a.rtl.parent
    results={}
    targets=[('base','nes-plan569-board01'),('transport','nes-gate570-board01'),('joint','nes-gate570-board03')]
    if a.shared_campaign:targets=[('shared','nes-gate570-board04')]
    if a.local_campaign:targets=[('local','nes-gate570-board05')]
    for name,board_name in targets:
        board=root/board_name;prev=a.rtl/name;d=a.out/name;d.mkdir()
        modules=json.loads((a.rtl/'result.json').read_text())[name]['modules']
        assert all(sha(board/f)==h for f,h in modules.items())
        top=(bench/'gate570_tb.sv').read_text()
        top=once(top,' integer resumes=0;', (bench/'gate570-observe.svh').read_text()+'\n integer resumes=0;')
        top=once(top,'finish_fault();restart();data_frame(0,32);','finish_fault();status570(ingress?0:1,1);restart();data_frame(0,32);')
        top=once(top,'  $display("PASS570 TOP','  external_stop570();\n  $display("PASS570 TOP')
        if name in ('joint','shared','local'):
            top=once(top,".mem_ready(1'b0),.mem_response(1'b0),.mem_error(1'b0),.mem_response_address(22'd0),.mem_data(8'd0)",
                     ".mem_ready(memory_open),.mem_response(memory_reply),.mem_error(1'b0),.mem_response_address(reply_address),.mem_data(8'h63)")
            top=once(top,".address(24'h6040),.read_n(1'b1),.write_n(1'b1),\n  .data_in(8'd0)",
                     ".address(bus),.read_n(rd_n),.write_n(wr_n),.data_in(wdata)")
            top=once(top,' nes_direct206 dut(', (bench/'gate570-bulk.svh').read_text()+'\n nes_direct206 dut(')
            top=once(top,'  // One accepted bank','  if($test$plusargs("BULK"))begin bulk570();$finish;end\n  // One accepted bank')
            payload=bytes.fromhex('80ba030100010083ba03')
            frame=bytes([0xe9,len(payload),0,2])+payload+crc(payload,16,0x1021,65535).to_bytes(2,'big')
            (d/'fresh.hex').write_text(''.join(f'{v:02x}\n' for v in frame+bytes([crc(frame,8,7,0),0xa5])))
        (d/'top.sv').write_text(top);(d/'requests.hex').write_bytes((prev/'requests.hex').read_bytes())
        guard=once((prev/'guard.sv').read_text(),' task check_off;', '''
 time both_good,unlock_at;
 always @(posedge locked)unlock_at=$time;
 wire qualified_pair=clock_guard.ref_qualified&&clock_guard.mem_qualified;
 always @(posedge qualified_pair)both_good=$time;
 always @(negedge release_memory)if(locked&&!guard_fault&&$time>100000)begin
  if(!qualified_pair)$fatal(1,"early memory start");
  $display("ALLOW570 since_lock=%0d since_pair=%0d",$time-unlock_at,$time-both_good);
 end
 task check_off;''')
        (d/'guard.sv').write_text(guard)
        def run(exe,argv,label):
            path=d/(label+'.log')
            with path.open('wb') as f:
                subprocess.run([str(a.bin/(exe+'.exe')),*map(str,argv)],cwd=d,check=True,timeout=90,stdout=f,stderr=subprocess.STDOUT)
            return path.read_text(errors='replace')
        run('vlib',['work'],'lib')
        run('vlog',['-sv','+define+SPLIT',*[board/f for f in modules],d/'guard.sv',d/'top.sv'],'compile')
        phases=[]
        for ph in (0,1):
            flags=['+SHIFT'] if ph else []
            ctl=flags+(['+GUARDED'] if name!='base' else [])+(['+INGRESS'] if name in ('joint','shared','local') else [])
            l=run('vsim',['-c','gate570_tb',*ctl,'-do','run -all; quit -f'],f'wire{ph}')
            assert 'PASS570 TOP' in l and '** Fatal:' not in l,l[-700:]
            e8=re.findall(r'E8570 flags=(\w+) count=(\d+)',l)
            assert e8==[('80','0' if name in ('joint','shared','local') else '1'),('01','0')],e8
            g=run('vsim',['-c','guard563_tb',*flags,'-do','run -all; quit -f'],f'guard{ph}')
            assert 'PASS563 6 losses and common reset' in g
            rows=[list(map(int,r)) for r in re.findall(r'ALLOW570 since_lock=(\d+) since_pair=(\d+)',g)]
            assert rows and all(0<x and 0<y for x,y in rows)
            bulk=[]
            if name in ('joint','shared','local'):
                for partial in (0,1):
                    opts=['+BULK']+(['+SHARED'] if name in ('shared','local') else [])+(['+PARTIAL'] if partial else [])
                    sample=run('vsim',['-c','gate570_tb',*ctl,*opts,'-do','run -all; quit -f'],f'bulk{ph}-{partial}')
                    assert f'PASS570 BULK consumes={1-partial}' in sample and '** Fatal:' not in sample,sample[-700:]
                    bulk.append(dict(partial=partial,consumes=1-partial))
            phases.append(dict(bulk=bulk,e8=e8,common_reset_while_stopped=True,allow_ps=rows))
        results[name]=phases
    (a.out/'result.json').write_text(json.dumps(results,indent=2)+'\n')


if __name__=='__main__':main()
