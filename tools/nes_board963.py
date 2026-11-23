"""Connect the seven-byte advisory page to the checked, immutable 961 row RAM."""
import argparse
import shutil
from pathlib import Path
from nes_raw506 import once
from prepare_nes_frame900 import QUARTUS, fit


def board(temp):
    old=temp/'nes-trial816-board961'
    dst=temp/'nes-trial816-board963'
    dst.mkdir()
    for sub in ('rtl','sys'):
        shutil.copytree(old/sub,dst/sub)
    for f in old.iterdir():
        if f.suffix in ('.sv','.v','.vhd','.qsf','.qpf','.sdc','.tcl','.hex'):
            shutil.copyfile(f,dst/f.name)
    def edit(file,pairs):
        path=dst/file
        code=path.read_text()
        for a,b in pairs:
            code=once(code,a,b)
        path.write_text(code,newline='\n')

    edit('nes_plan_spi200.sv',[
        ('output wire first905,','output wire page963,output wire [25:0] payload963,output wire first905,'),
        ("wire ours=command==8'he8","wire header963=command==8'heb;\n wire ours=header963||command==8'he8"),
        (' assign first905=',""" // The mailbox samples the existing EA parser fields on the deselect edge.
 // A malformed, partial or stale advisory cannot consume a plan credit.
 assign page963=live&&ss[1]&&!prev_ss&&header963&&can_write&&!ended&&!retiring&&accepted==0&&
      count==7&&bits==0&&received8==request8&&tail==8'ha5&&received16[10:8]==0&&received16[7:5]==0;
 assign payload963={length,received16[4:0],received16[15:11]};
 assign first905="""),
        ("if(command==8'he8)begin if(count!=20","if(header963)begin end\n     else if(command==8'he8)begin if(count!=20"),
        ("(command==8'hea&&count<=4)","((command==8'hea||header963)&&count<=4)"),
        ("end else if(command==8'hea)begin\n      case(count)","end else if(command==8'hea||header963)begin\n      case(count)")])
    edit('nes_direct206.sv',[
        (' nes_plan_spi200 endpoint(',''' wire page_src963,page_dst963;
 wire [25:0] payload_src963,payload_dst963;
 nes_native_mailbox206 #(.WIDTH(26),.CONSUMER_CAPTURE(1)) page_mail963(
  .src_clk(host_clk),.dst_clk(nes_clk),.reset(reset||cancel||nes_error),
  .src_valid(page_src963),.src_ready(),.src_data(payload_src963),
  .dst_valid(page_dst963),.dst_ready(1'b1),.dst_data(payload_dst963));
 nes_plan_spi200 endpoint(.page963(page_src963),.payload963(payload_src963),'''),
        (' source(.hint(hint)',' source(.page963(page_dst963 && payload_dst963[25:10]==captured_generation),.page_base963(payload_dst963[9:0]),.hint(hint)')])
    edit('nes_source_tile192.sv',[
        (' input wire clk,reset,stop,frame_owned,',' input wire page963,input wire [9:0] page_base963,\n input wire clk,reset,stop,frame_owned,'),
        (' ahead(.clk(clk)',' ahead(.page963(page963),.page_base963(page_base963),.plan963(plan_valid),.clk(clk)')])
    edit('nes_e9_rows914.sv',[
        (' input wire clk, reset,',' input wire page963,plan963,input wire [9:0] page_base963,\n input wire clk, reset,'),
        (' reg checked952;', ''' reg early963,first_half963;
 wire stop963=hint||plan963||demand;
 reg checked952;'''),
        ('live && armed && pending952','live && ((armed&&pending952)||(early963&&!stop963))'),
        ('if(!live) begin selected952<=0;',"""if(!live) begin early963<=0;first_half963<=0;selected952<=0;"""),
        ('  else if(cross961', '''  else if(page963&&empty_capture&&!armed&&!stop963&&!pending952)begin
   early963<=1;first_half963<=page_base963[0];
   page952<=page_base963[9:1];cursor952<={page_base963[0],6'd0};
  end else if(cross961'''),
        ('if(cursor952==15 ||','if(early963 && (&cursor952[5:0]) && cursor952[6]!=first_half963)early963<=0;\n   if(cursor952==15 ||'),
        (' end\n assign request=foreground','  if(live&&stop963)early963<=0;\n end\n assign request=foreground')])
    return dst


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('temp',type=Path)
    p.add_argument('--fit',action='store_true')
    a=p.parse_args()
    board(a.temp)
    if a.fit:
        fit(a.temp,963,QUARTUS)
