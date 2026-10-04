module gbc_inverse_ram(input wire clk,input wire[8:0]addr_a,input wire we_a,input wire[6:0]data_a,output wire[6:0]q_a,
 input wire[8:0]addr_b,input wire we_b,input wire[6:0]data_b);
 altsyncram #(.operation_mode("BIDIR_DUAL_PORT"),.intended_device_family("Cyclone IV E"),
 .width_a(7),.width_b(7),.widthad_a(9),.widthad_b(9),.numwords_a(512),.numwords_b(512),
 .width_byteena_a(1),.width_byteena_b(1),.address_reg_b("CLOCK1"),.indata_reg_b("CLOCK1"),.wrcontrol_wraddress_reg_b("CLOCK1"),
 .outdata_reg_a("UNREGISTERED"),.outdata_reg_b("UNREGISTERED"),.power_up_uninitialized("FALSE"),
 .read_during_write_mode_port_a("NEW_DATA_NO_NBE_READ"),.read_during_write_mode_port_b("NEW_DATA_NO_NBE_READ")) mem(
 .clock0(clk),.clock1(clk),.clocken0(1'b1),.clocken1(1'b1),.aclr0(1'b0),.aclr1(1'b0),
 .address_a(addr_a),.address_b(addr_b),.wren_a(we_a),.wren_b(we_b),.byteena_a(1'b1),.byteena_b(1'b1),
 .data_a(data_a),.data_b(data_b),.rden_a(1'b1),.rden_b(1'b1),.q_a(q_a));
endmodule
