"""Calibrate the linked first-block replay to the hardware checkpoint and check the BOOT control."""
import argparse
import json
import re
from pathlib import Path
from zipfile import ZipFile, ZipInfo

from check_nes_block894 import BASE, WORK, FirstBlock
from check_nes_game478 import Machine, sha, UC_ARM_REG_SP, UC_ARM_REG_PC, UC_ARM_REG_LR
from check_nes_reset796 import replay


def records(path, edition):
    data = path.read_bytes()
    assert len(data) == 80 * 512
    result = []
    for i in range(80):
        sector = data[i*512:(i+1)*512]
        line = sector.decode('ascii').rstrip().split()
        assert sector.endswith(b'\n') and line[0] == f'MMC{edition}'
        row = dict(field.split('=') for field in line[1:])
        assert int(row['seq']) == i
        result.append(row)
    return result


def check(progress, previous):
    src = WORK/'linkB/src'
    linked = json.loads((WORK/'checks.json').read_bytes())
    image = src/'obj-nes-100/firmware.stm'
    assert sha(image)==linked['firmware']
    current, old = records(progress,894), records(previous,893)
    for a,b in zip(current,old):
        exclude = {'elapsed_ms'} if a['seq']!='79' else {'elapsed_ms','bytes','total'}
        assert {k:v for k,v in a.items() if k not in exclude} == {k:v for k,v in b.items() if k not in exclude}
    last = current[-1]
    assert last['stage']=='DISPLAY_NEXT' and last['bytes']=='3'
    measured = int(last['total'])
    delta = measured-linked['cases']['normal']['records'][0][2]
    entry = int(linked['entry_sp'],16)+delta
    trace = json.loads((BASE.parent/'adventure893.json').read_bytes())['transactions']
    ready = [bytes.fromhex('e6000040000003')]
    cases = {}
    for mode in ('normal','data','token','empty'):
        test = FirstBlock(trace,entry,None if mode=='normal' else mode)
        row = replay(src,1,'defer',probe=3,pre_snapshots=ready,game=test)
        assert row['records'][0]==['DISPLAY_NEXT',3,measured]
        prior = linked['cases'][mode]
        assert row['records'][-1]==prior['records'][-1] and test.ops==prior['ops']
        assert row['spi'].count(0x64)==1 and test.first_write is None
        foreground = test.low-test.static_end
        end = 0x0803fff0
        test.cpu.reg_write(UC_ARM_REG_SP,(test.low-104)&~7)
        test.cpu.reg_write(UC_ARM_REG_LR,end|1)
        test.cpu.emu_start(test.systick|1,end,count=50000)
        assert test.cpu.reg_read(UC_ARM_REG_PC)==end
        assert test.first_write is None and test.low>test.static_end
        cases[mode] = dict(stop=row['records'][-1],ops=test.ops,foreground_gap=foreground,
                           injected_SysTick_gap=test.low-test.static_end)
    name = 'NES BOOT 894.nh1'
    machine = Machine(src,bytes(128))
    for marker, geometry in [(name,386),('NES BLOCK 894.nh1',387),('NES BOOT 893.nh1',0)]:
        machine.u.mem_write(0x20012000,marker.encode()+b'\0')
        assert machine.call('marker_geometry',[0x20012000])==geometry
        assert bool(machine.call('nes_menu_diagnostic_marker',[0x20012000]))==bool(geometry)
    boot = replay(src,1,'defer',probe=2,pre_snapshots=ready,game=FirstBlock(trace,entry,None))
    assert boot['frame_entry']==0 and boot['records'][-1]==['PROBE_STOPPED',2,0]
    assert boot['spi'].count(0x64)==1
    marker_zip = WORK/'MMC894-BOOT-MARKER-ONLY.zip'
    with ZipFile(marker_zip,'w') as archive:
        archive.writestr(ZipInfo(name),b'')
    with ZipFile(marker_zip) as archive:
        assert archive.namelist()==[name] and archive.read(name)==b'' and archive.testzip() is None
    return dict(firmware=sha(image),physical_progress_sha256=sha(progress),hardware_last=last,
                reference_progress_sha256=sha(previous),reference_checkpoint_msp=hex(measured-delta),
                hardware_checkpoint_msp=hex(measured),delta_B=delta,calibrated_entry_sp=hex(entry),replay=cases,
                boot_replay=boot['records'],marker_zip_sha256=sha(marker_zip))


if __name__=='__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for arg in ('progress','previous','out'):
        p.add_argument(arg,type=Path)
    a = p.parse_args()
    a.out.write_text(json.dumps(check(a.progress,a.previous),indent=2)+'\n')
