// SPDX-License-Identifier: MIT
integer cancel129=0,stopclock129=0;
task automatic ready_image129;
 fresh();dut.loader.state=4;dut.loader.loaded_bytes=81920;dut.loader.chr32=0;
endtask
always @(negedge mem_clk)if(!reset && !dut.reader.mr)begin
 if(dut.reader.owner_valid)ck(dut.reader.owner_check===dut.check_active,"OWNER129 captured mode");
 if(check_ready || !psram_oe)ck(dut.reader.owner_valid,"OWNER129 ready requires capture");
 if(check_response)ck(dut.reader.owner_valid&&dut.reader.owner_check,"OWNER129 CHECK response owner");
end
