"""Check linked scheduling, byte ranges, real CHR outputs and full board timing separately."""
import csv
import json
import math
import re
import sys
from pathlib import Path

from analyze_nes_deadline947 import Calendar, MASTER, coverage, directory, inspect, read, sha
from analyze_nes_input949 import timing
from prepare_nes_trial950 import RELEASE, ROM
from test_nes_banks557 import host_after

ROOT = Path(__file__).resolve().parents[1]
VARIANTS = ('retain','empty','neighbor','coldneighbor','banked')


def logtext(path):
    raw = path.read_bytes()
    return raw.decode('utf-16' if raw[:2] in (b'\xff\xfe', b'\xfe\xff') else 'utf-8', errors='replace')


def board_cost(path):
    out = path/'output_files'
    if not (out/'board.sta.summary').is_file():
        return dict(fit=False, last_fitter_lines=logtext(path/'fit.log').splitlines()[-8:])
    rpt = logtext(out/'board.fit.rpt')
    fit = logtext(out/'board.fit.summary')
    sta = logtext(out/'board.sta.summary')
    match = lambda pattern, text: int(re.search(pattern,text).group(1).replace(',',''))
    slacks = {}
    for kind,value in re.findall(r"Type\s*:.*?Model (Setup|Hold|Recovery|Removal|Minimum Pulse Width) [^\n]+\s+Slack\s*:\s*([-\d.]+)",sta):
        slacks[kind] = min(float(value),slacks.get(kind,float('inf')))
    assert len(slacks)==5 and 'Fitter Status : Successful' in fit
    return dict(fit=True,LE=match(r'Total logic elements\s*:\s*([\d,]+)',fit),
                LAB=match(r'Total LABs:\s+partially or completely used\s*;\s*(\d+)',rpt),
                M9K=match(r'; M9Ks\s*;\s*(\d+)',rpt),slack_ns=slacks,
                memory_bits=match(r'Total memory bits\s*:\s*([\d,]+)',fit),
                reports={f:sha(out/f) for f in ('board.fit.rpt','board.sta.rpt','board.sof')})


def port_log(log):
    s = logtext(log)
    polls = re.search(r'E8914 compared=(\d+) different=(\d+)',s)
    chunks = re.search(r'PASS914 trace chunks=(\d+) bytes=(\d+) hits=(\d+) grants=(\d+)',s)
    published = [[int(x) for x in row] for row in re.findall(r'PUB914 token=(\d+) bytes=(\d+) at=(\d+)',s)]
    error = re.search(r'\*\* Fatal: ([^\r\n]+)',s)
    reads=[[int(edge),int(address)//16,int(address)%16] for edge,address in
           re.findall(r'ROM914 edge=(\d+) spec=0 addr=(\d+)',s)]
    mismatches=re.findall(r'E8914 difference [^\n\r]+',s)
    return dict(first_foreground_read=reads[:1],first_E8_mismatch=mismatches[:1],
                log=sha(log),polls=list(map(int,polls.groups())) if polls else None,
                chunks_bytes_hits_grants=list(map(int,chunks.groups())) if chunks else None,
                error=error[1] if error else None, published=published)


def analyze(temp):
    ref = read(ROOT/'analysis/header950-results.json')['cases']
    cal = Calendar(temp/'nes-service509-rom03')
    proof = read(RELEASE/'safety950.json')
    assert proof['firmware']==sha(RELEASE/'link/src/obj-nes-100/firmware.stm')
    assert proof['consumer']==sha(ROM/'sink165.sfc')
    assert proof['menu'] and proof['CRC_rejected'] and proof['SRAM_D0_sites']==4
    assert read(RELEASE/'proof/base/result.json')['base_restored']
    out = dict(physical=False, master_Hz=MASTER, same_link_proof=proof,variants={})
    for variant in ('board',*VARIANTS):
        project = (temp/'nes-board950/board950' if variant=='board' else
                   (temp if variant=='retain' else temp/f'nes-951{variant}')/'nes-trial816-board951')
        tag = '950board' if variant=='board' else '951'+variant
        rows = {}
        v = out['variants'][variant] = dict(board=board_cost(project),cases=rows)
        for guard,marker in [('guards951.log','PASS914 checked'),('row951.log','PASS951 lease')]:
            gp=project/guard
            if gp.exists():
                v[guard]=dict(passed=marker in logtext(gp),sha256=sha(gp))
        for cache in ('warm','cold'):
            for phase in (1,2):
                case=cache+str(phase)
                d=directory(temp,phase,tag,cache)
                m,q=inspect(d,RELEASE,cal)
                refm,refq=inspect(directory(temp,phase,'950bound',cache),RELEASE.parent/'bound',cal)
                assert all(q[k]==refq[k] for k in ('map','colors','RGB','sections','tiles'))
                refcase=ref[case]['bound']
                margin=refcase['final_D2']+refcase['capture_line_margin']-m['capture_D2']
                gain=refcase['final_ACK']+refcase['ACK_advance_vs935']-m['final_ACK']
                def prior(m):
                    return coverage([p for p in m['preDMA'] if p[3]==m['stages'][912]['frame']-1])
                blocks=timing(d)['returned_before_show']
                same=prior(m).keys()==prior(refm).keys()
                r=rows[case]=dict(blocks=blocks,margin_us=round(margin*1e6/MASTER,3),
                    prior_B=m['prior_blank_B'],same_prior_coverage=same,tail_grant=m['tail_grant'],
                    gaps=m['gaps'],intervals=m['total'],ack912=m['final_ACK'],gain_vs935_ms=round(gain*1000/MASTER,6),
                    stage909=m['stages'][909],stage912=m['stages'][912],joint=sha(d/'joint.json'),
                    linked_target=blocks==17 and margin>=0 and (cache=='warm' or (same and m['prior_blank_B']==496 and m['tail_grant'])) and
                                  m['total']==(13 if cache=='warm' else 14) and gain>0,rtl={})
                dirs=[(g,d if g==912 else d/f'gen{g}') for g in range(905,913)]
                for gen,f in dirs:
                    for log in sorted(f.glob('port951*.log')):
                        r['rtl'].setdefault(gen,{})[log.stem]=port_log(log)
    for phase in (1,2):
        d=directory(temp,phase,'951banked','cold')
        case=out['variants']['banked']['cases'][f'cold{phase}']
        rtl=case['rtl'].get(912,{}).get('port951-banked',{})
        if not rtl.get('polls'):
            continue
        # Actual first newly available 288B token in a poll modeled as empty.
        mismatch=rtl['first_E8_mismatch'][0]
        edge=int(re.search(r'edge=(\d+) token=5/0',mismatch).group(1))
        origin=int((d/'origin914.txt').read_text())
        events=read(d/'events.json')
        poll=next(e for e in events if e.get('generation')==912 and e.get('opcode')=='0xe8' and
                  round(host_after(e['start']+7.5*MASTER/2625000,3)-origin)==edge)
        beam=list(csv.DictReader((d/'window.csv').read_text().splitlines()))
        last=next(w for w in reversed(beam) if w['g']=='912' and w['event']=='ppu_last' and
                  int(w['frame'])==case['stage912']['frame']-1)
        # PPU horizontal position is unknown in this record. Counting ALL of
        # the sampled scanline makes this an upper bound on time left.
        cutoff_upper=int(last['clock'])+(253-int(last['line']))*341*4
        available=math.floor(cutoff_upper-poll['clock'])
        case['earlier_RTL_token5']=dict(sample=origin+edge,E8_end=round(poll['clock']),
            cutoff_upper_clock=cutoff_upper,remaining_upper_clocks=available,
            DMA288_min_clocks=288*8,minimum_shortfall_clocks=288*8-available)
        assert 0<available<288*8
    rows=read(directory(temp,1,'950release','cold')/'pages933.json')['hits']
    origins={}
    for g,address,producer,_,_ in rows:
        if g==912:
            key=str(address//16)
            if key not in origins:
                origins[key]=dict(generation=producer,rows=[])
            assert origins[key]['generation']==producer
            origins[key]['rows'].append(address%16)
    out['page_hits_in_933_model']=origins
    for phase in (1,2):
        d=directory(temp,phase,'951idle','cold')
        if not (d/'verified905.json').exists():
            continue
        m,q=inspect(d,RELEASE,cal)
        _,expected=inspect(directory(temp,phase,'950board','cold'),RELEASE,cal)
        assert all(q[k]==expected[k] for k in ('map','colors','RGB','sections','tiles'))
        out.setdefault('idle_page_sensitivity_only',{})[phase]=dict(
            blocks=timing(d)['returned_before_show'],intervals=m['total'],prior_B=m['prior_blank_B'],
            ack912=m['final_ACK'],grants=len(read(d/'idle951.json')),joint=sha(d/'joint.json'))
    return out


if __name__=='__main__':
    result=analyze(Path(sys.argv[1]))
    (ROOT/'analysis/chr951-results.json').write_text(json.dumps(result,indent=2)+'\n',newline='\n')
    for name,v in result['variants'].items():
        print(name,{case:[r['blocks'],r['margin_us'],r['prior_B'],r['intervals'],r['gain_vs935_ms']] for case,r in v['cases'].items()})
        print({k:v['board'].get(k) for k in ('LE','LAB','M9K','slack_ns')})
