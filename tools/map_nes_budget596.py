"""Price named 595 deletions in isolated Quartus Lite region copies. Not functional builds."""
import argparse
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from check_nes_region595 import ROOT, sources, sha


def replace(body, old, new, count=1):
    assert body.count(old) == count, old
    return body.replace(old, new)


def variants(original):
    # Only the indication crosses in the mailbox. No lifetime interlock or
    # physical bundled-data constraints are priced by this diagnostic.
    cdc = replace(original, '.WIDTH(135)', '.WIDTH(1)')
    cdc = replace(cdc, '.src_data(host_word)', ".src_data(1'b1)")
    cdc = replace(cdc, '.dst_data(event_word)', '.dst_data()')
    cdc = replace(cdc, ' wire seal_ready', ' assign event_word=host_word;\n wire seal_ready')

    def address_crc(body):
        body = replace(body, 'map_crc,stream_crc,', 'map_crc,')
        body = replace(body, ':stream_crc;', ':map_crc;')
        body = replace(body, 'stream_crc<=map_crc;', '')
        body = replace(body, 'if(kind==0)begin map_crc<=crc16(map_crc,value[7:0]);digest<=crc32(digest,value[7:0]);end\n      else stream_crc<=crc16(stream_crc,value[7:0]);',
                       'map_crc<=crc16(map_crc,value[7:0]);if(kind==0)digest<=crc32(digest,value[7:0]);')
        body = replace(body, 'cursor,row_base,limit', 'cursor,limit')
        body = replace(body, 'kind==0 ? row_base+word_at : cursor', 'cursor')
        body = replace(body, 'row_base<=row_base+33;state<=phase', 'state<=phase')
        body = replace(body, 'row_base<=row_base+33;\n     if(addr', '\n     if(addr')
        body = replace(body, "if(kind==0)begin word_at<=word_at+1'b1;", "if(kind==0)begin cursor<=cursor+1'b1;word_at<=word_at+1'b1;")
        return body.replace('row_base','cursor')

    return {'cdc': cdc, 'crc_address': address_crc(original), 'joint': address_crc(cdc)}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('out', type=Path)
    args = p.parse_args()
    results = {}
    pins = json.loads((ROOT/'analysis/region595-verification.json').read_bytes())
    for name, digest in pins['RTL'].items():
        assert sha(ROOT/'rtl'/name) == digest
    args.out.mkdir(parents=True, exist_ok=False)
    for name, body in variants((ROOT/'rtl/nes_region595.sv').read_text()).items():
        dest = args.out/name
        dest.mkdir()
        with tempfile.TemporaryDirectory(prefix='nes596map-') as tmp:
            d = Path(tmp)
            sources(d)
            (d/'nes_region595.sv').write_bytes(body.encode())
            (d/'region.qpf').write_text('PROJECT_REVISION = "region"\n')
            qsf = ['set_global_assignment -name FAMILY "Cyclone IV E"',
                   'set_global_assignment -name DEVICE EP4CE15F17C8',
                   'set_global_assignment -name TOP_LEVEL_ENTITY nes_region595',
                   'set_global_assignment -name PROJECT_OUTPUT_DIRECTORY output_files']
            qsf += ['set_global_assignment -name SYSTEMVERILOG_FILE '+f.name for f in d.glob('*.sv')]
            (d/'region.qsf').write_text('\n'.join(qsf)+'\n')
            with (dest/'map.log').open('wb') as log:
                subprocess.run(['C:/altera_lite/25.1std/quartus/bin64/quartus_map.exe','region'],
                               cwd=d, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=600)
            for ext in ('summary','rpt'):
                shutil.copy(d/'output_files'/('region.map.'+ext), dest)
            summary = (dest/'region.map.summary').read_text()
            assert 'Successful' in summary and 'Lite Edition' in summary
            labels = ('Total logic elements','Total combinational functions','Dedicated logic registers','Total memory bits')
            costs = [int(re.search(r'^\s*'+k+r'\s*:\s*([\d,]+)',summary,re.M)[1].replace(',','')) for k in labels]
            results[name] = dict(zip(('LE','comb','FF','RAM_bits'),costs))
            results[name].update(RTL=sha(d/'nes_region595.sv'),report=sha(dest/'region.map.rpt'))
            print(name, costs, flush=True)
    (args.out/'result.json').write_text(json.dumps(results,indent=2)+'\n')


if __name__ == '__main__':
    main()
