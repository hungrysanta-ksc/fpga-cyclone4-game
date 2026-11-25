module nes_supply1016_host(input wire clk,reset,active,cancel,first_e9,writer,returned,reader,kind,
 input wire [7:0] units,
 input wire [31:0] token,input wire [15:0] generation,input wire retired,input wire [7:0] op,
 input wire query,set_page,input wire [7:0] incoming,input wire [4:0] index,input wire [31:0] q,
 output reg origin_toggle,output wire [8:0] rd,output wire bank_we,output wire [31:0] bank_word,output reg [7:0] reply);
 reg [7:0] page;
 reg [24:0] timer;
 reg [2:0] count;
 reg complete,read_ok,prior,bad,clear_record;
 reg [7:0] published;
 assign bank_we=returned && count<3;
 assign rd=bank_we?{7'h7f,count[1:0]}:{(page[7]?7'h7f:page[6:0]),!index[3],index[2]};
 assign bank_word={3'b0,token[10:0],reader,kind,units,timer[23:16]};
 always @(posedge clk)begin
  clear_record<=reset||!active||cancel;
  prior<=writer;
  if(!timer[24])timer<=timer+1'b1;
  if(returned)begin
   if(!(&count))count<=count+1'b1;
  end
  if(writer!=prior)published<=timer[23:16];
  if(timer[24]&&(returned||writer!=prior))bad<=1;
  if(retired&&op==3)complete<=1;
  if(query)read_ok<=complete&&!bad;
  if(set_page)page<=incoming;
  if(first_e9)begin origin_toggle<=!origin_toggle;timer<=0;count<=0;complete<=0;bad<=0;end
  if(first_e9||returned||writer!=prior||retired)read_ok<=0;
  if(clear_record)begin read_ok<=0;complete<=0;bad<=1;end
  if(reset)origin_toggle<=0;
 end
 always @(posedge clk)begin
  case(index)
   1:reply<=8'hb6;
   2:reply<=generation[7:0];3:reply<=generation[15:8];
   4:reply<=token[7:0];5:reply<=token[15:8];6:reply<=token[23:16];7:reply<=token[31:24];
   24:reply<=published;25,26,28,29:reply<=0;
   27:reply<={5'b0,count};
   30:reply<=page;31:reply<=read_ok&&!clear_record?8'ha5:0;
   default:case(index[1:0])
    0:reply<=q[7:0];1:reply<=q[15:8];
    2:reply<=q[23:16];3:reply<=q[31:24];
   endcase
  endcase
 end
endmodule
