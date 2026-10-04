// Converts lossless 9-bit frame-local color IDs using a scheduled slot map.
// IDs reference an external RGB555 dictionary; they are not reduced RGB colors.
// Palette planning, external SRAM and SNES integration are NOT included.
// A miss aborts the frame; callers must publish buffers only after done.
module indexed_sixplane (
    input wire clk_sys, reset, start,
    input wire pal_we,
    input wire [5:0] pal_slot,
    input wire [8:0] pal_id,
    input wire pixel_valid,
    input wire [8:0] pixel_id,
    output wire pixel_ready,
    output wire [7:0] row,
    output wire [7:0] column,
    output wire write_valid,
    input wire write_ready,
    output wire [14:0] write_addr,
    output wire [15:0] write_data,
    output reg done, error,
    output wire busy,
    input wire[8:0]pal_old_id,input wire pal_initial,input wire[9:0]color_count
);
    localparam IDLE=0, ACCEPT=1, LOOKUP=2, EMIT0=3, EMIT1=4, EMIT2=5, FAILED=6, CLEAR_MAP=7;
    reg [2:0] state;
    // Direct ID->slot table. Pipeline init is canonical slot ID or zero.
    // Two simultaneous writes invalidate the evicted ID and install the new ID.
    wire[6:0]index_q;reg[8:0]clear_index;
    wire replacing=pal_we&&!pal_initial;
    wire clear_old=replacing&&pal_old_id!=pal_id&&pal_old_id!=0;
    gbc_inverse_ram inverse_ram(clk_sys,clear_old?pal_old_id:pixel_id,clear_old,7'h40,index_q,
      state==CLEAR_MAP?clear_index:pal_id,state==CLEAR_MAP||replacing,
      state==CLEAR_MAP?(({1'b0,clear_index}<color_count&&clear_index<64)?{1'b0,clear_index[5:0]}:7'h40):{1'b0,pal_slot});
    reg [7:0] x, y;
    reg [7:0] planes [0:5];
    reg [14:0] block_addr;
    wire found=!index_q[6];wire[5:0]index=index_q[5:0];integer j;
    assign busy=(state!=IDLE && state!=FAILED);
    assign pixel_ready=(state==ACCEPT && !pal_we && !start);
    assign row=y;
    assign column=x;
    assign write_valid=(state==EMIT0 || state==EMIT1 || state==EMIT2);
    assign write_addr=block_addr + (state==EMIT1 ? 15'd5760 : state==EMIT2 ? 15'd11520 : 15'd0);
    assign write_data=state==EMIT0 ? {planes[1],planes[0]} : state==EMIT1 ? {planes[3],planes[2]} : {planes[5],planes[4]};
    always @(posedge clk_sys) begin
        if(reset) begin
            state<=IDLE; clear_index<=0; done<=0; error<=0;
            x<=0; y<=0; block_addr<=0;
            for(j=0;j<6;j=j+1) planes[j]<=0;
        end else begin
            done<=0;
            if(start) begin
                state<=CLEAR_MAP;clear_index<=0; x<=0; y<=0; error<=0;
                for(j=0;j<6;j=j+1) planes[j]<=0;
            end else case(state)
                CLEAR_MAP:begin if(clear_index==511)state<=ACCEPT;else clear_index<=clear_index+1'b1;end
                ACCEPT: if(pixel_valid && pixel_ready)state<=LOOKUP;
                LOOKUP:begin
                    if(!found) begin error<=1; state<=FAILED; end
                    else begin
                        for(j=0;j<6;j=j+1) planes[j]<={planes[j][6:0],index[j]};
                        if(x[2:0]==7) begin
                            // Stream order: plane pair, row within tile, tile index, byte.
                            block_addr<=({12'b0,y[2:0]}*15'd720) + ({10'b0,y[7:3]}*15'd40) + ({10'b0,x[7:3]}*15'd2);
                            state<=EMIT0;
                        end else begin x<=x+1'b1; state<=ACCEPT; end
                    end
                end
                EMIT0: if(write_ready) state<=EMIT1;
                EMIT1: if(write_ready) state<=EMIT2;
                EMIT2: if(write_ready) begin
                    if(x==159) begin
                        x<=0;
                        if(y==143) begin done<=1; state<=IDLE; end
                        else begin y<=y+1'b1; state<=ACCEPT; end
                    end else begin x<=x+1'b1; state<=ACCEPT; end
                end
                default: ;
            endcase
        end
    end
endmodule

