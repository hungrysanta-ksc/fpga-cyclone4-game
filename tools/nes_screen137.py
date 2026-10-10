# SPDX-License-Identifier: MIT
"""Materialize135 physical core plus live consumer bus; never alter pinned inputs."""
from pathlib import Path
import argparse, hashlib, json, re, shutil, subprocess
from build_nes_screen137 import build
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(p,s):p.write_text(s,encoding='utf-8',newline='\n')
def factor_counter(s):
    #137 fit01 exposed load_valid -> global priority mux -> loaded_bytes.
    # Derive the counter's exact clear/advance conditions independently of the
    # unrelated state/error transitions. No command or write edge is delayed.
    assert s.count('loaded_bytes<=0;')==6
    assert s.count("loaded_bytes<=loaded_bytes+1'b1;")==1
    s=s.replace('loaded_bytes<=0;','').replace("loaded_bytes<=loaded_bytes+1'b1;",'')
    block='''
 wire count_stop=stop && !load_begin && !load_end && !start &&
     (state==IDLE || state==READY || state==RECEIVE || state==SETUP || state==RELEASE);
 wire count_begin=load_begin && !load_end && !start && !stop && !load_valid &&
     (state==IDLE || state==READY);
 wire count_advance=state==RELEASE && remaining==1 && !stop && !load_begin && !load_end && !start;
 always @(posedge mem_clk or posedge reset)begin
  if(reset)loaded_bytes<=0;
  else if(active_reset)loaded_bytes<=0;
  else if(!fault)begin
   if(count_stop || count_begin)loaded_bytes<=0;
   else if(count_advance)loaded_bytes<=loaded_bytes+1'b1;
  end
 end
'''
    return s.replace('endmodule',block+'endmodule')
def prepare(baseline,out):
    assert not out.exists() and str(out).isascii();out.mkdir(parents=True)
    old=baseline/'nes-command135/evidence';meta=json.loads((ROOT/'analysis/command135-verification.json').read_bytes())
    assert sha(old/'manifest.json')==meta['manifest_sha256']
    pins=json.loads((old/'manifest.json').read_bytes())['files'];inputs={}
    qsf=(old/'fit03/board.qsf').read_text()
    names=re.findall(r'set_global_assignment -name (?:SYSTEMVERILOG|VERILOG|VHDL)_FILE (\S+)',qsf)
    for n in names+['board.sdc']:
        p=old/'fit03'/n;assert sha(p)==pins['fit03/'+n],n
        d=out/n;d.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,d);inputs['135fit03/'+n]=sha(p)
    p=out/'nes_rom_loader.sv';put(p,factor_counter(p.read_text()))
    fixture=baseline/'nes-safe122/evidence';pins122=json.loads((fixture/'manifest.json').read_bytes())['files']
    assert sha(fixture/'manifest.json')==json.loads((ROOT/'analysis/safe122-verification.json').read_bytes())['manifest_sha256']
    for n in ['prg.hex','chr.hex']:
        rel='full02/phase03500/fine_x/'+n;p=fixture/rel;assert sha(p)==pins122[rel]
        shutil.copy2(p,out/n);inputs['122/'+rel]=sha(p)
    rom=build(bytes(int(x,16) for x in (out/'chr.hex').read_text().split()),out/'client')
    shutil.copy2(rom,out/rom.name)
    p=out/'nes_live_joint.sv';s=p.read_text();old_arm='wire arm=ext_arm;';assert s.count(old_arm)==1
    s=s.replace(old_arm,'//137 Admit only initialized supported frames when the encoder is free.\n wire arm=ext_arm && frame_ready && supported_mode;')
    s=s.replace('output wire out_observe_reset,','output wire out_host_clk,output wire out_observe_reset,')
    s=s.replace('assign out_observe_reset=reset;','assign out_host_clk=ext_host_clk;\nassign out_observe_reset=reset;');put(p,s)
    p=out/'fxpak_nes_run134_top.sv';s=p.read_text().replace('fxpak_nes_run134_top','fxpak_nes_screen137_top')
    s=s.replace('// Minimum RUN diagnostic shell. SNES stays reset under MCU ownership.\n// No SNES program ROM/video/input/audio consumer is enabled in this candidate.','//137 Live diagnostic screen wiring. MCU display handoff is not yet packaged.')
    s=s.replace('input wire CLKIN,SNES_SYSCLK,','input wire CLKIN,SNES_SYSCLK,\n input wire [23:0] SNES_ADDR_IN,\n input wire SNES_READ_IN,SNES_WRITE_IN,SNES_ROMSEL_IN,')
    s=s.replace('wire [3:0] rom_error;','wire [3:0] rom_error;\n wire host_clk,run_enable;wire [7:0] bus_data,consumer_data;wire bus_oe_n,bus_dir;')
    s=s.replace('.ext_arm(1\'b0)',".ext_arm(1'b1)")
    s=s.replace(".ext_snes_addr(24'd0),.ext_read_n(1'b1),.ext_write_n(1'b1),.ext_romsel_n(1'b1),.ext_snes_data_in(8'd0)",'.ext_snes_addr(SNES_ADDR_IN),.ext_read_n(SNES_READ_IN),.ext_write_n(SNES_WRITE_IN),.ext_romsel_n(SNES_ROMSEL_IN),.ext_snes_data_in(SNES_DATA)')
    s=s.replace('.out_observe_reset(core_reset)', '.out_host_clk(host_clk),.out_run_enable(run_enable),\n  .out_bus_data(bus_data),.out_databus_oe_n(bus_oe_n),.out_databus_dir(bus_dir),\n  .out_observe_reset(core_reset)')
    s=s.replace("assign SNES_DATA=8'hzz;\n assign SNES_DATABUS_OE=1;assign SNES_DATABUS_DIR=0;assign SNES_IRQ=0;",'''nes_screen_bus137 consumer(.host_clk(host_clk),.reset(core_reset),.run_enable(run_enable),
 .address(SNES_ADDR_IN),.read_n(SNES_READ_IN),.write_n(SNES_WRITE_IN),.romsel_n(SNES_ROMSEL_IN),
 .link_data(bus_data),.link_oe_n(bus_oe_n),.link_dir(bus_dir),.data_out(consumer_data),
 .oe_n(SNES_DATABUS_OE),.dir(SNES_DATABUS_DIR));
 assign SNES_DATA=SNES_DATABUS_DIR&&!SNES_DATABUS_OE?consumer_data:8'hzz;
 assign SNES_IRQ=0;''')
    put(out/'fxpak_nes_screen137_top.sv',s)
    shutil.copy2(ROOT/'src/nes/diagnostic/nes_screen_bus137.sv',out/'nes_screen_bus137.sv')
    qsf=qsf.replace('fxpak_nes_run134_top','fxpak_nes_screen137_top')
    qsf+='\nset_global_assignment -name SYSTEMVERILOG_FILE nes_screen_bus137.sv\n'
    # Use the established board map, not invented pin locations.
    wanted={f'SNES_ADDR_IN[{i}]' for i in range(24)}|{'SNES_READ_IN','SNES_WRITE_IN','SNES_ROMSEL_IN'}
    loc={}
    for line in (ROOT/'src/fpga/pin.qsf').read_text().splitlines():
        if ' -to ' not in line:continue
        target=line.split(' -to ',1)[1].strip('"')
        if target in wanted:
            if line.startswith('set_location_assignment '):loc[target]=line.split()[1];qsf+=line+'\n'
            elif any('-name '+n+' ' in line for n in ['IO_STANDARD','CURRENT_STRENGTH_NEW','WEAK_PULL_UP_RESISTOR']):qsf+=line+'\n'
    assert set(loc)==wanted
    put(out/'board.qsf',qsf);put(out/'board.qpf','PROJECT_REVISION = "board"\n')
    put(out/'materialization137.json',json.dumps(dict(candidate='NES-SCREEN-137',inputs=inputs,added_pins=loc,
      changes=['arm gates initialization/backpressure','consumer bus +24KiB program ROM','27 physical SNES inputs','state-local loaded byte counter'],
      hardware_approved=False,scope='No MCU reset-release handoff yet; not installable.'),indent=2)+'\n')
    shutil.copy2(__file__,out/'executed-screen137.py')
    return names

def main():
    p=argparse.ArgumentParser()
    for n in ['baseline','out']:p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--quartus-bin',type=Path);a=p.parse_args();prepare(a.baseline,a.out)
    if a.quartus_bin:
        results={}
        for phase in ['map','fit','sta']:
            with (a.out/(phase+'.log')).open('wb') as f:r=subprocess.run([str(a.quartus_bin/('quartus_'+phase+'.exe')),'board'],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=900)
            results[phase]=r.returncode;put(a.out/'fit137.json',json.dumps(results,indent=2)+'\n')
            print(phase,r.returncode,flush=True)
            if r.returncode:break
        for n in ['board.fit.summary','board.sta.summary']:
            p=a.out/'output_files'/n
            if p.exists():print(p.read_text(errors='replace'))
if __name__=='__main__':main()
