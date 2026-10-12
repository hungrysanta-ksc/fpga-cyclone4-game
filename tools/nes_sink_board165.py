# SPDX-License-Identifier: MIT
"""Replace the physical164 framebuffer consumer with the native packet sink.

Materialization only: no firmware image or timing approval is implied.
"""
from pathlib import Path
import argparse,difflib,json,re,shutil
from nes_game147 import ROOT,sha
from nes_native_spi165 import prepare as native_prepare,FILES
from nes_native_ram_board165 import materialize as ram_materialize

SINK_FILES=['nes_sink_spi165.sv','nes_sink_bus165.sv','nes_sink_bridge165.sv']
def prepare(evidence,client,out):
 inputs=native_prepare(evidence,out)
 pins=json.loads((evidence/'manifest.json').read_bytes())['files']
 qsf=(evidence/'asm/board.qsf').read_text()
 names=re.findall(r'set_global_assignment -name (?:SYSTEMVERILOG_FILE|VERILOG_FILE|VHDL_FILE) (\S+)',qsf)
 for n in names+['board.qsf','board.qpf','board.sdc']:
  src=evidence/'asm'/n;assert sha(src)==pins['asm/'+n],n
  if not (out/n).exists():
   (out/n).parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,out/n)
  inputs['board/'+n]=sha(src)
 v=json.loads((ROOT/'analysis/native-sink165-verification.json').read_bytes())
 assert sha(client/'result.json')==v['raw_result_sha256']['sink01']
 expected='c60b6d145a9082dd85784b21f4ccf6b224cb6a2017677c9af4504f867ea91c9e'
 assert sha(client/'client/sink-program.hex')==expected
 shutil.copy2(client/'client/sink-program.hex',out/'sink-program.hex')
 for n in SINK_FILES:shutil.copy2(ROOT/'src/nes/diagnostic'/n,out/n)
 diffs=[]
 def edit(n,fn):
  p=out/n;old=p.read_text();new=fn(old);assert old!=new
  p.write_text(new,encoding='utf8');diffs.extend(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='native/'+n,tofile='board165/'+n))
 def once(s,a,b):assert s.count(a)==1,(a,s.count(a));return s.replace(a,b,1)
 def joint(s):
  s=once(s,'module nes_live_joint(','module nes_live_joint(\noutput wire out_native_spi_fault,')
  return once(s,'wire native_spi_miso,native_spi_selected,native_spi_fault;','wire native_spi_miso,native_spi_selected,native_spi_fault;\nassign out_native_spi_fault=native_spi_fault;')
 edit('nes_live_joint.sv',joint)
 def top(s):
  s=once(s,'wire boot_miso,boot_selected,observer_miso,observer_selected;','wire boot_miso,boot_selected,observer_miso,observer_selected;\n wire sink_miso,sink_selected,sink_fault,native_spi_fault;')
  s=once(s,'nes_live_joint core(', 'nes_live_joint core(.out_native_spi_fault(native_spi_fault),')
  start=s.index(' nes_game_frame150 framebuffer(');end=s.index(' nes_game_pad150 pad(',start)
  s=s[:start]+s[end:]
  start=s.index(' nes_game_bus151 consumer(');end=s.index(' assign SNES_DATABUS_DIR',start)
  s=s[:start]+''' // Common RUN reset covers producer, sink, client and pad ownership.
 // ROM faults are sticky NES-domain levels; synchronize before STOP readout.
 (* altera_attribute="-name SYNCHRONIZER_IDENTIFICATION FORCED_IF_ASYNCHRONOUS" *) reg [1:0] sink_rom_fault;
 always @(posedge host_clk or posedge core_reset)
  if(core_reset)sink_rom_fault<=0;else sink_rom_fault<={sink_rom_fault[0],rom_fault};
 nes_sink_bridge165 sink(.clk(host_clk),.raw_reset(core_reset),.active(run_enable&&!core_reset),
  .stop(sink_rom_fault[1]||native_spi_fault),
  .SPI_SS(SPI_SS),.SPI_SCK(SPI_SCK),.SPI_MOSI(SPI_MOSI),.spi_selected(sink_selected),.spi_miso(sink_miso),
  .address(SNES_ADDR_IN),.read_n(SNES_READ_IN),.write_n(SNES_WRITE_IN),.romsel_n(SNES_ROMSEL_IN),
  .data_in(SNES_DATA),.data_out(consumer_data),.oe_n(consumer_oe),.dir(consumer_dir),
  .pad_commit(pad_commit),.pad_buttons(pad_buttons),.fault(sink_fault));
'''+s[end:]
  start=s.index(' assign SPI_MISO=');end=s.index(' nes_domain_reset124 status_release',start)
  s=s[:start]+''' // Exclusive boot/native(D0..D3), observer70, status73, sinkE0/E1.
 // Unexpected overlap releases the physical MISO pin.
 assign SPI_MISO=boot_selected&&!observer_selected&&!status_selected&&!sink_selected?boot_miso:
                 observer_selected&&!boot_selected&&!status_selected&&!sink_selected?observer_miso:
                 status_selected&&!boot_selected&&!observer_selected&&!sink_selected?status_miso:
                 sink_selected&&!boot_selected&&!observer_selected&&!status_selected?sink_miso:1'bz;
'''+s[end:]
  s=once(s,' wire frame_ready,frame_response,frame_request,release_frame,pad_commit;\n wire [7:0] frame_data;wire [15:0] frame_address,pad_buttons;',' wire pad_commit;wire [15:0] pad_buttons;')
  s=once(s,' // Both slaves release on raw CS. Distinct command ranges60..6A and70.\n // An unexpected overlap fails closed instead of driving ambiguous data.\n','')
  return s
 edit('fxpak_nes_screen137_top.sv',top)
 # Old164 firmware must not accept the old E5 client identity for this ABI.
 edit('nes_screen_status151.sv',lambda s:once(s,"8'he5,stage,error_code,5'd0,flags,frames,8'd1","8'he6,stage,error_code,5'd0,flags,frames,8'd2"))
 remove={'nes_game_frame150.sv','nes_game_bus151.sv'}
 qsf='\n'.join(l for l in qsf.splitlines() if not any(l.endswith(' '+n) for n in remove) and '-to framebuffer|' not in l)+'\n'
 existing=set(names)
 # Some intermediate materializers copy superseded observers. Add only final
 # modules referenced by the actual native frame/exporter hierarchy.
 added=['nes_native_planes165.sv','nes_native_compact_planes165.sv','nes_native_raster_frame165.sv','nes_native_frame165.sv','nes_native_fill165.sv','nes_native_arbiter165.sv','nes_native_export165.sv','nes_native_mailbox165.sv','nes_native_spi165.sv']+SINK_FILES
 for n in added:
  assert (out/n).exists(),n
  if n not in existing:qsf+='set_global_assignment -name SYSTEMVERILOG_FILE '+n+'\n'
 (out/'board.qsf').write_text(qsf)
 toptext=(out/'fxpak_nes_screen137_top.sv').read_text()
 assert 'nes_game_frame150' not in toptext and 'nes_game_bus151' not in toptext
 for n in ['nes_game_pad150.sv','nes_dac162.sv','nes_run_observer134.sv','nes_pad_trace156.sv']:
  assert sha(out/n)==pins['asm/'+n],n
 assert 'assign RAM_ADDR=0;assign RAM_OE=1;assign RAM_WE=1;assign RAM_DATA=8\'hzz;' in toptext
 assert [l for l in qsf.splitlines() if l.startswith('set_location_assignment')]==[l for l in (evidence/'asm/board.qsf').read_text().splitlines() if l.startswith('set_location_assignment')]
 (out/'sink-board-binding.diff').write_text(''.join(diffs),encoding='utf8')
 ram_materialize(out)
 source_names=re.findall(r'set_global_assignment -name (?:SYSTEMVERILOG_FILE|VERILOG_FILE|VHDL_FILE) (\S+)',qsf)
 meta=dict(inputs=inputs,sources={n:sha(out/n) for n in source_names},rom_sha256=expected,framebuffer_removed=True,save_sram_reserved=True,physical_pins_unchanged=True,client_identity='E6/2',sink_identity='F6',public_sources={n:sha(ROOT/n) for n in ['tools/nes_sink_board165.py','tools/nes_native_ram_board165.py']},hardware_package=False)
 (out/'preparation.json').write_text(json.dumps(meta,indent=2)+'\n');return meta
if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ['evidence','client','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();prepare(a.evidence,a.client,a.out)
