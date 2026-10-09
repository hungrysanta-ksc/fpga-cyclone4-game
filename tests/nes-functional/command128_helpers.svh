integer starts128=0,begins128=0;
always @(posedge mem_clk)begin
 if(start)starts128++;
 if(load_begin)begins128++;
 if(!reset && dut.pending && dut.pending_command==8 && dut.pending_header_error==0 && dut.pending_body_error==0)
  if(dut.next_carry8 !== (&dut.check_next[7:0]))$fatal(1,"CARRY128 stale carry");
end
task automatic verified128;
 fresh();open_check();
 for(integer a=0;a<16;a++)begin command(8'h67,a,0);command(8'h68,a,a^8'ha5);end
 command(8'h69,16,0);ck(dut.verified&&!fault,"verified128 fixture");
endtask
