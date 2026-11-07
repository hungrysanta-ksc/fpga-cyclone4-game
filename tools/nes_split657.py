"""Split ordinary records at the source. Keep cells and cancellations atomic."""
from nes_raw506 import once


def split_source(s):
    s=once(s,"output reg tx_valid,input wire tx_ready,output reg [79:0] tx_data,",
           "output wire tx_valid,input wire tx_ready,output wire [41:0] segment,")
    s=s.replace("if(tx_ready)", "if(record_accepted)")
    pos=s.index(" always @* begin")
    return s[:pos]+""" reg word_valid, suffix;
 reg [79:0] tx_data;
 wire map_offer=state==VALUE && query_kind==0;
 wire abort_offer=state==ABORT;
 assign tx_valid=word_valid;
 assign segment=abort_offer ? {2'd3,20'd0,generation,error} :
                map_offer ? {2'd0,11'd0,tx_data[63],tx_data[76:64],tx_data[14:0]} :
                suffix ? {2'd2,tx_data[39:0]} : {2'd1,tx_data[79:40]};
 wire record_accepted=tx_ready && word_valid && (abort_offer || map_offer || suffix);
 always @(posedge clk)begin
  if(reset || !word_valid)suffix<=0;
  else if(tx_ready)suffix<=!map_offer && !abort_offer && !suffix;
 end
"""+s[pos:].replace("tx_valid=","word_valid=")


def split_host(s):
    s=once(s,"input wire [79:0] record_data,","input wire [41:0] segment,")
    s=once(s,"wire header_record=record_data[79:64]==16'he000;", """wire [1:0] form=segment[41:40];
 wire abort_offer=form==3;
 wire [15:0] record_key=abort_offer?16'he002:held[79:64];
 wire [15:0] offered_generation=abort_offer?segment[19:4]:held[63:48];
 wire header_record=record_key==16'he000;""")
    s=s.replace("wire abort_record=record_data[79:64]==16'he002;","wire abort_record=abort_offer;")
    s=s.replace("wire commit_record=record_data[79:64]==16'he003;","wire commit_record=record_key==16'he003;")
    s=s.replace("record_data[79:77]==0","form==0").replace("record_data[7:0]","segment[7:0]")
    s=s.replace("record_data[14:8]","segment[14:8]").replace("cell_base<=record_data[76:64]","cell_base<=segment[27:15]").replace("cell_last<=record_data[63]","cell_last<=segment[28]")
    s=once(s,"end else if(record_valid&&record_ready)begin","""end else if(record_valid && record_ready && form==1)begin
    held[79:40]<=segment[39:0];
   end else if(record_valid&&record_ready)begin""")
    s=s.replace("record_data[79:77]","record_key[15:13]").replace("record_data[76:64]","record_key[12:0]")
    start=s.index("if(explicit_generation)map_generation")
    end=s.index("     position<=0;",start)
    return s[:start]+"""if(explicit_generation)map_generation<=offered_generation;
     if(abort_offer)held<={16'he002,60'd0,segment[3:0]};
     else begin
      if(header_record)held[63:48]<=16'h2233;
      else if(commit_record)held[63:48]<=0;
      held[39:0]<=segment[39:0];
     end
"""+s[end:]
