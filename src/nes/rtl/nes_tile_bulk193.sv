// SPDX-License-Identifier: MIT
// Completed SNES-planar tiles -> immutable dual-clock RAM -> section chunks.
// Descriptors are host-domain ports, not yet mapped to the SNES control bus.
// end_sealed means all tile chunks published, NOT consumed/displayed/COMMIT.
module nes_tile_bulk193(
 input wire nes_clk,host_clk,reset,active,stop,source_fault,
 input wire tile_valid,output wire tile_ready,input wire [7:0] tile_data,
 input wire [4:0] tile_index,input wire [5:0] tile_length,input wire [1:0] tile_kind,
 input wire [9:0] tile_slot,input wire [15:0] tile_generation,
 input wire end_valid,output wire end_ready,input wire [15:0] end_generation,
 input wire [31:0] token_seed,
 output wire chunk_ready,output wire [11:0] chunk_length,output wire [31:0] chunk_token,
 output wire chunk_kind,output wire [9:0] chunk_slot,output wire [15:0] chunk_generation,
 input wire consume,input wire [31:0] consume_token,output wire consume_error,
 input wire [23:0] address,input wire read_n,write_n,
 output wire [7:0] data_out,output wire oe_n,dir,
 output wire fault,output reg end_sealed,output reg [15:0] sealed_generation
);
 wire common_reset=reset||stop||!active||source_fault;
 wire sr,hr;
 nes_domain_reset124 src_release(.clk(nes_clk),.raw_reset(common_reset),.reset(sr));
 nes_domain_reset124 dst_release(.clk(host_clk),.raw_reset(common_reset),.reset(hr));
 reg source_failed,host_failed,sending,ending;
 (* ramstyle="M9K, no_rw_check" *) reg [7:0] tile_store[0:31];
 reg [7:0] read_data; // Payload is never reset; ownership protects both ports.
 reg skind;reg [15:0] sgen;reg [9:0] sslot;reg [5:0] slength;
 reg [4:0] next_index;
 wire cancel=common_reset||source_fault||source_failed||host_failed;
 assign fault=source_fault||source_failed||host_failed;
 wire box_ready,word_valid,word_ready;wire [33:0] word_data;
 nes_native_mailbox165 #(.WIDTH(34)) tiles(
  .src_clk(nes_clk),.dst_clk(host_clk),.reset(cancel),
  .src_valid(sending&&!cancel),.src_ready(box_ready),.src_data({ending,skind,sgen,sslot,slength}),
  .dst_valid(word_valid),.dst_ready(word_ready),.dst_data(word_data));
 // Do not overwrite the RAM until host consumed the ENTIRE prior tile and
 // its ACK returned through the mailbox synchronizer.
 assign tile_ready=!sr&&!cancel&&!sending&&box_ready;
 assign end_ready=tile_ready&&next_index==0&&!tile_valid;
 wire input_ok=tile_kind<3&&tile_length==(tile_kind==1?32:16)&&
  (tile_kind!=1||tile_slot<128)&&(tile_kind!=2||tile_slot==0);
 always @(posedge nes_clk)if(tile_valid&&tile_ready&&input_ok&&tile_index==next_index)
  tile_store[tile_index]<=tile_data;
 always @(posedge nes_clk or posedge sr)begin
  if(sr)begin source_failed<=0;sending<=0;ending<=0;skind<=0;sgen<=0;sslot<=0;slength<=0;next_index<=0;end
  else if(!cancel)begin
   if(sending&&box_ready)sending<=0;
   if(tile_valid&&tile_ready)begin
    if(!input_ok||tile_index!=next_index||
       (next_index!=0&&(skind!=(tile_kind==1)||sgen!=tile_generation||sslot!=tile_slot||slength!=tile_length)))source_failed<=1;
    else begin
     if(next_index==0)begin
      skind<=tile_kind==1;sgen<=tile_generation;sslot<=tile_slot;slength<=tile_length;ending<=0;
     end
     if(tile_index==tile_length-1)begin next_index<=0;sending<=1;end
     else next_index<=next_index+1'b1;
    end
   end else if(end_valid&&end_ready)begin ending<=1;sgen<=end_generation;sending<=1;end
  end
 end
 wire wend=word_data[33],wkind=word_data[32];
 wire [15:0] wgen=word_data[31:16];wire [9:0] wslot=word_data[15:6];wire [5:0] wlength=word_data[5:0];
 localparam INIT=0,CHECK=1,OPEN=2,WRITE=3,SEAL=4,READ=5;
 reg [2:0] state;reg opened,in_frame,writer,reader;
 reg [11:0] used;reg [4:0] at;reg [31:0] token;
 reg [15:0] frame_gen;reg section_kind;reg [10:0] next_slot;
 reg [26:0] descriptors[0:1]; // generation16,kind1,first slot10; length lives in188.
 wire begin_ready,put_ready,producer_error;
 wire append_ok=wkind==section_kind&&{1'b0,wslot}==next_slot&&used+{6'd0,wlength}<=2048;
 wire valid_word=wlength==(wkind?32:16)&&(!wkind||wslot<128);
 always @(posedge host_clk)read_data<=tile_store[at];
 assign word_ready=!cancel&&word_valid&&((state==WRITE&&put_ready&&at==wlength-1)||
                    (state==CHECK&&wend&&!opened&&in_frame&&wgen==frame_gen));
 assign {chunk_generation,chunk_kind,chunk_slot}=chunk_ready?descriptors[reader]:27'd0;
 nes_bulk_aperture188 #(.ALLOW_SHORT_SEAL(1)) aperture(
  .clk(host_clk),.reset(reset),.active(active),.stop(stop||fault),
  .begin_valid(state==OPEN&&!cancel&&token!=32'hffffffff),.begin_length(12'd2048),.begin_token(token),.begin_ready(begin_ready),
  .byte_valid(state==WRITE&&!cancel),.byte_data(read_data),.byte_ready(put_ready),
  .seal(state==SEAL&&!cancel),.cancel(1'b0),.producer_error(producer_error),
  .chunk_ready(chunk_ready),.chunk_length(chunk_length),.chunk_token(chunk_token),
  .consume(consume),.consume_token(consume_token),.consume_error(consume_error),
  .address(address),.read_n(read_n),.write_n(write_n),.data_out(data_out),.oe_n(oe_n),.dir(dir));
 always @(posedge host_clk or posedge hr)begin
  if(hr)begin
   host_failed<=0;state<=INIT;opened<=0;in_frame<=0;writer<=0;reader<=0;used<=0;at<=0;token<=0;
   frame_gen<=0;section_kind<=0;next_slot<=0;descriptors[0]<=0;descriptors[1]<=0;end_sealed<=0;sealed_generation<=0;
  end else begin
   end_sealed<=0;
   if(producer_error)host_failed<=1;
   if(!cancel)begin
    if(consume&&chunk_ready&&consume_token==chunk_token)reader<=!reader;
    case(state)
     INIT:begin token<=token_seed;state<=CHECK;end
     CHECK:if(word_valid)begin
      if((in_frame&&wgen!=frame_gen)||(wend&&!in_frame)||(!wend&&!valid_word))host_failed<=1;
      else if(wend)begin
       if(opened)state<=SEAL;
       else begin end_sealed<=1;sealed_generation<=frame_gen;in_frame<=0;end
      end else if(opened&&!append_ok)state<=SEAL;
      else if(!opened)state<=OPEN;
      else begin at<=0;state<=READ;end
     end
     OPEN:if(token==32'hffffffff)host_failed<=1;
          else if(begin_ready)begin
           descriptors[writer]<={wgen,wkind,wslot};frame_gen<=wgen;in_frame<=1;
           section_kind<=wkind;next_slot<={1'b0,wslot};used<=0;at<=0;opened<=1;state<=READ;
          end
     READ:state<=WRITE;
     WRITE:if(put_ready)begin
      if(at==wlength-1)begin used<=used+{6'd0,wlength};next_slot<={1'b0,wslot}+11'd1;state<=CHECK;end
      else begin at<=at+1'b1;state<=READ;end
     end
     SEAL:begin opened<=0;used<=0;writer<=!writer;token<=token+1'b1;state<=CHECK;end
    endcase
   end
  end
 end
endmodule
