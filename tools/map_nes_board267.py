# SPDX-License-Identifier: MIT
"""Whole-board Lite MAP resource gate with explicit retained plan/ROM controls.

This is an unplaced resource integration, not production/CDC/STA approval.
The board's original capture lease and shared physical memory reader survive.
Source240 and old tile bulk/control are replaced; E8/E9+plan decoder remain.
"""
from pathlib import Path
import argparse,json,re,shutil,subprocess
from nes_delta231 import BASE,ROOT,sha,once
from nes_rom267 import MODULE

GLUE=r'''
//267 resource integration: source input commit and final display are distinct.
wire source_start_ready267,source_done267,waiting267,flow_retired267,flow_ack267,flow_fault267,bus_valid267;
wire identity_ready267,plan_fault267,plan_commit267,plan_done267;
reg source_started267,identity_pending267;reg [31:0] source_serial267;
always @(posedge clk)begin
 if(reset)begin source_started267<=0;source_serial267<=1;identity_pending267<=0;end
 else begin
  if(!lease204)source_started267<=0;
  else if(export_permitted204&&source_start_ready267&&!source_started267)source_started267<=1;
  if(source_done267)identity_pending267<=1;
  else if(identity_pending267&&identity_ready267)identity_pending267<=0;
  if(plan_commit267)source_serial267<=source_serial267+1'b1;
 end
end
assign export_release204=source_done267;
assign retire_commit204=plan_commit267;
assign retire_gen204=captured_gen204;
assign native_spi_fault=|native_export_error||flow_fault267||plan_fault267;
wire cancel_host267,cancel_nes267;
nes_fault267 retained_fault267(.nes_clk(clk),.host_clk(host_clk),.reset(reset),
 .transport_fault(native_spi_fault||ext_sink_fault),.lease_fault(lease_fault204),.core_fault(rom_fault),
 .spi_fault(plan_fault267),.batch_fault(1'b0),.bulk_fault(flow_fault267),.tile_fault(1'b0),.consume_error(1'b0),.command_error(1'b0),
 .host_fault(direct_fault204),.nes_fault(direct_nes_fault204),.hc(cancel_host267),.nc(cancel_nes267));
assign databus_oe_n=!bus_valid267;assign databus_dir=bus_valid267;
wire tv267,tr267,ev267,er267;wire [7:0] td267;wire [4:0] ti267;wire [5:0] tl267;wire [1:0] tk267;wire [9:0] ts267;
wire tile_closed267;
nes_joint267_board native_joint267(.clk(clk),.host_clk(host_clk),.reset(reset),.abort_source(direct_nes_fault204),
 .start(export_permitted204&&source_start_ready267&&!source_started267),.start_ready(source_start_ready267),
 .frame_owned(native_frame_owned),.geometry_valid(native_geometry_valid&&!rom_fault),.frame_generation(captured_gen204),.content_epoch(captured_epoch204),.frame_serial(source_serial267),
 .patch_count(native_patch_count181),.row_count(native_row_count),.object_count(native_object_count),.exception_count(native_exception_count),.group_count(native_group_count),.palette_count(native_palette_count),
 .query(native_query),.query_kind(native_query_kind),.query_index(native_query_index),.query_generation(native_query_generation),.response(native_response),.hit(native_hit),.data(native_data),
 .SPI_SS(ext_SPI_SS),.SPI_SCK(ext_SPI_SCK),.SPI_MOSI(ext_SPI_MOSI),.selected(native_spi_selected),.miso(native_spi_miso),.done(source_done267),.fault(native_export_error),
 .capture_begin(1'b0),.source_ready(source_ready204),.source_is_rom(source_rom204),.source_writing(source_write204),.reader_drained(reader_drained204),
 .release_frame(),.lease_valid(lease204),.waiting_display(waiting267),.lease_fault(lease_fault204),.retired(flow_retired267),.display_ack(flow_ack267),
 .identity_valid(identity_pending267),.identity_ready(identity_ready267),.bank(~source_serial267[0]),
 .address(snes_addr),.read_n(read_n),.write_n(write_n),.data_in(snes_data_in),.data_out(bus_data),.bus_valid(bus_valid267),
 .staged(),.receipt_committed(),.flow_fault(flow_fault267),.tile_closed267(tile_closed267),
 .tile_valid(tv267),.tile_ready(tr267),.tile_data(td267),.tile_index(ti267),.tile_length(tl267),.tile_kind(tk267),.tile_slot(ts267),.tile_generation(captured_gen204),
 .end_valid(ev267),.end_ready(er267),.end_generation(captured_gen204),.ordinary_ready(),.next_token(),
 .sink_ready(1'b1),.sink_valid(),.sink_data(),.sink_kind(),.sink_unit(),.sink_lane(),.stream_ready(),.v_ready(),.v_sealed(),.h_ready(),.context_ready(),.output_phase());
nes_plan_path267 retained_plan267(.clk(clk),.host_clk(host_clk),.reset(reset),.stop(cancel_host267||cancel_nes267),
 .lease(lease204),.retire_permitted(flow_retired267&&retire_permitted204),.retire_commit(plan_commit267),.generation(captured_gen204),
 .source_ready(source_ready204),.source_is_rom(source_rom204),.source_writing(source_write204),.captured_epoch(captured_epoch204),.live_epoch(source_epoch204),
 .SPI_SS(ext_SPI_SS),.SPI_SCK(ext_SPI_SCK),.SPI_MOSI(ext_SPI_MOSI),.selected(direct_selected204),.miso(direct_miso204),.tile_closed(tile_closed267),
 .tv(tv267),.tr(tr267),.td(td267),.ti(ti267),.tl(tl267),.tk(tk267),.ts(ts267),.ev(ev267),.er(er267),
 .qualified(native_fill_slot),.core_safe(native_core_safe),.core_request(rom_request),.core_address(rom_address),.core_ready(rom_ready),.core_response(rom_response),.core_data(rom_data),
 .core_error267(rom_error),.core_response_address267(rom_response_address),
 .mem_ready(native_mem_ready),.mem_response(native_mem_response),.mem_error(native_mem_error),.mem_response_address(native_mem_response_address),.mem_data(native_mem_data),
 .mem_request(native_mem_request),.mem_address(native_mem_address),.fault(plan_fault267),.drained(reader_drained204),.retire_done(plan_done267));
'''

def path_module():
 s=MODULE.replace('module nes_plan_rom267(','module nes_plan_path267(')
 s=s.replace('clk,host_clk,mem_clk,reset','clk,host_clk,reset')
 s=once(s,' input wire [15:0] generation,',''' input wire source_ready,source_is_rom,source_writing,input wire [31:0] captured_epoch,live_epoch,
 output wire retire_commit,core_error267,output wire [21:0] core_response_address267,
 input wire [15:0] generation,''')
 a=s.index(' output wire [21:0] psram_address,');b=s.index('\n);',a)
 s=s[:a]+''' input wire mem_ready,mem_response,mem_error,input wire [21:0] mem_response_address,input wire [7:0] mem_data,
 output wire mem_request,output wire [21:0] mem_address,output wire fault,drained,retire_done'''+s[b:]
 s=once(s,'.retire_commit(),','.retire_commit(retire_commit),')
 s=s.replace(".source_ready(1'b1),.source_is_rom(1'b1),.source_writing(1'b0),.captured_epoch(32'd1),.live_epoch(32'd1)",'.source_ready(source_ready),.source_is_rom(source_is_rom),.source_writing(source_writing),.captured_epoch(captured_epoch),.live_epoch(live_epoch)')
 a=s.index(' nes_rom_physical #');b=s.index(' assign fault=',a)
 s=s[:a]+''' assign mem_request=mr;assign mem_address=ma;
 assign mready=mem_ready;assign mresponse=mem_response;assign merror=mem_error;assign mra=mem_response_address;assign md=mem_data;
 assign core_error267=ce;assign core_response_address267=cra;
'''+s[b:]
 return s

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);p.add_argument('--test',type=Path,required=True);a=p.parse_args();d=a.out.resolve();assert not d.exists() and d.as_posix().isascii();d.mkdir(parents=True)
 test=json.loads((a.test/'result.json').read_text());assert test['passed'] and test['actual_tile_ROM']
 board=BASE/'probes/nes-source240/board01';pins={}
 for f in board.rglob('*'):
  rel=f.relative_to(board)
  if any(n in ('db','incremental_db','output_files') for n in rel.parts):continue
  if f.is_file() and f.suffix.lower() in ('.sv','.v','.vhd','.vh','.mif','.hex','.qsf','.qpf','.sdc','.qip'):
   target=d/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(f,target);pins[f.relative_to(BASE).as_posix()]=sha(f)
 files=[]
 oldfault=(board/'nes_direct206.sv').read_text();a0=oldfault.index(' reg hf,nf;');b=oldfault.index(' wire pw,',a0)
 fault='''module nes_fault267(input wire nes_clk,host_clk,reset,transport_fault,lease_fault,core_fault,
 input wire spi_fault,batch_fault,bulk_fault,tile_fault,consume_error,command_error,
 output wire host_fault,nes_fault,hc,nc);
'''+oldfault[a0:b].replace('wire hr,nr,hc,nc;','wire hr,nr;')+'endmodule\n'
 (d/'nes_fault267.sv').write_text(fault,encoding='utf-8',newline='\n');files.append('nes_fault267.sv')
 for name,h in test['rtl_hashes'].items():
  assert sha(a.test/name)==h
  if name=='nes_plan_rom267.sv':continue
  shutil.copyfile(a.test/name,d/name);files.append(name)
 joint_name='nes_joint265.sv' if test.get('baseline265') else 'nes_joint266.sv'
 f=d/joint_name;s=f.read_text(encoding='utf-8').replace('module '+f.stem,'module nes_joint267_board')
 s=once(s,'output wire release_frame,lease_valid,waiting_display,lease_fault,retired,display_ack,',
  'output wire release_frame,retired,display_ack,\ninput wire lease_valid,waiting_display,lease_fault,\noutput wire tile_closed267,')
 a0=s.index(' nes_capture_lease201 lease(');b=s.index(' nes_output260 #',a0)
 s=s[:a0]+''' assign display_generation=frame_generation;assign display_epoch=content_epoch;
 assign release_frame=1'b0;
 assign tile_closed267=flow.tiles_closed;
'''+s[b:]
 # Export via an ordinary port, never synthesize a hierarchical cross-reference.
 s=s.replace(' assign tile_closed267=flow.tiles_closed;','')
 s=once(s,'.identity_valid(identity_valid),','.tile_closed267(tile_closed267),.identity_valid(identity_valid),')
 f.write_text(s,encoding='utf-8',newline='\n')
 f=d/'nes_mux260.sv';s=f.read_text(encoding='utf-8');s=once(s,' output wire ordinary_ready,',' output wire tile_closed267,\n output wire ordinary_ready,')
 s=once(s,' reg tiles_closed;',' reg tiles_closed;assign tile_closed267=tiles_closed;');f.write_text(s,encoding='utf-8',newline='\n')
 (d/'nes_plan_path267.sv').write_text(path_module(),encoding='utf-8',newline='\n');files.append('nes_plan_path267.sv')
 f=d/'nes_live_joint.sv';s=f.read_text();a0=s.index('nes_direct206 direct_path(');b=s.index('assign native_nt_address=',a0);s=s[:a0]+s[b:]
 tail=s[s.index('wire spi_collision204='):]
 a0=s.index('// Source240 resource candidate:');s=s[:a0]+GLUE+'\n'+tail
 s=once(s,'.waiting_display(),.lease_fault(lease_fault204)', '.waiting_display(waiting267),.lease_fault(lease_fault204)')
 # Declare the reused waiting output before the capture instance.
 s=s.replace('wire source_start_ready267,source_done267,waiting267,','wire source_start_ready267,source_done267,')
 s=once(s,'wire [2:0] native_patch_count181;','wire waiting267;\nwire [2:0] native_patch_count181;')
 f.write_text(s,encoding='utf-8',newline='\n')
 q=d/'board.qsf';lines=q.read_text().splitlines();existing={line.split()[-1].strip('"') for line in lines if 'SYSTEMVERILOG_FILE' in line}
 for n in files:
  if n not in existing:lines.append('set_global_assignment -name SYSTEMVERILOG_FILE '+n)
 q.write_text('\n'.join(lines)+'\n',encoding='utf-8',newline='\n')
 with (d/'map.log').open('wb') as log:
  cp=subprocess.run(['C:/altera_lite/25.1std/quartus/bin64/quartus_map.exe','board'],cwd=d,stdout=log,stderr=subprocess.STDOUT,timeout=900,creationflags=subprocess.CREATE_NO_WINDOW)
 summary=(d/'output_files/board.map.summary').read_text() if (d/'output_files/board.map.summary').exists() else ''
 raw=(d/'map.log').read_text(errors='replace')
 undriven=re.findall(r'Warning \(10034\):[^\r\n]+',raw)
 r=dict(passed=cp.returncode==0,returncode=cp.returncode,summary=summary,scope=__doc__,input_hashes=pins,test_sha256=sha(a.test/'result.json'),
  baseline265=test.get('baseline265',False),changed_hashes={n:sha(d/n) for n in ['nes_live_joint.sv',joint_name,'nes_mux260.sv','nes_plan_path267.sv','nes_fault267.sv','board.qsf']},
  Quartus='Lite25.1std',whole_board_MAP=True,FIT=False,STA=False,functional_board_glue_verified=False,production=False,undriven_outputs=undriven,
  removed_instances=['native_source240','direct_path.bulk','direct_path.control'],
  retained_instances=['native_frame.ownership','direct_path fault/reset shell','E8/E9 endpoint','plan batch decoder/RAM','tile205','CHR cache','core-priority arbiter','loader shared physical ROM reader'])
 r['passed']=r['passed'] and not undriven
 (d/'result.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8',newline='\n');print(summary or raw[-3000:]);assert r['passed'],raw[-3000:]

if __name__=='__main__':main()
