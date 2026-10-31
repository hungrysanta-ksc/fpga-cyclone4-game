# SPDX-License-Identifier: MIT
"""Capture position probes for the scripted NES route; verify alignment to the original PPU states."""
import argparse
import csv
import json
import os
import subprocess
from pathlib import Path
from run_nes_scroll229 import ROM_SHA, sha

ROOT=Path(__file__).resolve().parents[1]
OBSERVER="""
local rows=assert(io.open(OUT_DIR..'/positions.csv','w'))
rows:write('frame,nes_clock,player_x,player_y,slot_xy,oam,world_state\\n')
emu.addEventCallback(function()
 local state=emu.getState();local f=state.frameCount
 if f>=905 then
  local slots={};local oam={};local snapshot={}
  for i=0,7 do slots[#slots+1]=string.format('%02x%02x',emu.read(0x91+i,emu.memType.nesMemory),emu.read(0xa3+i,emu.memType.nesMemory)) end
  for i=0,255 do oam[#oam+1]=string.char(emu.read(i,emu.memType.nesSpriteRam)) end
  for _,part in ipairs({{emu.memType.nesNametableRam,2048},{emu.memType.nesSpriteRam,256},{emu.memType.nesPaletteRam,32}}) do
   for i=0,part[2]-1 do snapshot[#snapshot+1]=string.char(emu.read(i,part[1])) end
  end
  for i=0,7 do local p=emu.convertAddress(i*1024,emu.memType.nesPpuMemory,emu.cpuType.nes);snapshot[#snapshot+1]=string.pack('<I4I2',p.address,p.memType) end
  local function hex(s)return (s:gsub('.',function(c)return string.format('%02x',string.byte(c))end))end
  rows:write(string.format('%d,%d,%d,%d,%s,%s,%s\\n',f,state.masterClock,emu.read(0x90,emu.memType.nesMemory),emu.read(0xa2,emu.memType.nesMemory),table.concat(slots),hex(table.concat(oam)),hex(table.concat(snapshot))))
 end
 if f>=END_FRAME then rows:close();emu.stop(0) end
end,emu.eventType.endFrame)
"""

def run(a):
    assert sha(a.rom)==ROM_SHA and a.frames>=975
    a.out.mkdir(parents=True,exist_ok=False)
    source=(ROOT/'tests/nes-functional/capture_scroll229.lua').read_text()
    pinned=json.loads((a.capture/'capture.json').read_text())
    assert sha(a.mesen)==pinned['emulator_sha256']
    assert sha(a.mesen.parent/'MesenCore.dll')==pinned['core_sha256']
    assert sha(ROOT/'tests/nes-functional/capture_scroll229.lua')==pinned['script_sha256']
    input_script=source[source.index('local function input(f)'):source.index('local function screenshot(f)')]
    lua=f'local OUT_DIR={json.dumps(a.out.as_posix())}\nlocal END_FRAME={a.frames}\n'+input_script+OBSERVER
    (a.out/'positions.lua').write_text(lua,encoding='utf8')
    rom=a.out/'local.nes';rom.write_bytes(a.rom.read_bytes())
    with (a.out/'mesen.log').open('wb') as log:
        subprocess.run([str(a.mesen),'--testRunner',str(a.out/'positions.lua'),str(rom),'--timeout=180','--doNotSaveSettings',
                        '--enableStdout','--debug.scriptWindow.allowIoOsAccess=true'],env=dict(os.environ,DOTNET_ROOT='C:/works/dotnet',DOTNET_ROOT_X64='C:/works/dotnet'),
                       cwd=a.out,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=195,creationflags=subprocess.CREATE_NO_WINDOW)
    original=(a.capture/'mesen.log').read_text(errors='replace').splitlines()
    current=(a.out/'mesen.log').read_text(errors='replace').splitlines()
    board=lambda lines:[line for line in lines if line.startswith('[DB]')]
    assert board(current)==board(original) and '[DB] Chip: MMC3A' in current, 'NES database/board mismatch'
    old={int(x[0]):int(x[1]) for l in (a.capture/'frames.tsv').read_text().splitlines() if len(x:=l.split())==6}
    with (a.out/'positions.csv').open() as f:rows=list(csv.DictReader(f))
    assert [int(r['frame']) for r in rows]==list(range(905,a.frames+1))
    for r in rows[:71]:
        g=int(r['frame'])
        assert int(r['nes_clock'])==old[g] and bytes.fromhex(r['world_state'])==(a.capture/f'state-{g:04d}.bin').read_bytes()
    def stats(rows):
        pairs=list(zip(rows,rows[1:]))
        return dict(first=int(rows[0]['frame']),last=int(rows[-1]['frame']),intervals=len(pairs),
                    player_xy_changes=sum((a['player_x'],a['player_y'])!=(b['player_x'],b['player_y']) for a,b in pairs),
                    slot_xy_changes=sum(a['slot_xy']!=b['slot_xy'] for a,b in pairs),oam_changes=sum(a['oam']!=b['oam'] for a,b in pairs))
    r=dict(ROM_SHA256=ROM_SHA,emulator_SHA256=sha(a.mesen),core_SHA256=sha(a.mesen.parent/'MesenCore.dll'),input_script_sha256=sha(ROOT/'tests/nes-functional/capture_scroll229.lua'),
           matched_PPU_states_and_clocks=71,matched=stats(rows[:71]),extended=stats(rows),
           trace_SHA256=sha(a.out/'positions.csv'),scope='Position samples, not an authoritative count of all game logic updates; input is scripted, not the hardware playthrough.')
    (a.out/'reference.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8',newline='\n')
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('rom','out','mesen','capture'):p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--frames',type=int,default=1800)
    a=p.parse_args();a.out=a.out.resolve();run(a)
