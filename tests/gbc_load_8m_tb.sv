// Feed the production 512-byte duplex engine back-to-back blocks. Compare
// each returned word against the original file, including the final D2.
module gbc_load_8m_tb;
  bit clk, reset, run, cmd_ready, ending, rx_valid, take;
  logic [7:0] cmd;
  logic [31:0] count;
  logic [15:0] rx, returned;
  wire mode, primed, lock_bus, inhibit, req, wr;
  wire [7:0] status;
  wire [22:0] addr;
  wire [15:0] data;
  logic response;
  logic [15:0] read_data;
  byte unsigned image[0:8388607];
  reg [15:0] memory[0:4194303];
  integer writes, reads, fd, n;
  string path;
  always #1 clk = !clk;
  always @(posedge clk) begin
    response <= req;
    if (req) begin
      if (wr) begin
        if (addr !== writes || data !== {image[2*writes+1], image[2*writes]})
          $fatal(1, "write address/data %d", writes);
        memory[addr] <= data;
        writes <= writes + 1;
      end else begin
        if (addr !== reads) $fatal(1, "read alias at %d", reads);
        read_data <= memory[addr];
        reads <= reads + 1;
      end
    end
  end
  gbc_load_duplex dut(clk,reset,run,cmd_ready,cmd,ending,count,rx_valid,rx,take,
                      returned,mode,primed,lock_bus,inhibit,status,req,wr,
                      addr,data,1'b1,response,read_data);
  task command(input byte opcode);
    cmd=opcode; cmd_ready=1; @(negedge clk); cmd_ready=0; @(negedge clk);
  endtask
  task reset_session;
    reset=1; @(negedge clk); @(negedge clk); reset=0;
    command(8'hd0);
    if (!lock_bus || !inhibit) $fatal(1,"session admission");
  endtask
  task block(input integer b, input bit final_read);
    integer p;
    command(final_read ? 8'hd2 : 8'hd1);
    while (!primed) @(negedge clk);
    for (integer i=0;i<256;i++) begin
      p=b*512+i*2;
      if (!final_read) rx={image[p+1],image[p]};
      if (b && returned !== {image[p-511],image[p-512]}) $fatal(1,"readback %d:%d",b,i);
      rx_valid=1; take=1; @(negedge clk); rx_valid=0; take=0;
      repeat(7) @(negedge clk);
    end
    count=514; ending=1; @(negedge clk); ending=0;
    while(status==8'hc2) @(negedge clk);
    if(status!==8'hc0 || inhibit==final_read) $fatal(1,"block completion %d",b);
  endtask
  initial begin
    if (!$value$plusargs("ROM=%s",path)) $fatal(1,"missing ROM");
    fd=$fopen(path,"rb");
    n=$fread(image,fd);
    if(n!=8388608 || $fgetc(fd)!=-1) $fatal(1,"input size");
    $fclose(fd);
    writes=0; reads=0;
    @(negedge clk); reset_session();
    for(integer b=0;b<16384;b++) block(b,0);
    block(16384,1);
    if(reads!=4194304 || writes!=reads) $fatal(1,"transfer counts");
    command(8'hd1);
    if (!inhibit || status!==8'hc1) $fatal(1,"post-final write accepted");
    reset_session(); command(8'hd2);
    if (!inhibit || status!==8'hc1) $fatal(1,"empty read accepted");
    reset_session(); command(8'hd1);
    count=112; ending=1; @(negedge clk); ending=0; repeat(3) @(negedge clk);
    if (!inhibit || !status[0]) $fatal(1,"short write accepted");
    $display("PASS 8 MiB 16384 blocks, 4194304 writes/reads, final and partial guards");
    $finish;
  end
  initial begin repeat(40000000) @(posedge clk); $fatal(1,"timeout"); end
endmodule
