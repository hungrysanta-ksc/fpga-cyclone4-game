// SPDX-License-Identifier: MIT
`timescale 1ps/1ps
module bus571_mux_tb;
 reg core_reset,sink_oe204,bus_oe_n,sink_dir204,bus_dir,status_receive;
 reg [7:0] sink_data204,bus_data;
 wire consumer_dir,consumer_oe,SNES_DATABUS_DIR,SNES_DATABUS_OE;
 wire [7:0] consumer_data,SNES_DATA;
@FITTED_MUX@
 bit owner,drive;
 logic [7:0] expected_data;
 initial begin
  for(int pattern=0;pattern<2;pattern++)begin
   sink_data204=pattern?8'h5a:8'ha5;bus_data=~sink_data204;
   for(int code=0;code<64;code++)begin
    {core_reset,sink_oe204,bus_oe_n,sink_dir204,bus_dir,status_receive}=code;
    #10;owner=!core_reset&&(sink_oe204!=bus_oe_n);
    drive=owner&&(sink_oe204?bus_dir:sink_dir204);
    expected_data=drive?(sink_oe204?bus_data:sink_data204):8'hzz;
    if(SNES_DATABUS_OE!==(!owner&&!status_receive)||SNES_DATABUS_DIR!==drive||SNES_DATA!==expected_data)
     $fatal(1,"owner code=%0d",code);
   end
  end
  $display("PASS571 MUX 128");$finish;
 end
endmodule
