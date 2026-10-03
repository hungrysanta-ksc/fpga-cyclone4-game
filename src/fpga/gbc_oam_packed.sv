module gbc_oam_packed(input wire clk,input wire[6:0]addr_a,addr_b,
 input wire we_a,lane_a,input wire[7:0]data_a,
 input wire we_b,lane_b,input wire[7:0]data_b,output wire[15:0]q_a,q_b);
 altsyncram #(.operation_mode("BIDIR_DUAL_PORT"),.intended_device_family("Cyclone IV E"),
 .width_a(16),.width_b(16),.widthad_a(7),.widthad_b(7),.numwords_a(128),.numwords_b(128),
 .width_byteena_a(2),.width_byteena_b(2),.byte_size(8),
 .address_reg_b("CLOCK1"),.indata_reg_b("CLOCK1"),.wrcontrol_wraddress_reg_b("CLOCK1"),.byteena_reg_b("CLOCK1"),
 .outdata_reg_a("UNREGISTERED"),.outdata_reg_b("UNREGISTERED"),.power_up_uninitialized("FALSE"),
 .read_during_write_mode_port_a("NEW_DATA_WITH_NBE_READ"),.read_during_write_mode_port_b("NEW_DATA_WITH_NBE_READ")) mem(
 .clock0(clk),.clock1(clk),.clocken0(1'b1),.clocken1(1'b1),.aclr0(1'b0),.aclr1(1'b0),
 .address_a(addr_a),.address_b(addr_b),.wren_a(we_a),.wren_b(we_b),
 .byteena_a(lane_a?2'b10:2'b01),.byteena_b(lane_b?2'b10:2'b01),
 .data_a({data_a,data_a}),.data_b({data_b,data_b}),.rden_a(1'b1),.rden_b(1'b1),.q_a(q_a),.q_b(q_b));
endmodule
