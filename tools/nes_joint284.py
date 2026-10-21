# SPDX-License-Identifier: MIT
"""Shared checked progress and level notification on the existing PB8 wire.

The immutable SPI snapshot is also the notification baseline. No event FIFO,
second counter namespace, or trusted receipt is introduced. A change after
snapshot capture remains visible until a later command captures it. E0/source
views disarm notification; the ARM must issue checked E2 before sleeping.
"""
from nes_delta231 import once
from nes_joint283 import patch as previous,from280 as previous280


def apply(d):
    p=d/'nes_spi270.sv';s=p.read_text()
    s=once(s,' input wire request_crc_enable,',
           ' output wire progress_irq284,output reg progress_mode284,\n input wire request_crc_enable,')
    s=once(s,' reg reply_bit282;', ''' // Compare only autonomous progress: retirement, phase and plan flags.
 // accepted counters change on ARM writes, and cannot authorize a wake/credit.
 reg armed284;
 assign progress_irq284=armed284&&
   ({output_status[175],output_status[151:128],plan_status[167:160]}!=
    {snapshot[175],snapshot[151:128],snapshot[127:120]});
 reg reply_bit282;''')
    s=once(s,'request_crc<=0;status_crc<=0;snapshot<=0;',
           'armed284<=0;progress_mode284<=0;request_crc<=0;status_crc<=0;snapshot<=0;')
    s=once(s,'      command<=incoming;', '''      armed284<=incoming==8'he2||incoming==8'he8||incoming==8'he1||incoming==8'he9;
      if(incoming==8'he2||incoming==8'he8)progress_mode284<=1;
      else if(incoming==8'hd0||incoming==8'hd2||incoming==8'hd3||incoming==8'hd4||incoming==8'hd5)progress_mode284<=0;
      command<=incoming;''')
    s=once(s,"       8'he2:begin snapshot<={8'hf9,output_status[175:128],8'd0,120'd0};status_length<=8;end\n",'')
    s=once(s,"       8'he1,8'he9:begin", "       8'he1,8'he9,8'he2,8'he8:begin")
    s=once(s,"       8'he8:begin snapshot<=plan_status;status_length<=19;end\n",'')
    p.write_text(s,encoding='utf-8',newline='\n')
    p=d/'nes_queue260.sv';s=p.read_text().replace("(command==8'he2 ? 9 : 24)","(command==8'he2 ? 12 : 24)")
    p.write_text(s,encoding='utf-8',newline='\n')
    p=d/'nes_plan_spi200.sv';s=p.read_text()
    s=once(s,'if(count!=20||bits!=0)', 'if(count!=12||bits!=0)')
    a=s.index(' assign status270=');b=s.index('\nendmodule',a)
    s=s[:a]+''' // Chunk identity is checked by the output E0 owner. The plan endpoint
 // publishes only its admission/lifetime; no duplicated descriptor view.
 assign status270={8'hd7,8'd4,{fault||source_fault,4'd0,retiring,ended,
   live&&!ended&&!retiring&&plan_idle&&accepted!=16'hffff},accepted,144'd0};
'''+s[b:]
    p.write_text(s,encoding='utf-8',newline='\n')
    p=d/'nes_live_joint.sv'
    if p.exists():
        s=p.read_text()
        s=once(s,'assign out_observe_ready=external_memory_ready;',
               'wire progress_irq284,progress_mode284;\nassign out_observe_ready=progress_mode284?progress_irq284:external_memory_ready;')
        s=once(s,'nes_spi270 spi_front270(',
               'nes_spi270 spi_front270(.progress_irq284(progress_irq284),.progress_mode284(progress_mode284),')
        p.write_text(s,encoding='utf-8',newline='\n')


def patch(d):previous(d);apply(d)
def from280(d):previous280(d);apply(d)
