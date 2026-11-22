"""Compare slot-zero publication against MMC915 on identical inputs and clocks."""
import argparse
import json
from pathlib import Path

from analyze_nes_issue917 import MASTER, coverage, summarize
from nes_first918 import ARM, sha, work


def tile_bytes(directory):
    writes = {}
    for line in (directory/'packets.jsonl').read_text().splitlines():
        _, _, head, bulk = json.loads(line)
        packet = bytes.fromhex(head)
        if packet[0] != 7:
            continue
        gen = int.from_bytes(packet[8:10], 'little')
        offset = int.from_bytes(packet[10:12], 'little')
        payload = bytes.fromhex(bulk)
        assert len(payload) == int.from_bytes(packet[14:16], 'little')
        for index, value in enumerate(payload, offset):
            key = (gen, packet[1], index)
            assert key not in writes
            writes[key] = value
    return writes


def analyze(temp):
    output = {}
    for phase in (1, 2):
        for cache in ('warm', 'cold'):
            def folder(tag):
                return temp/f'nes-tile821-obj-jointmirror-p{phase}-{tag}-{cache}-pair'
            baseline = folder('915stepfinal')
            ref, old, ref_time = summarize(baseline, ARM)
            original = tile_bytes(baseline)
            rows = output[f'{phase}-{cache}'] = {}
            for mode in ('baseline', 'pair', 'early', 'single', 'joined'):
                arm = ARM if mode == 'baseline' else work(mode)
                run = baseline if mode == 'baseline' else folder('918'+mode)
                actual, packets, t = summarize(run, arm)
                assert ref['client'] == actual['client'] and ref['parameters'] == actual['parameters']
                assert tile_bytes(run) == original
                for g in old:
                    for pattern in ('frame-{}.rgb', 'map-{}.bin', 'colors636-{}.bin'):
                        name = pattern.format(g)
                        assert sha(run/name) == sha(baseline/name)
                    assert [v for v in old[g] if v[0] in (1,3)] == [v for v in packets[g] if v[0] in (1,3)]
                for g in ref['frames']:
                    assert ref['frames'][g]['section5_hash'] == actual['frames'][g]['section5_hash']
                def ahead(before, after):
                    return round((before-after)*1000/MASTER, 4)
                first = t['jobs'][0]
                assert first['bytes'] == 16 and first['kind'] == 0
                def boundaries(timing):
                    return {k:[v[0] for v in timing[k]] for k in ('palette','OAM','section5','tile','E9')}
                rows[mode] = dict(
                    flash=(arm/'link/src/obj-nes-100/firmware.stm').stat().st_size,
                    first_E9=t['E9'][0], first_ready=round(first['producer']), first_observed=round(first['observed']),
                    first_accept=t['tile'][0], pre908=actual['preDMA'][908], seal=t['SEAL'],
                    accept908=boundaries(t), producer908=t['jobs'],
                    upload=t['upload'], upload_gain_ms=ahead(ref_time['upload'][0], t['upload'][0]),
                    reveal=t['reveal'], intervals=actual['intervals'], ack912=actual['final_ACK'],
                    ack_gain_ms=ahead(ref['final_ACK'],actual['final_ACK']), pre912=actual['preDMA'][912],
                    coverage912=len(coverage(actual['preDMA'][912])),
                    same_coverage912=coverage(actual['preDMA'][912]).keys()==coverage(ref['preDMA'][912]).keys())
    guards={}
    def read(path):
        return json.loads(path.read_bytes())
    for mode in ('pair','early','single','joined'):
        arm=work(mode)
        digest=sha(arm/'link/src/obj-nes-100/firmware.stm')
        proof=arm/'proof'
        assert all(read(proof/f)['firmware']==digest for f in ('timer.json','loader.json','menu.json'))
        assert read(proof/'timer.json')['passed'] and read(proof/'menu.json')['rows']['normal']['released']
        base=read(proof/'base/result.json')
        assert base['firmware_sha256']==digest and base['safe_return']
        rx=read(proof/'sram.json')['cases']
        assert len(rx['normal']['d0_sites'])==4 and rx['normal']['checked_retire'] and not rx['bad-crc']['checked_retire']
        for test,code in [('stop',228),('bad-seal',224)]:
            assert read(arm/(test+'.json'))==dict(commits=4,status=code)
        guards[mode]=dict(sha256=digest,SRAM_D0_sites=4,CRC_reject=True,STOP=228,bad_SEAL=224,base_menu=True)
    rtl=temp/'nes-first918-questa'
    checks={}
    for filename,marker in [('port918.log','PASS914'),('stop918.log','PASS918')]+[
        (f'trace-{g}-{p}-{cache}.log','PASS914 trace') for g in (908,912) for p in (1,2) for cache in ('cold','warm')]:
        lines=(rtl/filename).read_text(errors='replace').splitlines()
        checks[filename]=dict(result=next(line.strip('# ') for line in lines if marker in line),
                              E8=next((line.strip('# ') for line in lines if 'E8914 compared=' in line),None))
    return dict(cases=output,firmware=guards,single_RTL=checks)


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('temp',type=Path)
    parser.add_argument('output',type=Path)
    args=parser.parse_args()
    args.output.write_text(json.dumps(analyze(args.temp),indent=2)+'\n',encoding='utf8')
