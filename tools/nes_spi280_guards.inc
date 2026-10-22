 task prefix(input [7:0] op,input [15:0] token,input [15:0] gen,input [7:0] flags);
 begin
  for(integer i=0;i<1024;i++)tx[i]=0;
  tx[0]=op;tx[1]=token[15:8];tx[2]=token[7:0];tx[3]=gen[7:0];tx[4]=gen[15:8];tx[5]=flags;
  for(integer i=0;i<6;i++)tx[6]=crc8(tx[6],tx[i]);tx[7]=8'ha5;
 end endtask
 task send_record(input integer n);
 begin
  for(integer part=0;part<(n==248?2:1);part++)begin
   @(negedge src_clk);length280=n==248?124:n;flush280=n!=248||part==1;record_valid280=1;
   do @(posedge src_clk);while(!record_ready280);
   @(negedge src_clk);record_valid280=0;
   for(integer i=0;i<length280;i++)begin
    byte280=i+part*124;byte_valid280=1;
    do @(posedge src_clk);while(!byte_ready280);
    @(negedge src_clk);byte_valid280=0;
   end
  end
  repeat(30)@(negedge src_clk);
 end endtask
 task reply_check(input integer n,input [15:0] token);
 reg [7:0] hcrc;reg [15:0] pcrc;
 begin
  hcrc=0;for(integer i=8;i<12;i++)hcrc=crc8(hcrc,rx[i]);
  if(rx[8]!==8'hab||rx[9]!==n||{rx[10],rx[11]}!==token||rx[12]!==hcrc)$fatal(1,"source reply header");
  pcrc=16'hffff;for(integer i=0;i<n;i++)begin
   if(rx[13+i]!==i[7:0])$fatal(1,"source payload %0d",i);
   pcrc=crc16(pcrc,rx[13+i]);
  end
  if({rx[13+n],rx[14+n]}!==pcrc||hf||sf)$fatal(1,"source CRC/fault");
  checks++;
 end endtask
 task source_tests280;
 reg [15:0] prior_token;
 begin
  clear();prefix(8'hd4,0,1,0);transfer(13,0);
  if(hf||sf||source.token||rx[8]!==8'haa||rx[9]!==0)$fatal(1,"empty source");checks++;
  send_record(37);send_record(248);
  prefix(8'hd4,0,1,0);transfer(52,0);reply_check(37,0);
  tx[0]=8'he8;transfer(20,0);check_status(20,8'hd7);
  tx[0]=8'he2;transfer(9,0);check_status(9,8'hf9);
  prefix(8'hd4,0,1,1);transfer(263,0);reply_check(248,1);
  if(source.token!=1||!source.read_seen)$fatal(1,"POP/read coverage");checks++;
  prefix(8'hd5,1,1,3);transfer(8,0);repeat(30)@(negedge src_clk);
  if(hf||sf||source.token!=2||!av||!aa||ag!=1)$fatal(1,"final input commit");checks++;
  // Invalid prefix never consumes a fully read bank. Reset is the only
  // recovery from a protocol fault; no retry of a partially consumed reply.
  for(integer mode=0;mode<9;mode++)begin
   clear();send_record(17);
   if(mode!=4)begin prefix(8'hd4,0,1,0);transfer(32,0);reply_check(17,0);end
   prefix(8'hd4,0,1,1);
   case(mode)
    0:tx[6]^=1;
    1:tx[7]=0;
    2:prefix(8'hd4,1,1,1);
    3:prefix(8'hd4,0,2,1);
    5:prefix(8'hd4,0,1,2);
    8:prefix(8'hd5,0,2,3);
   endcase
   transfer(mode==6?7:mode==8?8:13,mode==7?1:0);
   if(!hf||source.token!=(mode==7?1:0)||av)$fatal(1,"bad prefix mode%0d token%0d",mode,source.token);checks++;
  end
  clear();send_record(17);prefix(8'hd4,0,1,0);transfer(31,0);
  if(!hf||source.read_seen||source.token)$fatal(1,"truncated payload");checks++;
  clear();send_record(17);prefix(8'hd4,0,1,0);transfer(32,1);
  if(!hf||source.read_seen||source.token)$fatal(1,"partial payload bit");checks++;
  clear();send_record(17);send_record(19);prefix(8'hd4,0,1,0);transfer(32,0);
  prefix(8'hd5,0,1,3);transfer(8,0);
  if(!hf||source.token||av)$fatal(1,"early final commit");checks++;
  clear();send_record(17);@(negedge clk);source.token=16'hffff;
  prefix(8'hd4,16'hffff,1,0);transfer(32,0);reply_check(17,16'hffff);
  prefix(8'hd5,16'hffff,1,3);transfer(8,0);
  if(!hf||source.token!=16'hffff||av)$fatal(1,"token overflow");checks++;
  clear();send_record(17);prefix(8'hd4,0,1,0);transfer(32,0);
  stop280=1;repeat(20)@(negedge clk);prior_token=source.token;
  prefix(8'hd5,0,1,3);transfer(8,0);
  if(!hf||!sf||source.token!=prior_token||av||record_ready280||byte_ready280)$fatal(1,"STOP commit");checks++;
 end endtask
