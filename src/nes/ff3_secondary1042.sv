// Fragment inside the FF3 OAMEval. A PPU enable is issued every fourth
// master clock. Commit both byte writes on the following falling edge;
// idle falling edges sample the read addresses for the next PPU enable.
reg write_load,write_copy;
reg [4:0] load_addr,copy_addr;
reg [7:0] load_data,copy_data;
always @(posedge clk) begin
 write_load<=!reset && temp_load;
 write_copy<=!reset && oam_copy_write && !(temp_load && oam_secondary_addr==oam_row_cur);
 if(temp_load)begin load_addr<=oam_secondary_addr;load_data<=oam_dbus;end
 if(oam_copy_write)begin
  copy_addr<=oam_row_cur;
  copy_data<=temp_copy_data;
 end
end
`ifndef SYNTHESIS
always @(posedge clk) if(!reset && ce && (write_load || write_copy))
 $fatal(1,"FF3 secondary OAM requires an idle master clock after a write");
`endif
altsyncram #(.operation_mode("BIDIR_DUAL_PORT"),.intended_device_family("Cyclone IV E"),
 .ram_block_type("M9K"),.width_a(8),.width_b(8),.widthad_a(5),.widthad_b(5),
 .numwords_a(32),.numwords_b(32),.width_byteena_a(1),.width_byteena_b(1),
 .address_reg_b("CLOCK0"),.indata_reg_b("CLOCK0"),.wrcontrol_wraddress_reg_b("CLOCK0"),
 .outdata_reg_a("UNREGISTERED"),.outdata_reg_b("UNREGISTERED"),
 .read_during_write_mode_mixed_ports("DONT_CARE")) secondary_ram(
 .clock0(~clk),.clock1(1'b1),.clocken0(1'b1),.clocken1(1'b1),.clocken2(1'b1),.clocken3(1'b1),
 .aclr0(1'b0),.aclr1(1'b0),.addressstall_a(1'b0),.addressstall_b(1'b0),
 .address_a(write_load?load_addr:oam_secondary_addr),.data_a(load_data),.wren_a(write_load && !reset),
 .address_b(write_copy?copy_addr:oam_row_last),.data_b(copy_data),.wren_b(write_copy && !reset),
 .byteena_a(1'b1),.byteena_b(1'b1),.rden_a(1'b1),.rden_b(1'b1),.q_a(secondary_q),.q_b(copy_q),.eccstatus());
