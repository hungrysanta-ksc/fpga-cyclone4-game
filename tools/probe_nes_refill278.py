# SPDX-License-Identifier: MIT
"""Actual ARM274 wire/refill IRQ and ordinary CPU traces on host-output278."""
import inspect,shutil,re
import probe_nes_refill274 as prior
import probe_nes_refill267 as old
from probe_nes_split274 import build,verify
from nes_delta231 import ROOT,sha,once
from nes_joint278 import patch


def tb_patch(s):
    s=once(s,' parameter real PHASE=3.5;', ''' parameter real PHASE=3.5;
 initial begin
  repeat(30)begin
   #10000000;
   $display("PROGRESS278 t=%0t f=%0d flow=%0d v=%0d op=%0d tap=%0d begin=%0d context=%0d seq=%0d",
    $time,f,dut.flow.state,dut.core.validator.state,dut.flow.header[0],dut.flow.tap_state278,
    dut.flow.begun,dut.core.validator.context_complete,dut.flow.packet_seq);
  end
 end
''')
    s=once(s,' task clear_output;', ''' integer tap_count278=0,mask_count278=0,provisional278=0,ack_count278=0;
 reg acked278=0;
 always @(posedge clk)if(!reset&&dut.core.encoder.mask_pending278)mask_count278++;
 always @(posedge host_clk)if(!reset)begin
  if(dut.flow.state==dut.flow.CHECK)acked278<=0;
  if(dut.flow.tap_capture278)tap_count278++;
  if(dut.flow.state==dut.flow.ACKWAIT&&dut.flow.qdone)begin
   if(!acked278)ack_count278++;
   acked278<=1;
  end
  if(dut.core.validator.state==dut.core.validator.V_RWRITE&&
     !dut.core.validator.v_mapmode&&!acked278)$fatal(1,"receipt before ordered ACK");
  if(dut.crc_done278)begin
   provisional278++;
   if(dut.core.memory[560+dut.crc_index278/8]&(1<<(dut.crc_index278%8)))
    $fatal(1,"raw CRC prematurely published receipt");
  end
 end
 final $display("COUNTS278 tap=%0d mask=%0d provisional=%0d orderedACK=%0d",
  tap_count278,mask_count278,provisional278,ack_count278);
 task clear_output;''')
    s=once(s,' always @(posedge clk)if(!reset)begin\n  if((flow_fault',
           ' always @(posedge host_clk)if(!reset)begin\n  if((flow_fault')
    s=once(s,'if(dut.flow.ns==2&&v_ready)',
           'if(dut.flow.state==dut.flow.WAIT_RECEIPT&&v_ready)')
    a=s.index(' always @(posedge clk)if(!reset&&output_phase)begin')
    # Replace only the ownership monitor. Guards have no ROM block, and a
    # next-task boundary would also delete the newly added ACK/CRC counters.
    b=s.index('\n end\n',a)+len('\n end\n')
    s=s[:a]+''' always @(posedge clk)if(!reset)begin
  if(dut.core.encoder.mask_pending278&&dut.core.encoder.a_we)$fatal(1,"source single port overlap");
  if(output_phase&&dut.core.ram_a_we)$fatal(1,"source write during host phase");
  if(dut.core.ram_a_we&&dut.core.ram_a_addr<512)$fatal(1,"source persistent write");
 end
 always @(posedge host_clk)if(!reset)begin
  if(dut.grant278&&(!output_phase||dut.core.encoder.q_pending||
     dut.core.encoder.mask_pending278||!dut.core.transport_empty))
   $fatal(1,"host grant before source/query/transport drain");
  if(dut.core.validator.context_write&&dut.core.validator.context_bad)
   $display("BADH2 i=%0d got=%h expected=%h epoch=%h serial=%h gen=%h raw=%h",
    dut.core.validator.rec_i,dut.context_data,dut.core.validator.context_expected,
    dut.core.validator.epoch,dut.core.validator.base_serial,dut.core.validator.generation,dut.core.validator.admitted_raw);
  if(dut.core.vf278)
   $display("BADV state=%0d fault=%0d rec=%0d cursor=%0d kind=%0d ready=%0d flow=%0d",
    dut.core.validator.state,dut.core.vf278,dut.core.validator.rec_i,dut.core.validator.cursor,
    dut.h_kind,dut.core.validator.context_complete,dut.flow.state);
  if(dut.core.ram_b_we&&dut.core.validator.state!=dut.core.validator.V_CLEARALL&&
     (!dut.core.validator.active||!output_phase))$fatal(1,"host write without source drain/grant");
  if(dut.core.ram_b_we&&dut.core.ram_b_addr>867)$fatal(1,"host RAM bound");
  if(dut.flow.ordinary_mode&&dut.flow.state==dut.flow.PREAD&&
     (dut.flow.data_command278||dut.flow.header[0]==7))$fatal(1,"original body reread");
 end
'''+s[b:]
    s=s.replace('dut.core.encoder.context_complete','dut.core.validator.context_complete')
    s=once(s,' always @(posedge clk)if(!reset)begin\n  if(dut.context_valid',
           ' always @(posedge host_clk)if(!reset)begin\n  if(dut.context_valid')
    s=s.replace('dut.core.encoder.state==dut.core.encoder.V_RWRITE',
                'dut.core.validator.state==dut.core.validator.V_RWRITE')
    s=s.replace('dut.core.encoder.state==dut.core.encoder.V_STREAM','1\'b0')
    s=s.replace('always @(posedge clk)if(!reset&&output_phase&&dut.core.encoder.state!=dut.core.encoder.V_CLEARALL)',
                'always @(posedge host_clk)if(!reset&&output_phase&&dut.core.validator.state!=dut.core.validator.V_CLEARALL)')
    s=s.replace('dut.core.encoder.state>=dut.core.encoder.H_BYTES',
                'dut.core.validator.state>=dut.core.validator.H_BYTES')
    s=s.replace('$fatal(1,"joint261 flow/lease fault', '''begin
   $display("HOST278 f=%0d flow=%0d v=%0d vf=%0d cf=%0d tap=%0d tapfault=%0d op=%0d pos=%0d cursor=%0d reads=%0d lease=%0d",
    f,dut.flow.state,dut.core.validator.state,dut.core.vf278,dut.core.cf,dut.flow.tap_state278,
    dut.flow.tap_fault278,dut.flow.header[0],dut.flow.tap_pos278,dut.core.validator.cursor,
    dut.flow.ordinary_reads,lease_valid);
   $fatal(1,"joint261 flow/lease fault''')
    s=s.replace('flow_fault,lease_fault,dut.flow.state);','flow_fault,lease_fault,dut.flow.state);end')
    return s


def prepare(*args,**kwargs):
    src,pins=prior.prepare(*args,**kwargs);d=args[0];patch(d)
    src['nes_validator278.sv']=''
    p=d/'joint266_tb.sv';p.write_text(tb_patch(p.read_text()),encoding='utf-8',newline='\n')
    for name in ['nes_joint278.py','probe_nes_refill278.py']:
        shutil.copyfile(ROOT/'tools'/name,d/name);pins[name]=sha(ROOT/'tools'/name)
    return src,pins


def worker(*args,**kwargs):
    ns=dict(old.__dict__);ns.update(verify=verify)
    exec(compile(inspect.getsource(old.worker),'worker278','exec'),ns)
    return ns['worker'](*args,**kwargs)


def main():
    ns=dict(old.__dict__);ns.update(prepare=prepare,build=build,worker=worker,__file__=__file__,__doc__=__doc__)
    exec(compile(inspect.getsource(old.main),'refill278-main','exec'),ns);ns['main']()


if __name__=='__main__':main()
