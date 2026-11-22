// Passive 84 MHz observer. All inputs have already reached this clock domain.
module nes_display927(input wire clk,reset,active,first_e9,writer,begin_frame,
    seal,dma,show,ack,query,input wire [1:0] port_code,
    input wire [15:0] generation,input wire [4:0] index,output reg [7:0] reply);
    reg [24:0] timer;
    reg old_writer,tile_valid,tile_epoch,live,sealed,shown,pre,post,multiple,done,bad;
    reg [15:0] ack_gen;
    reg final_tile;
    reg [1:0] first_port,last_port,pre_port;
    wire publish=tile_epoch && writer!=old_writer;
    wire head=live && !sealed && seal;
    wire beat=live && !shown && dma;
    wire reveal=live && sealed && !shown && show;
    wire finish=live && ack;
    // In a one-beat upload the decoder uses the first stamp for both ends.
    // Slot 7 records the first pre-SEAL destination beat.
    reg [15:0] previous_show,qshow;
    reg pre_multiple;
    reg [2:0] addr;
    always @* begin
        if(query) addr=6;
        else if(finish) addr=5;
        else if(reveal) addr=4;
        else if(head) addr=1;
        else if(beat && sealed) addr=post ? 3 : 2;
        else if(beat) addr=pre ? 3 : 7;
        else addr=0;
    end
    wire store=query || finish || reveal || head || beat || publish;
    (* ramstyle="M9K" *) reg [15:0] stamps[0:7];
    reg [15:0] q;
    wire [4:0] offset=index-5'd8;
    always @(posedge clk) begin
        q<=stamps[offset[3:1]];
        if(active && !reset && store) stamps[addr]<=timer[24:9];
        if(reset || !active) begin
            timer<=0;old_writer<=writer;tile_valid<=0;tile_epoch<=0;live<=0;
            sealed<=0;shown<=0;pre<=0;post<=0;multiple<=0;done<=0;bad<=0;
            first_port<=0;last_port<=0;pre_port<=0;previous_show<=0;ack_gen<=0;final_tile<=0;pre_multiple<=0;
        end else begin
            timer<=timer+1'b1;old_writer<=writer;
            if(first_e9) begin tile_valid<=0;tile_epoch<=1;end
            if(publish) tile_valid<=1;
            if(begin_frame) begin
                live<=1;done<=0;sealed<=0;pre<=0;post<=0;multiple<=0;bad<=0;pre_multiple<=0;
                if(shown) previous_show<=qshow;
                shown<=0;
            end
            if(head) sealed<=1;
            if(beat && !sealed && !pre) begin pre<=1;pre_port<=port_code;end
            if(beat && !sealed && pre) begin pre_multiple<=1;last_port<=port_code;end
            if(beat && sealed) begin
                if(!post) first_port<=port_code;
                else multiple<=1;
                last_port<=port_code;post<=1;
            end
            if(reveal) shown<=1;
            if(finish) begin ack_gen<=generation;done<=1;live<=0;tile_epoch<=0;
                final_tile<=tile_valid;tile_valid<=0;end
            if((publish && (query||finish||reveal||head||beat)) ||
               (query && (finish||reveal||head||beat)) ||
               (finish && (reveal||head||beat)) || (reveal && (beat||head)) ||
               (head && beat)) bad<=1;
        end
    end
    always @(posedge clk) if(reveal) qshow<=timer[24:9];
    always @(posedge clk) case(index)
        1:reply<=8'h97;
        2:reply<=ack_gen[7:0];3:reply<=ack_gen[15:8];
        4:reply<={bad,done,shown,multiple,post,pre,sealed,final_tile};
        5:reply<={1'b0,pre_multiple,pre_port,last_port,first_port};
        6:reply<=previous_show[7:0];7:reply<=previous_show[15:8];
        default:reply<=offset[0]?q[15:8]:q[7:0];
    endcase
endmodule
