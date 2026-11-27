// Compare each CPU file word and the external execution bus against FF3 1040.
`timescale 1ns/1ps
module ff3_cpu1041_tb;
  bit clk, power, reset_n, enable_cpu, ready_cpu, irq_n, nmi_n, so_n;
  bit load, write_word, bus_reset;
  bit [9:0] address;
  bit [63:0] word_in;
  bit [7:0] data_in;
  wire [63:0] got, expected;
  wire [32:0] bus_a, bus_b;
  int cycles, writes, seed=1041;
  bit [255:0] opcodes;
  `define INPUTS .Mode(2'b0),.BCD_en(1'b0),.Res_n(reset_n),.Pwr_n(power),.Enable(enable_cpu),.Clk(clk),.Rdy(ready_cpu),.Abort_n(1'b1),.SO_n(so_n),.IRQ_n(irq_n),.NMI_n(nmi_n),.DI(data_in),.SaveStateBus_Din(word_in),.SaveStateBus_Adr(address),.SaveStateBus_wren(write_word),.SaveStateBus_rst(bus_reset),.SaveStateBus_load(load)
  T65 dut(`INPUTS,.A(bus_a[32:9]),.DO(bus_a[8:1]),.R_W_n(bus_a[0]),.SaveStateBus_Dout(got));
  T65_ref baseline(`INPUTS,.A(bus_b[32:9]),.DO(bus_b[8:1]),.R_W_n(bus_b[0]),.SaveStateBus_Dout(expected));
  `undef INPUTS
  task automatic tick;
    bit [9:0] write_address;
    write_address=address;
    #2;clk=1;#2;
    for(int word=0;word<4;word++)begin
      address=word;#1;
      if(got!==expected || bus_a!==bus_b)
        $fatal(1,"cycle %d write=%d read=%d data=%h/%h bus=%h/%h",cycles,write_address,word,got,expected,bus_a,bus_b);
      if(word==0 && enable_cpu && !load && power) opcodes[expected[23:16]]=1;
    end
    address=write_address;clk=0;#2;cycles++;
  endtask
  initial begin
    void'($urandom(seed));
    repeat(4)tick();
    for(int round=0;round<512;round++)begin
      power=1;reset_n=1;load=1;write_word=1;bus_reset=0;
      for(int slot=0;slot<3;slot++)begin
        address=slot;word_in={$urandom(),$urandom()};
        if(slot==0)begin
          word_in[58:55]=$urandom_range(11);
          word_in[54:51]=$urandom_range(11);
          word_in[49:48]=0;
          word_in[23:16]=round[7:0];
        end
        tick();writes++;
      end
      write_word=0;load=0;
      for(int step=0;step<80;step++)begin
        enable_cpu=$urandom_range(7)!=0;ready_cpu=$urandom_range(3)!=0;
        irq_n=$urandom_range(5)!=0;nmi_n=$urandom_range(11)!=0;so_n=1;
        data_in=$urandom();tick();
      end
      power=0;reset_n=0;bus_reset=1;tick();
    end
    $display("PASS paired T65 cycles=%0d restored_words=%0d observed_opcodes=%0d",cycles,writes,$countones(opcodes));
    $finish;
  end
endmodule
