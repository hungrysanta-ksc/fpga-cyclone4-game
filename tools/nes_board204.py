# SPDX-License-Identifier: MIT
"""Actual selected board binding for203 ingress/201 lease/192 source/195 SNES.

No installation or clock/timing waiver. Copy only pinned inputs, not old DBs.
"""
from pathlib import Path
import argparse,json
from nes_metadata203 import ROOT,BASE,sha,replace
from nes_board181 import copy_pins

RTL=['nes_source_epoch204.sv','nes_direct204.sv','nes_source_tile192.sv','nes_chr_cache192.sv',
 'nes_tile191.sv','nes_plan_spi200.sv','nes_plan_batch201.sv','nes_capture_lease201.sv',
 'nes_tile_bulk193.sv','nes_bulk_aperture188.sv','nes_bulk_control194.sv']
VIDEO=['nes_native_frame201.sv','nes_native_capture201.sv']

def prepare(out):
 prior=BASE/'probes/nes-window184-coupled/evidence/route02'
 pins=json.loads((prior/'preparation.json').read_bytes())['sources'];copy_pins(prior,out,pins)
 public={};added=[]
 for folder,names in [('rtl',RTL),('video',VIDEO)]:
  for n in names:
   f=ROOT/'src/nes'/folder/n;public[f.relative_to(ROOT).as_posix()]=sha(f);(out/n).write_bytes(f.read_bytes());added.append(n)
 meta=BASE/'probes/nes-metadata203/test04'
 h=json.loads((meta/'preparation203.json').read_bytes())['generated']['nes_native_export203.sv']
 assert sha(meta/'nes_native_export203.sv')==h
 (out/'nes_native_export203.sv').write_bytes((meta/'nes_native_export203.sv').read_bytes());added.append('nes_native_export203.sv')
 client=BASE/'probes/nes-bulk195/coupled03/candidate/client'
 assert len((client/'body.bin').read_bytes())==3935
 assert len((client/'sink-program.hex').read_text().split())==4096
 (out/'sink-program.hex').write_bytes((client/'sink-program.hex').read_bytes())
 # The epoch is sourced by the actual memory-clock command/loader outputs.
 f=out/'nes_spi_boot.sv';s=f.read_text()
 s=replace(s,' output wire rom_chr32,',' output wire rom_chr32,\n output wire source_ready204,source_rom204,source_write204,output wire [31:0] source_epoch204,')
 s=replace(s,'endmodule',''' nes_source_epoch204 content_lifetime(.mem_clk(mem_clk),.nes_clk(clk),.reset(reset),
 .load_begin(load_begin),.load_valid(load_valid),.loaded(internal_loaded),.run_enable(run_enable),
 .loader_fault(boot_fault||spi_fault),.loaded_bytes(loaded_bytes),
 .source_ready(source_ready204),.source_is_rom(source_rom204),.source_writing(source_write204),.live_epoch(source_epoch204));
endmodule''');f.write_text(s,encoding='utf8',newline='\n')
 f=out/'nes_live_joint.sv';s=f.read_text()
 s=replace(s,'output wire out_native_spi_fault,','output wire out_native_spi_fault,\ninput wire ext_sink_fault,')
 start=s.index('wire native_fill_start');end=s.index('wire native_boot_miso',start)
 s=s[:start]+'''wire native_fill_slot,native_core_safe;
wire native_mem_ready,native_mem_request,native_mem_response,native_mem_error;
wire [21:0] native_mem_address,native_mem_response_address;wire [7:0] native_mem_data;
wire native_frame_response,native_frame_hit;wire [63:0] native_frame_data;
wire native_frame_query=native_query;
wire [2:0] native_frame_query_kind=native_query_kind;
wire [12:0] native_frame_query_index=native_query_index;
wire [15:0] native_frame_query_generation=native_query_generation;
assign native_response=native_frame_response;assign native_hit=native_frame_hit;
assign native_data=native_hit?native_frame_data:64'd0;
wire source_ready204,source_rom204,source_write204;wire [31:0] source_epoch204;
wire lease204,lease_fault204,export_release204,export_permitted204,retire_permitted204,retire_commit204,reader_drained204;
wire [15:0] captured_gen204,retire_gen204;wire [31:0] captured_epoch204;
wire [3:0] native_export_error;
wire direct_miso204,direct_selected204,direct_fault204,direct_nes_fault204;
wire native_spi_miso,native_spi_selected,native_spi_fault;
'''+s[end:]
 s=replace(s,' assign bus_data=0;assign databus_oe_n=1;assign databus_dir=0;','')
 s=replace(s,'nes_spi_boot loader_boot(','''nes_spi_boot loader_boot(.source_ready204(source_ready204),.source_rom204(source_rom204),
 .source_write204(source_write204),.source_epoch204(source_epoch204),''')
 s=replace(s,'nes_native_frame181 native_frame(','''nes_native_capture201 native_frame(
 .capture_begin(),.source_ready(source_ready204),.source_is_rom(source_rom204),.source_writing(source_write204),.live_epoch(source_epoch204),
 .export_error(native_export_error),.reader_drained(reader_drained204),.retire_commit(retire_commit204),.retire_generation(retire_gen204),
 .effective_release(native_release_frame),.lease_valid(lease204),.retire_permitted(retire_permitted204),.export_permitted(export_permitted204),.waiting_display(),.lease_fault(lease_fault204),
 .captured_epoch(captured_epoch204),.captured_generation(captured_gen204),''')
 start=s.index('nes_native_capture201 native_frame(');end=s.index('nes_native_fill165 #',start)
 s=s[:start]+replace(s[start:end],'.release_frame(native_release_frame)', '.release_frame(export_release204)')+s[end:]
 start=s.index('nes_native_fill165 #');end=s.index('assign native_nt_address=',start)
 s=s[:start]+'''nes_direct204 direct_path(.nes_clk(clk),.host_clk(host_clk),.reset(reset),.transport_fault(native_spi_fault||ext_sink_fault),
 .lease_valid(lease204),.lease_fault(lease_fault204),.retire_permitted(retire_permitted204),
 .captured_generation(captured_gen204),.captured_epoch(captured_epoch204),.live_epoch(source_epoch204),
 .source_ready(source_ready204),.source_is_rom(source_rom204),.source_writing(source_write204),
 .reader_drained(reader_drained204),.retire_commit(retire_commit204),.retire_generation(retire_gen204),
 .core_fault(rom_fault),.qualified_slot(native_fill_slot),.core_safe(native_core_safe),.core_request(rom_request),.core_address(rom_address),
 .core_ready(rom_ready),.core_response(rom_response),.core_error(rom_error),.core_response_address(rom_response_address),.core_data(rom_data),
 .mem_ready(native_mem_ready),.mem_request(native_mem_request),.mem_address(native_mem_address),.mem_response(native_mem_response),
 .mem_error(native_mem_error),.mem_response_address(native_mem_response_address),.mem_data(native_mem_data),
 .SPI_SS(ext_SPI_SS),.SPI_SCK(ext_SPI_SCK),.SPI_MOSI(ext_SPI_MOSI),.spi_selected(direct_selected204),.spi_miso(direct_miso204),
 .address(snes_addr),.read_n(read_n),.write_n(write_n),.data_in(snes_data_in),.data_out(bus_data),.oe_n(databus_oe_n),.dir(databus_dir),
 .host_fault(direct_fault204),.nes_fault(direct_nes_fault204));

'''+s[end:]
 s=replace(s,'wire [16:0] native_ack_data;wire [3:0] native_export_error;','wire [16:0] native_ack_data;')
 s=s.replace('nes_native_export181 #','nes_native_export203 #')
 start=s.index('nes_native_export203 #');end=s.index('nes_native_mailbox165 #',start)
 block=s[start:end].replace(".enable(1'b1)",'.enable(export_permitted204&&!direct_nes_fault204)').replace('!native_arbiter_fault','!direct_nes_fault204').replace('.release_frame(native_release_frame)','.release_frame(export_release204)')
 lo=block.index('.fill_start(');hi=block.index(' .tx_valid(',lo);block=block[:lo]+'\n'+block[hi:];s=s[:start]+block+s[end:]
 old='''wire native_spi_miso,native_spi_selected,native_spi_fault;
assign out_native_spi_fault=native_spi_fault;
assign out_spi_selected=native_boot_selected||native_spi_selected;
assign out_spi_miso=native_boot_selected&&!native_spi_selected?native_boot_miso:
 native_spi_selected&&!native_boot_selected?native_spi_miso:1'b0;'''
 s=replace(s,old,'''wire spi_collision204=(native_boot_selected&&native_spi_selected)||(native_boot_selected&&direct_selected204)||(native_spi_selected&&direct_selected204);
assign out_native_spi_fault=native_spi_fault||direct_fault204||spi_collision204;
assign out_spi_selected=native_boot_selected||native_spi_selected||direct_selected204;
assign out_spi_miso=spi_collision204?1'b0:native_boot_selected?native_boot_miso:native_spi_selected?native_spi_miso:direct_miso204;''')
 assert 'nes_native_fill165' not in s and 'native_arbiter(' not in s
 f.write_text(s,encoding='utf8',newline='\n')
 # Merge raw ownership, including write receivers. No bank40/SRAM overlap.
 f=out/'fxpak_nes_screen137_top.sv';s=f.read_text()
 s=replace(s,'nes_live_joint core(', 'nes_live_joint core(.ext_sink_fault(sink_fault),')
 s=replace(s,'wire sink_miso,sink_selected,sink_fault,native_spi_fault;',
 'wire sink_miso,sink_selected,sink_fault,native_spi_fault;\n wire [7:0] sink_data204;wire sink_oe204,sink_dir204;')
 s=replace(s,'.data_out(consumer_data),.oe_n(consumer_oe),.dir(consumer_dir)', '.data_out(sink_data204),.oe_n(sink_oe204),.dir(sink_dir204)')
 s=replace(s,' assign SNES_DATABUS_DIR=consumer_dir;', ''' assign consumer_oe=core_reset||(sink_oe204==bus_oe_n);
 assign consumer_dir=!consumer_oe&&(sink_oe204?bus_dir:sink_dir204);
 assign consumer_data=sink_oe204?bus_data:sink_data204;
 assign SNES_DATABUS_DIR=consumer_dir;''')
 f.write_text(s,encoding='utf8',newline='\n')
 f=out/'board.qsf';s=f.read_text()
 for n in ['nes_native_fill165.sv','nes_native_frame181.sv','nes_native_export181.sv']:
  s=replace(s,'set_global_assignment -name SYSTEMVERILOG_FILE '+n+'\n','')
 for n in added:s+='set_global_assignment -name SYSTEMVERILOG_FILE '+n+'\n'
 f.write_text(s,encoding='utf8',newline='\n')
 public['tools/nes_board204.py']=sha(Path(__file__))
 r=dict(sources={n:sha(out/n) for n in list(pins)+added},baseline=pins,added=added,changed=[n for n in pins if sha(out/n)!=pins[n]],
        public_sources=public,metadata_export_sha256=h,client_hex_sha256=sha(client/'sink-program.hex'),source_ready_from_actual_loader=True,
        full_board_binding=True,hardware_package=False,new_fit=False,scope=__doc__)
 (out/'preparation204.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8');return r
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();r=prepare(a.out);print(json.dumps(dict(files=len(r['sources']),changed=r['changed'],added=r['added'])))
