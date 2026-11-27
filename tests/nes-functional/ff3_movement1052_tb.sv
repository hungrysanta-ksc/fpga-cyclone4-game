module ff3_movement1052_tb;
 reg clk=0,reset=1,active=1,cancel=0,returned=0,header=0,retired=0,show=0,query=0;
 reg [3:0] directions=0;
 reg [7:0] data=0,op=0;
 reg [15:0] generation=42;
 reg [4:0] index=0;
 wire [7:0] reply;
 wire offer;
 always #5 clk=!clk;
 nes_display1010 dut(.clk(clk),.reset(reset),.active(active),.cancel(cancel),.first_e9(1'b0),
   .writer(1'b0),.returned(returned),.tile_done(1'b0),.token(32'd0),.generation(generation),
   .header(header),.data(data),.retired(retired),.op(op),.dma(1'b0),.show(show),.query(query),
   .accepted1034(1'b0),.group1034(1'b0),.index(index),.offer_phase(offer),.reply(reply),.directions(directions));
 task tick; @(negedge clk);endtask
 task stamp(input integer t);dut.clock_count=t<<16;endtask
 task read_byte(input integer at,input integer expected);
   index=at;tick();if(reply!==expected[7:0])$fatal(1,"index %d got %h expected %h",at,reply,expected);
 endtask
 initial begin
   repeat(3)tick();reset=0;tick();tick();
   header=1;data=1;tick();header=0;
   stamp(4093);directions=1;tick();
   stamp(4094);returned=1;tick();returned=0;
   stamp(4095);header=1;data=3;tick();header=0;
   stamp(2);show=1;tick();show=0;
   stamp(3);retired=1;op=3;tick();retired=0;
   query=1;tick();query=0;
   read_byte(1,'hd2);read_byte(2,42);read_byte(4,'h31);
   read_byte(5,'hfe);read_byte(6,'hff);read_byte(7,2);read_byte(8,3);
   read_byte(9,'hff);read_byte(10,0);read_byte(11,'hfd);read_byte(12,15);read_byte(15,'h5a);
   header=1;data=1;tick();header=0;read_byte(15,0);
   generation=43;data=3;header=1;tick();header=0;show=1;tick();show=0;
   retired=1;op=3;tick();retired=0;query=1;tick();query=0;
   read_byte(4,'h11);read_byte(15,'h5a);
   cancel=1;repeat(3)tick();read_byte(15,0);cancel=0;tick();tick();
   query=1;tick();query=0;read_byte(15,0);
   $display("PASS1052 movement, final tile, SEAL, show, ACK, generation rollover boundary, no-tile frame and STOP");$finish;
 end
endmodule
