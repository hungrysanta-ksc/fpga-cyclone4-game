# SPDX-License-Identifier: MIT
"""Non-final BG range close through the existing plan/end mailbox ownership."""
from nes_delta231 import once

def apply(d):
    p=d/'nes_plan_batch206.sv';s=p.read_text()
    s=once(s,'output wire end_valid,input wire end_ready,','output wire end_valid,output wire end_partial295,input wire end_ready,')
    s=once(s,'reg bad,shortform,closed;', 'reg bad,shortform,closed,bg_closed295,partial295;')
    s=once(s,'assign end_generation=plan_generation;', 'assign end_generation=plan_generation;assign end_partial295=partial295;')
    s=once(s,'shortform<=0;closed<=0;end', 'shortform<=0;closed<=0;bg_closed295<=0;partial295<=0;end')
    s=once(s,'else closed<=0;', 'else begin closed<=0;bg_closed295<=0;end')
    s=once(s,'shortform<=1;plan_kind<=data[1:0];if(data[6:2]!=0)bad<=1;', "shortform<=1;plan_kind<=data[1:0];partial295<=data==8'h87;if(data[6:2]!=0&&data!=8'h87)bad<=1;")
    s=once(s,'0:begin plan_kind<=data[1:0];shortform<=0;', '0:begin plan_kind<=data[1:0];shortform<=0;partial295<=0;')
    s=once(s,'CHECK:if(!shape_ok||!lease_ok)nf<=1;', 'CHECK:if(!shape_ok||!lease_ok||(bg_closed295&&(partial295||plan_kind==0||plan_kind==2)))nf<=1;')
    s=once(s,'ENDING:if(end_valid&&end_ready)begin state<=WAIT;closed<=1;end', 'ENDING:if(end_valid&&end_ready)begin state<=WAIT;if(partial295)bg_closed295<=1;else closed<=1;end')
    p.write_text(s,newline='\n')
    p=d/'nes_tile_producer260.sv';s=p.read_text()
    s=once(s,'input wire end_valid,output wire end_ready,','input wire end_valid,end_partial295,output wire end_ready,')
    s=once(s,'output wire fault,output reg end_sealed,', 'output wire range_idle295,output wire fault,output reg end_sealed,')
    s=once(s,'ending<=1;sgen<=end_generation;sending<=1;', 'ending<=1;skind<=end_partial295;sgen<=end_generation;sending<=1;')
    s=once(s,'wire append_ok=', 'assign range_idle295=!hc&&!opened&&state==CHECK&&!word_valid;\n wire append_ok=')
    s=once(s,'(in_frame&&wgen!=frame_gen)||(!wend&&!valid_word)', '(in_frame&&wgen!=frame_gen)||(wend&&wkind&&!in_frame)||(!wend&&!valid_word)')
    s=once(s,'else begin end_sealed<=1;sealed_generation<=wgen;in_frame<=0;end','else if(!wkind)begin end_sealed<=1;sealed_generation<=wgen;in_frame<=0;end')
    p.write_text(s,newline='\n')
    for name in ('nes_mux260.sv','nes_joint266.sv'):
        p=d/name;s=p.read_text()
        s=once(s,'input wire end_valid,output wire end_ready,','input wire end_valid,end_partial295,output wire end_ready,')
        s=once(s,'.end_valid(end_valid),.end_ready(end_ready),','.end_valid(end_valid),.end_partial295(end_partial295),.end_ready(end_ready),')
        if name=='nes_mux260.sv':
            s=once(s,'have_identity,tile_ended;', 'have_identity;wire range_idle295;')
            s=once(s,'.fault(tfault),.end_sealed(tend),','.fault(tfault),.range_idle295(range_idle295),.end_sealed(tend),')
            s=s.replace('tile_ended<=0;','')
            s=once(s,'if(tend)begin tile_ended<=1;tiles_closed<=1;end','if(tend)tiles_closed<=1;')
            s=once(s,'if((tile_ended||tend)&&!chunk_ready)', 'if(range_idle295&&!chunk_ready)')
            assert 'tile_ended' not in s
        p.write_text(s,newline='\n')
    for name in ('nes_plan_rom267.sv','nes_plan_path267.sv'):
        p=d/name
        if not p.exists():continue
        s=p.read_text();s=once(s,'output wire ev,input wire er,','output wire ev,ep295,input wire er,')
        s=once(s,'.end_valid(ev),.end_ready(er),','.end_valid(ev),.end_partial295(ep295),.end_ready(er),')
        p.write_text(s,newline='\n')
    p=d/'joint266_tb.sv'
    if p.exists():
        s=p.read_text()
        s=once(s,' .end_valid(ev),.end_ready(er),',' .end_valid(ev),.end_partial295(ep295),.end_ready(er),')
        s=once(s,'.ev(ev),.er(er)', '.ev(ev),.ep295(ep295),.er(er)')
        s=once(s,'module joint266_tb;', 'module joint266_tb;\n wire ep295;')
        s=once(s,'wait(ev&&er);@(negedge clk);wait(!ev);','wait(ev&&er&&!ep295);@(negedge clk);wait(!ev);')
        p.write_text(s,newline='\n')
    p=d/'nes_live_joint.sv'
    if p.exists():
        s=p.read_text();s=once(s,'wire tv267,tr267,ev267,er267;', 'wire tv267,tr267,ev267,er267,ep295;')
        s=once(s,'.end_valid(ev267),.end_ready(er267),','.end_valid(ev267),.end_partial295(ep295),.end_ready(er267),')
        s=once(s,'.ev(ev267),.er(er267)', '.ev(ev267),.ep295(ep295),.er(er267)')
        p.write_text(s,newline='\n')
