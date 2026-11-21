"""Replay cartridge accesses from an actual 65816 boot in the MMC891 board RTL."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

from nes_reset892 import PROBES, ROOT


def cpu(temp,out):
    out.mkdir(parents=True)
    script=out/'boot.lua'
    script.write_text('local f=assert(io.open('+json.dumps((out/'cpu.txt').as_posix())+', "w"))\n'+"""
local function log(k,a,v)
 f:write(string.format('%s %x %x %d\\n',k,a,v,emu.getState().masterClock))
end
emu.addMemoryCallback(function(a,v) log('r',a,v) end,emu.callbackType.read,0x8000,0xffff)
emu.addMemoryCallback(function(a,v) log('x',a,v) end,emu.callbackType.exec,0x8000,0x8026)
emu.addMemoryCallback(function(a,v)
 log('w',a,v); f:close();emu.stop(0)
end,emu.callbackType.write,0x7000)
emu.addEventCallback(function() if emu.getState().frameCount>2 then emu.stop(1) end end,emu.eventType.endFrame)
""")
    with (out/'mesen.log').open('wb') as f:
        subprocess.run([temp/'nes-bonus698-mesen/Mesen.exe','--testRunner',script,
                        PROBES/'nes-trial890/client02/sink165.sfc','--timeout=40','--doNotSaveSettings',
                        '--enableStdout','--debug.scriptWindow.allowIoOsAccess=true'],cwd=out,stdout=f,
                       stderr=subprocess.STDOUT,env=dict(os.environ,DOTNET_ROOT='C:/works/dotnet',
                       DOTNET_ROOT_X64='C:/works/dotnet'),timeout=60,check=True)
    events=(out/'cpu.txt').read_text().splitlines()
    assert events[-1]=='w 7000 1 640' and any(e.startswith('x 8000 ') for e in events)


def simulate(temp,out,trace,bin_dir):
    board=temp/'nes-trial816-board891E'
    out.mkdir(parents=True)
    files=re.findall(r'^set_global_assignment -name (VHDL|VERILOG|SYSTEMVERILOG)_FILE (\S+)',
                     (board/'board.qsf').read_text(),re.M)
    for _,name in files:
        (out/name).parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(board/name,out/name)
    for name in ('rtl','sys'):
        shutil.copytree(board/name,out/name,dirs_exist_ok=True)
    for f in board.iterdir():
        if f.suffix in ('.vh','.svh','.mif','.hex'):
            shutil.copyfile(f,out/f.name)
    shutil.copyfile(trace/'cpu.txt',out/'cpu.txt')
    # Reuse the SPI, write and polling waveform primitives from the 891 pin test.
    fixture=(ROOT/'tools/nes_boot891_tb.sv').read_text().split(' reg [63:0] reply;')[0]
    fixture=fixture.replace('module nes_boot891_tb;', 'module nes_reset892_tb;\n reg nesclk=0;always #23.283 nesclk=~nesclk;')
    fixture=fixture.replace(".SNES_SYSCLK(1'b0)",".SNES_SYSCLK(nesclk)")
    (out/'reset892.sv').write_text(fixture+(ROOT/'tools/nes_reset892_cases.svh').read_text())
    def run(exe,args,log):
        with (out/log).open('wb') as f:
            subprocess.run([bin_dir/(exe+'.exe'),*args],cwd=out,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=900)
    run('vmap',['-c'],'vmap.log')
    run('vlib',['work'],'vlib.log')
    for i,(kind,name) in enumerate(files):
        if kind=='VHDL':
            run('vcom',['-2008',name],f'vcom-{i}.log')
    run('vlog',['-sv','-mfcu',*[n for k,n in files if k!='VHDL'],'reset892.sv'],'vlog.log')
    run('vsim',['-c','-L','altera_mf_ver','-L','cycloneive_ver','work.nes_reset892_tb',
                '-do','onerror {quit -code 1};run -all;quit -f'],'sim.log')
    text=(out/'sim.log').read_text(errors='replace')
    assert 'PASS RESET892' in text
    rows=[dict(field.split('=') for field in row.split()) for row in re.findall(r'^# RESET892 (.*)$',text,re.M)]
    assert len(rows)==12
    (out/'result.json').write_text(json.dumps(rows,indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=['cpu','simulate'])
    p.add_argument('temp',type=Path)
    p.add_argument('out',type=Path)
    p.add_argument('--trace',type=Path)
    p.add_argument('--bin',type=Path,default=Path('C:/altera_standard/25.1std/questa_fse/win64'))
    a=p.parse_args()
    if a.action=='cpu':
        cpu(a.temp,a.out)
    else:
        simulate(a.temp,a.out,a.trace,a.bin)
