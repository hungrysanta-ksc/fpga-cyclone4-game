// SPDX-License-Identifier: MIT
// Included in the actual SPI bench. Deterministic SEALED query fixture;
// actual selected180 fill and SPI, candidate181 exporter. No live PPU here.
parameter integer PATCHES=0;
reg owned=0,en=1;
wire released,eq,fq,fs,fb,fdone,fok,bv,br,mreq,mabort,quarantine;
wire [2:0] ek,fk;wire [12:0] ei,fi,bt;wire [15:0] eg,fg,bg,mg;
wire [7:0] bd;wire [3:0] bl,fe,ee,estate;wire [1:0] bk;
wire [21:0] ma;reg mr=0;reg [21:0] mra=0;reg [15:0] mrg=0;reg [7:0] md=0;
reg er=0,fr=0;reg [63:0] ed=0,fdq=0;
wire ebusy;wire [9:0] tc;wire [13:0] bc;wire [31:0] fc;
integer exported=0,raw_count=0,chr_count=0,record_fd,lease_ticks=0;
reg chr_ended=0,export_finished=0;
function automatic [63:0] fixture(input [2:0] k,input [12:0] i);
 integer slot;begin
 fixture=0;
 case(k)
 0:fixture=3; // BG tile3; OBJ5 and exception7 are distinct requirements.
 1:fixture=i%8;
 2:fixture=5;
 3:fixture=(64'd7<<19)|(64'd36<<6);
 4:begin
   for(slot=0;slot<PATCHES;slot=slot+1)
    if(i==32+slot*24)fixture=(64'd1<<49)|(64'(slot)<<50);
  end
 5:fixture=i;
 6:fixture=i==3||i==7?1:i==5?2:0;
 7:fixture=(i*3+(i/256)*11+(i%256)/7)&63;
 endcase
 end endfunction
always @(posedge clk)begin
 er<=eq;fr<=fq;
 if(eq)ed<=fixture(ek,ei);
 if(fq)fdq<=fixture(fk,fi);
 mr<=mreq;
 if(mreq)begin mra<=ma;mrg<=mg;md<=((ma[16:4]*17)+ma[3:0]*5)&255;end
 if(!reset)begin
  lease_ticks<=lease_ticks+1;
  if(released)begin owned<=0;export_finished<=1;end
  if(valid&&ready)begin
   $fwrite(record_fd,"%024x\n",data);exported<=exported+1;
   if(data[95:93]==7&&data[76:64]==4)chr_ended<=1;
   if(data[95:93]==6)begin
    if(chr_ended)raw_count<=raw_count+1;else chr_count<=chr_count+1;
   end
   if(data[95:93]==7&&data[76:64]==2)$fatal(1,"unexpected ABORT %x",data);
  end
 end
end
nes_native_export181 #(.MAX_CYCLES(33554432)) exporter(
 .clk(clk),.reset(reset),.enable(en),.frame_owned(owned),.geometry_valid(1'b1),.frame_generation(16'd12),
 .patch_count(3'(PATCHES)),.row_count(8'd224),.object_count(8'd1),.exception_count(8'd1),.group_count(6'd1),.palette_count(6'd1),
 .release_frame(released),.query(eq),.query_kind(ek),.query_index(ei),.query_generation(eg),.response(er),.hit(1'b1),.data(ed),
 .fill_start(fs),.fill_busy(fb),.fill_done(fdone),.fill_success(fok),.fill_error(fe),
 .byte_valid(bv),.byte_ready(br),.byte_data(bd),.byte_tile(bt),.byte_lane(bl),.byte_kind(bk),.byte_generation(bg),
 .tx_valid(valid),.tx_ready(ready),.tx_data(data),.ack_valid(av),.ack_accept(aa),.ack_generation(ag),.ack_ready(ack_ready),
 .observe_state177(estate),.busy(ebusy),.error(ee));
nes_native_fill165 #(.MAX_CYCLES(16777216),.WAIT_CYCLES(131072),.COOPERATIVE_WAIT(1)) fill(
 .clk(clk),.reset(reset),.start(fs),.clear(released),.frame_owned(owned),.geometry_valid(1'b1),.frame_generation(16'd12),
 .query(fq),.query_kind(fk),.query_index(fi),.query_generation(fg),.response(fr),.hit(1'b1),.data(fdq),
 .mem_idle(!mr),.mem_ready(1'b1),.mem_response(mr),.mem_error(1'b0),.mem_response_address(mra),.mem_response_generation(mrg),.mem_data(md),
 .mem_request(mreq),.mem_abort(mabort),.mem_address(ma),.mem_generation(mg),
 .byte_valid(bv),.byte_ready(br),.byte_data(bd),.byte_tile(bt),.byte_lane(bl),.byte_kind(bk),.byte_generation(bg),
 .busy(fb),.done(fdone),.quarantine(quarantine),.success(fok),.error(fe),.tile_count(tc),.byte_count(bc),.cycles(fc));
