// Reserve boot word port. Already accepted background replies keep their owner.
module gbc_load_bus_mux(input wire clk,reset,lock_bus,
 input wire lv,lw,input wire[22:0]la,input wire[15:0]ld,output wire lr,lp,output wire[15:0]lq,
 input wire bv,bw,input wire[22:0]ba,input wire[15:0]bd,output wire br,bp,output wire[15:0]bq,
 output wire ov,ow,output wire[22:0]oa,output wire[15:0]od,input wire ready,rsp,input wire[15:0]data);
 reg owner=0;
 assign ov=lock_bus?lv:bv;assign ow=lock_bus?lw:bw;assign oa=lock_bus?la:ba;assign od=lock_bus?ld:bd;
 assign lr=lock_bus&&ready;assign br=!lock_bus&&ready;
 assign lp=rsp&&owner;assign bp=rsp&&!owner;assign lq=data;assign bq=data;
 always @(posedge clk)if(reset)owner<=0;else if(ov&&ready)owner<=lock_bus;
endmodule
