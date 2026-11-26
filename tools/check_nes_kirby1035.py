"""Compare printed board gates with real exporter, record CDC and CRC-checked captured SPI blocks."""
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

from prepare_nes_kirby1035 import BASE

ROOT = Path(__file__).resolve().parents[1]
OUT = BASE.parents[1]/'nes-kirby1035'
BIN = Path('C:/altera_standard/25.1std/questa_fse/win64')


def command(tmp, tag, program, *args):
    path = OUT/(tag+'.log')
    with path.open('wb') as log:
        completed = subprocess.run([BIN/(program+'.exe'), *args], cwd=tmp, stdout=log,
                                   stderr=subprocess.STDOUT, timeout=180)
    output = path.read_text(errors='replace')
    if completed.returncode or '** Fatal' in output or '** Error' in output:
        raise RuntimeError(path)
    return output


def check(tmp):
    (fixture,) = BASE.parents[1].glob('nes-kirby1023/replay-*/frame3570.d1')
    blocks = [bytes.fromhex(line) for line in fixture.read_text().splitlines()]
    assert len(blocks)==18 and all(2 < len(b) <= 256 for b in blocks)
    (tmp/'golden.hex').write_text(''.join(f'@{i*256:x}\n'+b.hex(' ')+'\n' for i,b in enumerate(blocks)))
    (tmp/'lengths.hex').write_text(''.join(f'{len(b):x}\n' for b in blocks))
    shutil.copyfile(fixture.with_suffix('.query'),tmp/'frame.query')
    files = ['nes_capture_lease201','nes_native_mailbox165','nes_native_export203','nes_native_spi165','nes_geometry_sender653']
    shutil.copy(ROOT/'tests/nes-functional/spi200_bus.svh', tmp)
    tb = ROOT/'tests/nes-functional/kirby1035_export_tb.sv'
    command(tmp,'lib','vlib','work')
    report = {'fixture_sha256':hashlib.sha256(fixture.read_bytes()).hexdigest(),'first_block_payload_B':len(blocks[0])-2,
              'query_sha256':hashlib.sha256((tmp/'frame.query').read_bytes()).hexdigest(),
              'wire_payload_and_crc_B':sum(map(len,blocks)), 'cases':[]}
    for label, board in [('baseline',BASE),('early',OUT/'board'),('instrumented',OUT/'board-times')]:
        top = (board/'nes_live_joint.sv').read_text().split('native_export(',1)[1].split('));',1)[0]
        gates = []
        for port, wire in [('enable','run_gate'),('start_permitted','start_gate'),('ack_accept','commit_gate')]:
            (expr,) = re.findall(r'\.'+port+r'\(([^\n]*?)\),\.',top.replace(',\n',',.\n'))
            gates.append(f'wire {wire}={expr};')
        (tmp/'gate1035.svh').write_text('\n'.join(gates))
        sources=files+(['nes_input_times1035'] if label=='instrumented' else [])
        for f in sources:
            shutil.copy(board/(f+'.sv'),tmp)
        shutil.copy(tb,tmp)
        defines=['+define+INTERVAL1035'] if label=='instrumented' else []
        command(tmp,label+'-compile','vlog','-sv',*defines,*[f+'.sv' for f in sources],tb.name)
        for phase,hold,late,mode in [(1,11420,0,0),(2,16340,0,0),(1,11420,1,0),(2,0,0,0),(1,11420,0,1),(2,16340,0,2)]:
            tag=f'{label}-{phase}-{hold}-{late}-{mode}'
            output=command(tmp,tag,'vsim','-c','work.kirby1035_export_tb',f'+PHASE={phase}',f'+HOLD={hold}',
                           f'+LATE={late}',f'+MODE={mode}','-do','onbreak {quit -code 1}; onerror {quit -code 1}; run -all; quit -code 0')
            (result,)=re.findall(r'^# (PASS1035[^\n]*)',output,re.M)
            report['cases'].append(dict(board=label,phase=phase,imposed_plan_open_us=hold,
                                        geometry_late=bool(late),mode=mode,result=result))
    return report


if __name__=='__main__':
    with TemporaryDirectory(prefix='kirby1035-') as work:
        result=check(Path(work))
    (OUT/'comparison.json').write_text(json.dumps(result,indent=2)+'\n')
