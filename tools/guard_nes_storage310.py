# SPDX-License-Identifier: MIT
"""Retained guards plus early-storage STOP, duplicate, replay and ACK faults."""
import os
import guard_nes_ingress307 as old
from nes_storage310 import apply
from nes_delta231 import once
previous=old.old.record305

def patch(d):previous(d);apply(d)
old.old.record305=patch
previous_observe=old.old.observe305

def observe(s):
    s=previous_observe(s)
    s=once(s,'!((dut.core.ram_b_addr<166)', '!((dut.core.validator.exec_op298==5&&dut.core.validator.state==dut.core.validator.E_CAP298&&dut.core.ram_b_addr>=166&&dut.core.ram_b_addr<256)||(dut.core.ram_b_addr<166)')
    return once(s,' initial begin : result264', '''
 initial begin : storage310
  if(GNEG>=75&&GNEG<=81)begin
   if(GNEG==75)wait(dut.core.validator.exec_op298==5&&dut.core.validator.state==dut.core.validator.E_CAP298&&dut.core.validator.packet_at298==20);
   if(GNEG==76||GNEG==79)wait(dut.flow.state==dut.flow.IDLE&&dut.stored310);
   if(GNEG==77)wait(dut.flow.state==dut.flow.REPLAYWAIT310&&dut.core.validator.packet_at298==24);
   if(GNEG==78)wait(dut.flow.state==dut.flow.REPLAYWAIT310&&dut.core.validator.packet_at298==40);
   if(GNEG==80)wait(dut.flow.state==dut.flow.XBEGIN298&&dut.flow.header[0]==15);
   if(GNEG==81)wait(dut.flow.state==dut.flow.REPLAY310);
   @(negedge host_clk);injected264=1;
   if(GNEG<=77)begin
    disable bus263;bus_read=1;bus_write=1;test_abort=1;
    #2000;if(dut.stored310||dut.exec_busy298||dut.exec_done298||dut.core.ram_b_we||v_sealed||bus_valid)$fatal(1,"STOP retained storage ownership");
   end
   if(GNEG==78)force dut.core.validator.data310=0;
   if(GNEG==79)begin disable bus263;bus_read=1;bus_write=1;token261(dut.flow.last_map_token);wr261(24'h006058,8'h5a);end
   if(GNEG==80)force dut.core.validator.stored310=1;
   if(GNEG==81)force dut.core.validator.stored_length310=41;
   wait(source_fault);
   if((GNEG==78||GNEG==80||GNEG==81)&&dut.core.validator.fault!=3)$fatal(1,"wrong stored manifest rejection");
  end
 end
 initial begin : result264''')
old.old.observe305=observe
old.engine.CASES.update({75:'STOP during storage write',76:'STOP after credit return before consumption',77:'STOP during stored replay',78:'independent replay rejects bad codec',79:'final ACK rejected while stored only',80:'duplicate stored requirements rejected',81:'stored replay exact-length rejection'})
if os.environ.get('NES310_EARLY_GUARDS')=='1':
    original_packets=old.engine.prior.packets
    def packets(path):
        pp=list(original_packets(path));at=next(i for i,p in enumerate(pp) if p[0]==15)
        p=pp.pop(at);q=bytearray(p[:40]);q[1]=2;q.append(1)
        i=40
        while i<206:
            zero=p[i]==0;n=1
            while i+n<206 and n<128 and (p[i+n]==0)==zero:n+=1
            q.append((128 if zero else 0)|(n-1))
            if not zero:q.extend(p[i:i+n])
            i+=n
        assert len(q)<=106
        q[12:14]=(len(q)-16).to_bytes(2,'little');pp.insert(2,bytes(q))
        return [p[:2]+i.to_bytes(2,'little')+p[4:] for i,p in enumerate(pp)]
    old.engine.prior.packets=packets
if __name__=='__main__':old.old.main()
