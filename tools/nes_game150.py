# SPDX-License-Identifier: MIT
"""Physical game top from pinned146 board and148 SMB3 core, without ROM assets."""
from pathlib import Path
import argparse,difflib,json,re,shutil
from nes_game147 import ROOT,sha
from build_nes_game150 import build

MODULES=['nes_game_frame150.sv','nes_game_pad150.sv','nes_game_bus150.sv']
def prepare(baseline,out):
    assert not out.exists() and str(out).isascii();out.mkdir(parents=True)
    old=baseline/'nes-display146/evidence';game=baseline/'nes-game148/evidence'
    inputs={};patches=[]
    for e,meta in [(old,'screen146'),(game,'game148')]:
        assert sha(e/'manifest.json')==json.loads((ROOT/f'analysis/{meta}-verification.json').read_bytes())['manifest_sha256']
    pins=json.loads((old/'manifest.json').read_bytes())['files']
    gamepins=json.loads((game/'manifest.json').read_bytes())['files']
    qsf=(old/'fit/board.qsf').read_text()
    removed=['nes_packet_queue_ram.sv','nes_packet_cdc_ram.sv','nes_host_stage.sv','nes_snes_frontend.sv',
             'nes_transport.sv','nes_packet_memory_producer.sv','nes_ncr1_encoder.sv','nes_ncr1_ppu_tap.sv','nes_screen_bus137.sv']
    qsf='\n'.join(line for line in qsf.splitlines() if not any(n in line for n in removed))+'\n'
    names=re.findall(r'set_global_assignment -name (?:SYSTEMVERILOG|VERILOG|VHDL)_FILE (\S+)',qsf)
    for n in names+['board.sdc']:
        source=old/'fit'/n;pin=pins['fit/'+n];label='146/'+n
        if 'core03/'+n in gamepins:
            source=game/'core03'/n;pin=gamepins['core03/'+n];label='148/'+n
        assert sha(source)==pin,n
        dest=out/n;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,dest);inputs[label]=pin
    def edit(name,changes):
        p=out/name;before=after=p.read_text()
        for a,b in changes:
            assert after.count(a)==1,(name,a,after.count(a));after=after.replace(a,b)
        p.write_text(after,encoding='utf8',newline='\n')
        patches.extend(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='prior/'+name,tofile='150/'+name))
    edit('nes_live_joint.sv',[
        ('output wire [16:0] out_loaded_bytes,','output wire [18:0] out_loaded_bytes,'),
        ('wire [16:0] loaded_bytes;','wire [18:0] loaded_bytes;'),
        ('wire arm=ext_arm && frame_ready && supported_mode;','wire arm=1\'b0;'),
        (' nes_ncr1_ppu_tap tap(.*);\n nes_ncr1_encoder encoder(.*);\n nes_packet_memory_producer producer(.*);\n nes_transport transport(.reset(common_reset),.*);',
         " assign bus_data=0;assign databus_oe_n=1;assign databus_dir=0;\n assign ready=0;assign busy=0;assign fault=0;assign encoder_fault=0;\n assign producer_fault=0;assign tap_fault=0;assign tap_error=0;assign published=0;"),
        ('wire rom_cpu_address_valid,rom_ppu_address_valid;','wire rom_cpu_address_valid,rom_ppu_address_valid,game147_prefetch_hint;\n wire [21:0] game148_hint_physical;'),
        ('nes_rom_early rom_service(',"nes_rom_early rom_service(\n .ppu_prefetch_valid(game147_prefetch_hint && (rom_ppu_valid || (ppumem_addr>=22'h3a0000 && ppumem_addr<22'h3a0800))),.ppu_prefetch_address(game148_hint_physical),")])
    top=(out/'fxpak_nes_screen137_top.sv').read_text()
    top=top.replace('.ext_joypad1(5\'d0),.ext_joypad2(5\'d0),',".ext_joypad1({4'd0,pad_serial}),.ext_joypad2(5'd0),\n  .out_color(pixel_color),.out_cycle(pixel_cycle),.out_scanline(pixel_line),\n  .out_joypad_clock(pad_clock),.out_joypad_out(pad_strobe),")
    decl='''wire [5:0] pixel_color;wire [8:0] pixel_cycle,pixel_line;
 wire [1:0] pad_clock;wire [2:0] pad_strobe;wire pad_serial;
 wire frame_ready,frame_response,frame_request,release_frame,pad_commit;
 wire [7:0] frame_data;wire [15:0] frame_address,pad_buttons;
'''
    top=top.replace(' nes_live_joint core(',decl+' nes_live_joint core(')
    start=top.index(' nes_screen_bus137 consumer(');end=top.index(' assign SNES_DATABUS_DIR=',start)
    top=top[:start]+''' nes_game_frame150 framebuffer(.nes_clk(SNES_SYSCLK),.host_clk(host_clk),.reset(core_reset),
 .cycle(pixel_cycle),.scanline(pixel_line),.color(pixel_color),.release_frame(release_frame),
 .ready(frame_ready),.request(frame_request),.byte_address(frame_address),.response(frame_response),.data(frame_data));
 nes_game_pad150 pad(.nes_clk(SNES_SYSCLK),.host_clk(host_clk),.reset(core_reset),
 .commit(pad_commit),.snes_buttons(pad_buttons),.host_ready(),
 .strobe(pad_strobe[0]),.read_clock(pad_clock[0]),.serial(pad_serial));
 nes_game_bus150 consumer(.host_clk(host_clk),.reset(core_reset),.active(run_enable),
 .address(SNES_ADDR_IN),.read_n(SNES_READ_IN),.write_n(SNES_WRITE_IN),.romsel_n(SNES_ROMSEL_IN),
 .data_in(SNES_DATA),.data_out(consumer_data),.oe_n(consumer_oe),.dir(consumer_dir),
 .frame_ready(frame_ready),.frame_response(frame_response),.frame_data(frame_data),
 .frame_request(frame_request),.frame_address(frame_address),.release_frame(release_frame),
 .pad_commit(pad_commit),.pad_buttons(pad_buttons));
'''+top[end:]
    (out/'fxpak_nes_screen137_top.sv').write_text(top,encoding='utf8',newline='\n')
    # New identity belongs to this wiring, not the old D9 packet consumer.
    for name,oldid,newid in [('nes_rom_spi.sv',"8'h5f","8'h60"),('nes_run_observer134.sv',"8'hd9","8'hda"),('nes_screen_status142.sv',"8'hd9","8'hda")]:
        p=out/name;s=p.read_text();assert oldid in s,name;p.write_text(s.replace(oldid,newid),encoding='utf8',newline='\n')
    for n in MODULES:
        shutil.copy2(ROOT/'src/nes/diagnostic'/n,out/n)
        qsf+=f'set_global_assignment -name SYSTEMVERILOG_FILE {n}\n'
    for target in ['framebuffer|release_meta','framebuffer|release_sync','framebuffer|publish_meta','framebuffer|publish_sync',
                   'pad|request_meta','pad|request_sync','pad|ack_meta','pad|ack_sync']:
        qsf+=f'set_instance_assignment -name SYNCHRONIZER_IDENTIFICATION FORCED_IF_ASYNCHRONOUS -to {target}\n'
    shutil.copy2(build(out/'client'),out/'game-program.hex')
    (out/'board.qsf').write_text(qsf,encoding='utf8',newline='\n');(out/'board.qpf').write_text('PROJECT_REVISION = "board"\n')
    (out/'joint.diff').write_text(''.join(patches),encoding='utf8',newline='\n')
    sources={n:sha(out/n) for n in names+MODULES+['board.qsf','board.sdc','game-program.hex']}
    (out/'result.json').write_text(json.dumps(dict(inputs=inputs,sources=sources,hardware=False,
      id=[0x60,0xda],scope='Game board materialization. MCU150 pairing, implementation timing and physical test required.'),indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ['baseline','out']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();prepare(a.baseline,a.out)
