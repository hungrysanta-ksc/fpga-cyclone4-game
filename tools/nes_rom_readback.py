# SPDX-License-Identifier: MIT
"""058 experiment: share the existing reader FSM with a memory-clock CHECK port.

No SPI opcode, MCU implementation, integrity verdict or automatic RUN gate yet.
Frozen052/053/054/057 sources are never edited.
"""
from nes_rom_geometry import ROOT, materialize as geometry, replace
from nes_spi_boot import put, sha

PORTS = ''' input wire check_enable,check_request,input wire [16:0] check_address,
 output wire check_ready,check_response,output wire [16:0] check_response_address,
 output wire [7:0] check_data,output wire check_fault,
'''
CONNECT = '''.check_enable(check_enable),.check_request(check_request),.check_address(check_address),
 .check_ready(check_ready),.check_response(check_response),.check_response_address(check_response_address),
 .check_data(check_data),.check_fault(check_fault),'''


def materialize(out):
    geometry(out)
    original = ROOT / 'src/nes/nes_rom_physical.sv'
    assert sha(original) == '8a0fb832b318730201beaa5971496d696b8aa795dafb099d5d1a66230944562e'
    s = original.read_text()
    s = replace(s, ' input wire clk,mem_clk,reset,', ''' input wire clk,mem_clk,reset,
 input wire check_mode,check_request,input wire [21:0] check_address,
 output wire check_ready,output reg check_response,
 output wire [21:0] check_response_address,output wire [7:0] check_data,''')
    s = replace(s, ' wire reading=!mr && remaining!=0;', ''' wire reading=!mr && remaining!=0;
 assign check_ready=!mr && check_mode && remaining==0;
 // Reuse the controller address/chip/lane and held data; no second tag RAM.
 assign check_response_address={psram_address[19:0],chip,lane};
 assign check_data=data_hold;
 wire pending=check_mode ? check_request : request_sync[1]!=ack_toggle;
 wire [21:0] selected_address=check_mode ? check_address : address_hold;''')
    s = s.replace('remaining<=0;ack_toggle<=0;data_hold<=0;',
                  'remaining<=0;ack_toggle<=0;data_hold<=0;check_response<=0;')
    s = replace(s, '  else if(remaining!=0)begin', '''  else begin
   check_response<=0;
   if(remaining!=0)begin''')
    s = replace(s, '    ack_toggle<=request_sync[1];',
                  '    if(check_mode)check_response<=1;else ack_toggle<=request_sync[1];')
    s = replace(s, '  end else if(request_sync[1]!=ack_toggle)begin', '  end else if(pending)begin')
    s = replace(s, 'psram_address<={2\'b0,address_hold[21:2]};chip<=address_hold[1];lane<=address_hold[0];',
                  "psram_address<={2'b0,selected_address[21:2]};chip<=selected_address[1];lane<=selected_address[0];")
    s = replace(s, ' end\nendmodule', '  end\n end\nendmodule')
    put(out / original.name, s)

    s = (out / 'nes_rom_boot.sv').read_text()
    s = replace(s, ' input wire load_begin,', PORTS + ' input wire load_begin,')
    s = replace(s, ' wire [21:0] load_address,read_address;', ''' reg check_failed;
 wire loader_run;
 wire check_active=check_enable && loaded && !loader_run && !boot_fault && !check_failed;
 wire reader_owner=run_enable || check_active;
 wire reader_reset=reset || check_failed || (!check_active && (read_reset || !run_enable));
 wire raw_check_ready,raw_check_response;
 wire [21:0] raw_check_address;
 wire address_valid=check_address < (rom_chr32 ? 17'h18000 : 17'h14000);
 wire [21:0] physical_check_address=check_address[16] ?
     {1'b1,5'b0,check_address[15:0]} : {6'b0,check_address[15:0]};
 assign check_fault=check_failed;
 assign run_enable=loader_run && !check_failed;
 assign check_ready=check_active && raw_check_ready;
 assign check_response=check_active && raw_check_response;
 assign check_response_address={raw_check_address[21],raw_check_address[15:0]};
 always @(posedge mem_clk or posedge reset)
  if(reset)check_failed<=0;
  else if((check_enable && (loader_run || !loaded || boot_fault || load_begin || load_valid || load_end || start)) ||
          (check_request && (!check_ready || !address_valid)))check_failed<=1;
 wire [21:0] load_address,read_address;''')
    s = replace(s, '.load_begin(load_begin)', '.load_begin(load_begin && !check_enable && !check_failed)')
    s = replace(s, '.load_valid(load_valid)', '.load_valid(load_valid && !check_enable && !check_failed)')
    s = replace(s, '.load_end(load_end)', '.load_end(load_end && !check_enable && !check_failed)')
    s = replace(s, '.start(start)', '.start(start && !check_enable && !check_failed)')
    s = replace(s, '.run_enable(run_enable)', '.run_enable(loader_run)')
    s = replace(s, '.reset(reset || read_reset || !run_enable)', '''.reset(reader_reset),
 .check_mode(check_active),.check_request(check_request && check_ready && address_valid),
 .check_address(physical_check_address),.check_ready(raw_check_ready),.check_response(raw_check_response),
 .check_response_address(raw_check_address),.check_data(check_data)''')
    s = replace(s, '.rom_request(rom_request)', '.rom_request(rom_request && run_enable)')
    s = s.replace('run_enable?read_', 'reader_owner?read_')
    s = replace(s, '!reset && !run_enable && load_drive', '!reset && !reader_owner && load_drive')
    put(out / 'nes_rom_boot.sv', s)
    s = (out / 'nes_spi_boot.sv').read_text()
    s = replace(s, ' input wire SPI_SS,', PORTS + ' input wire SPI_SS,')
    s = replace(s, 'nes_rom_boot boot(', 'nes_rom_boot boot(' + CONNECT)
    # SPI fault must also close the CHECK ownership, not just exported RUN.
    s = replace(s, '.check_enable(check_enable)', '.check_enable(check_enable && !spi_fault)')
    put(out / 'nes_spi_boot.sv', s)
