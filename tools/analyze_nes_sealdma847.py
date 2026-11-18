"""Reconcile SEAL validation, scoped map DMA and the remaining blank budget."""
import json
from pathlib import Path
from analyze_nes_dma845 import tail
from analyze_nes_section841 import folder, opening, window, point
from nes_sealdma847 import OUT, REFERENCE, CLIENT, arm


def read(p):return json.loads(p.read_bytes())


def measured(p,test):
    f=folder(p,'847'+test);ref=folder(p,'832base')
    start=read(Path('analysis/section841-results.json'))['phases'][str(p)]['VB52_start']
    cutoff=start+22*1364
    d=tail(f,ref,cutoff)
    rows=[r for r in window(f) if r['g']==910]
    seal=[r for r in rows if r['op']==3]
    stages={k:next(r for r in seal if r['event']==k) for k in
            ('load','seal','coverage212','upload165_entry','wait169')}
    semantic=next((r for r in seal if r['event']=='validate181'),None)
    proof=[]
    if semantic is None:
        assert test=='rawfixed'
        proof=[s for s in (f/'admission838.txt').read_text().splitlines() if s.startswith('910 ')]
        assert any(' reuse838 ' in s for s in proof)
    else:stages['validate181']=semantic
    checked,=[int(v.split()[2]) for v in (f/'seal847.txt').read_text().splitlines() if v.startswith('910 checked ')]
    dma=list(zip((r for r in rows if r['event']=='ppu_dma'),
                 (r for r in rows if r['event']=='ppu_last'),strict=True))
    scoped=[(a,b) for a,b in dma if checked<=a['clock']<b['clock']<stages['upload165_entry']['clock']]
    assert all(a['value']==704 and a['frame']==b['frame']==52 and b['line']<=255 for a,b in scoped)
    if test!='rawfixed':assert len(scoped)==1
    before=[a['value'] for a,b in dma if b['frame']==51]
    if test=='rawfixed':assert before==[64,64,64,768]
    remaining=sum(a['value'] for a,b in dma if a['clock']>=checked)
    semantic_start=semantic['clock'] if semantic else stages['coverage212']['clock']
    elapsed=dict(header_identity_and_proof=semantic_start-stages['load']['clock'],
                 semantic=stages['coverage212']['clock']-semantic_start,
                 coverage_and_admission=checked-stages['coverage212']['clock'],
                 scoped_DMA_and_dispatch=stages['upload165_entry']['clock']-checked,
                 upload_preparation=stages['wait169']['clock']-stages['upload165_entry']['clock'])
    assert sum(elapsed.values())==stages['wait169']['clock']-stages['load']['clock']
    j=read(f/'joint.json')
    assert j['firmware_SHA256']==arm.base.section.sha(arm.link('queued')/'src/obj-nes-100/firmware.stm')
    assert j['client_SHA256']==arm.base.section.sha((CLIENT if test=='boot' else REFERENCE)/'sink165.sfc')
    d.update(stages={k:point(v) for k,v in stages.items()},checked=checked,stage_clocks=elapsed,prior_semantic_proof=proof,
             stage_ms={k:v/(236250000/11/1000) for k,v in elapsed.items()},
             scoped_DMA=[dict(bytes=a['value'],start=point(a),end=point(b)) for a,b in scoped],
             remaining_at_checked_B=remaining,
             ideal_DMA_only_late_clocks=checked+8*remaining-cutoff,
             ideal_DMA_only_late_ms=(checked+8*remaining-cutoff)/(236250000/11/1000),
             payload_B=j['wire_B']['0xe1'],ARM_stack_low=j['observed_stack_low'],
             receiver_observed_stack_B=j['observed_stack_B'],
             ROM_SHA256=j['client_SHA256'],
             injected_body_SHA256=arm.base.section.sha((OUT/'client-raw' if test=='rawfixed' else CLIENT)/'body.bin') if test!='boot' else None)
    return d


def analyze():
    previous=read(Path('analysis/palette846-results.json'))
    phases={}
    for p in (1,2):
        cases={t:measured(p,t) for t in ('fixed','boot','rawfixed')}
        for t,d in cases.items():
            prior=previous['phases'][str(p)]['fixed' if t=='rawfixed' else 'boot']['queued']
            d['ACK_delta_846queued']=d['ACK']-prior['ACK']
            assert d['total']==16 and d['display2576'][1]==48
        early=opening(folder(p,'847opening',True),folder(p,'823826',True))
        assert early['latch'][0]==(245 if p==1 else 246)
        phases[p]=dict(cases=cases,opening=early,opening_245_pass=early['latch'][0]<=245)
    guards={}
    for fault in ('stop','coverage','identity','table'):
        f=folder(1,'847'+fault);rows=window(f)
        assert [r['g'] for r in rows if r['event']=='reveal']==list(range(905,910))
        bad=[r for r in rows if r['event']=='ack' and r['value']>=224]
        assert [(r['g'],r['op'],r['value']) for r in bad]==[(910,3,228 if fault=='stop' else 224)]
        assert 'PASS847 '+fault in (OUT/(fault+'-p1.log')).read_text()
        if fault=='stop':
            tick=int((f/'stop847.txt').read_text())
            assert not any(r['clock']>=tick and r['event'] in ('ppu_dma','ppu_last','reveal') for r in rows)
            guards[fault]=dict(injected=tick,ACK=point(bad[0]))
        else:
            assert not (f/'seal847.txt').read_text().strip()
            guards[fault]=dict(ACK=point(bad[0]),checked_scope_reached=False)
    fw=arm.link('queued')/'src/obj-nes-100/firmware.stm'
    menu=read(arm.OUT/'menu-queued.json');recovery=read(arm.OUT/'base-queued/result.json')
    assert menu['firmware']==recovery['firmware_sha256']==arm.base.section.sha(fw)
    assert menu['rows']['normal']['released'] and recovery['base_restored'] and recovery['safe_return']
    return dict(phases=phases,guards=guards,
        cost=dict(ARM_Flash_B=fw.stat().st_size,ARM_limit_B=212992,
                  receiver=read(CLIENT/'cost.json'),raw_receiver=read((OUT/'client-raw')/'cost.json')),
        unchanged_ARM_menu_base_evidence='nes-palette846/menu-queued.json and base-queued/result.json; modeled IO, not physical',
        FPGA='Unchanged; no new Quartus FIT/STA. No circuit savings claimed.',
        verdict='Not selected: intervals remain 16; boot final ACK remains later than MMC826; opening phase 2 slips to line 246; Flash and ROM exceed limits.',
        scope='Actual linked M4/65816; modeled SPI/IRQ/ROM competition. Fixed swaps receiver only after 2576 ACK. Raw fixed retains 192B early DMA. Ideal eight-clocks-per-byte bound excludes all setup/refresh/checks, so cannot be used as an achievable schedule.',
        trace_note='Initial non-raw runs wrote an unused fourth map trace field from WRAM 4305. Analysis ignores it; DMA sizes come from actual PPU write traces. Later trace uses channel register shadow.')


if __name__=='__main__':
    data=analyze()
    Path('analysis/sealdma847-results.json').write_text(json.dumps(data,indent=2)+'\n',newline='\n')
    print('PASS847 two-phase timing, payload/RGB, early raw, opening, four rejection guards; candidate not selected')
