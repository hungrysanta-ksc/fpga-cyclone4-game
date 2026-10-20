# SPDX-License-Identifier: MIT
"""Compare whole-board cost and retimed ARM/ROM parser relocation evidence."""
from pathlib import Path
import argparse,collections,csv,hashlib,json,re,sys
from nes_delta231 import BASE,ROOT,sha
from analyze_nes_boundary269 import hierarchy
sys.path.insert(0,str(BASE/'.tools/arm259-python'))
from elftools.elf.elffile import ELFFile


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();b=a.base.resolve();d=a.out.resolve()
    assert not d.exists();d.mkdir(parents=True);pins={}
    def pin(q):pins[str(q)]=sha(q);return q
    def read(q):return json.loads(pin(q).read_text(encoding='utf-8'))
    def loaded(q):
        with pin(q).open('rb') as f:
            e=ELFFile(f)
            return dict(entry=e.header['e_entry'],machine=e.header['e_machine'],
                segments=[dict(address=s['p_vaddr'],memsize=s['p_memsz'],filesize=s['p_filesz'],flags=s['p_flags'],
                               sha256=hashlib.sha256(s.data()).hexdigest())
                          for s in e.iter_segments() if s['p_type']=='PT_LOAD'],
                functions={s.name:[s['st_value'],s['st_size']] for s in e.get_section_by_name('.symtab').iter_symbols()
                           if s['st_info']['type']=='STT_FUNC'})
    def metrics(q):
        r=read(q/'result.json');assert r['passed']
        ev=list(csv.reader(pin(q/'joint-events.csv').open()))
        source={int(x['frame']):x for x in csv.DictReader(pin(q/'cycles.csv').open())}
        arm={x['frame']:x for x in r['ARM']['frames']};rows={}
        for x in ev:
            if x[0]!='frame_done':continue
            f=int(x[1]);c=collections.Counter()
            for e in ev:
                if e[0]=='arm267' and int(e[1])==f:c[int(e[2])]+=1
            sm=int(source[f]['total'])*45.454/1e6;out=int(x[3])/1e9
            rows[f]=dict(source_ms=sm,output_ms=out,serial_ms=sm+out,gap_ms=sm+out-1000/60,
                         E0=c[224],E2=c[226],E1=c[225],E8=c[232],SPI_bytes=arm[f]['SPI_bytes'],
                         instructions=arm[f]['instructions'])
        return r,rows,ev
    refs={'normal':BASE/'probes/nes-joint270/test05','restricted':BASE/'probes/nes-joint270/window01'}
    prior={mode:metrics(q)[1] for mode,q in refs.items()}
    board270=pin(BASE/'probes/nes-joint270/board02/nes_mux260.sv').read_text()
    normalized270=board270.replace(' output wire tile_closed267,\n','').replace(';assign tile_closed267=tiles_closed;',';')
    assert normalized270==pin(refs['normal']/'nes_mux260.sv').read_text()
    rows=[];results={};transactions=[];packet_counts={}
    for variant,mode,name in [('A','normal','test02'),('B','normal','test03'),('B','restricted','window02')]:
        q=b/name;r,m,ev=metrics(q);assert r['frames']==3 and set(m)=={905,906,907};results[name]=r
        assert r['ELF_sha256']==sha(pin(q/'output.elf'))
        assert loaded(q/'output.elf')==loaded(refs[mode]/'output.elf')
        assert r['tb_sha256']==sha(pin(q/'joint266_tb.sv'))
        for n,h in r['rtl_hashes'].items():assert h==sha(pin(q/n))
        for f,x in m.items():
            tx=[t['tx'] for t in read(q/f'arm{f}.json')['transfers'] if t['tx'].startswith('e1')]
            ref=[t['tx'] for t in read(refs[mode]/f'arm{f}.json')['transfers'] if t['tx'].startswith('e1')]
            assert tx==ref,(name,f);packet_counts[f]=len(tx)
            for suffix in ['.records']:
                assert pin(q/f'frame{f}{suffix}').read_bytes()==pin(refs[mode]/f'frame{f}{suffix}').read_bytes()
            rows.append(dict(variant=variant,mode=mode,frame=f,**x,delta270_ms=x['serial_ms']-prior[mode][f]['serial_ms'],
                             delta270_instructions=x['instructions']-prior[mode][f]['instructions'],
                             delta270_E2=x['E2']-prior[mode][f]['E2'],delta270_E8=x['E8']-prior[mode][f]['E8'],
                             delta270_SPI_bytes=x['SPI_bytes']-prior[mode][f]['SPI_bytes']))
        for n in ['CPU-bus.csv','CPU-ordinary.sfc','CPU-packets.hex','nes_plan_batch206.sv','nes_spi270.sv','nes_queue260.sv']:
            assert pin(q/n).read_bytes()==pin(refs[mode]/n).read_bytes()
        previous=[0]*5
        for e in ev:
            if e[0]=='parser272':
                values=list(map(int,e[2:]));diff=[v-old for v,old in zip(values,previous)];previous=values
                assert diff[0]==8*diff[4] and diff[1]==diff[2]
                transactions.append(dict(run=name,frame=int(e[1]),metadata_words=diff[0],body_bytes=diff[1],
                                         read_requests=diff[2],local_events=diff[3],completed_packets=diff[4]))
    areas={};hierarchies={}
    for v,q in [('270',BASE/'probes/nes-joint270/board02'),('A',b/'board01'),('B',b/'board02')]:
        r=read(q/'result.json');assert r['passed']
        summary=pin(q/'output_files/board.map.summary').read_text()
        areas[v]={k:int(re.search(pat+r'\s*:\s*([\d,]+)',summary).group(1).replace(',',''))
                  for k,pat in [('LE','Total logic elements'),('comb','Total combinational functions'),
                                ('FF','Dedicated logic registers'),('RAM_bits','Total memory bits')]}
        h=hierarchy(pin(q/'output_files/board.map.rpt'))
        hierarchies[v]={k:h[k] for k in ['|nes_core257:encoder|','|nes_output260:flow|']+
                       ([] if v=='270' else ['|nes_parser272:parser272|'])}
        if v!='270':
            run=b/('test02' if v=='A' else 'test03')
            for n in ['nes_mux260.sv','nes_parser272.sv','nes_core257.sv','nes_joint257.sv']:
                left=pin(q/n).read_text();right=pin(run/n).read_text()
                if n=='nes_mux260.sv':
                    # The board exports the existing tile-closed flag; the TB
                    # reads it hierarchically. Both270 and272 retain this pair.
                    assert left.count(' output wire tile_closed267,\n')==1
                    assert left.count(';assign tile_closed267=tiles_closed;')==1
                    left=left.replace(' output wire tile_closed267,\n','').replace(';assign tile_closed267=tiles_closed;',';')
                assert left==right,n
            flow=pin(q/'nes_mux260.sv').read_text()
            assert 'event264(' not in flow and 'manifest_at' not in flow and 'opos' not in flow
            assert '#(.WIDTH(24)) consumed' in flow and '#(.WIDTH(8)) receipt' in flow
            assert 'state==NORMAL?asyn[7:0]:parser_address' in flow
    g=read(b/'guards01/result.json');assert g['passed'] and g['guards']==list(range(1,43))
    repro=read(b/'reproduction01/result.json')
    assert repro['passed'] and repro['script_sha256']==sha(pin(ROOT/'tools/nes_joint272.py'))
    for n in ['nes_mux260.sv','nes_parser272.sv','nes_core257.sv','nes_joint257.sv']:
        assert pin(b/'guards01'/n).read_bytes()==pin(b/'test03'/n).read_bytes()==pin(b/'window02'/n).read_bytes()
    # Exclusive host flow, standalone parser, and core are disjoint.
    region={v:h['|nes_core257:encoder|']['comb']+h['|nes_output260:flow|']['own_comb']+
            (0 if v=='270' else h['|nes_parser272:parser272|']['comb']) for v,h in hierarchies.items()}
    with (d/'costs.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
    result=dict(passed=True,stage='NES272',selected=['test02','test03','window02','guards01','board01','board02'],
        new_frame_executions=9,new_full71=False,prior71='analysis/joint270-verification.json',
        warm907=[x for x in rows if x['frame']==907],transactions=transactions,E1_packets_per_frame=packet_counts,
        MAP=dict(areas=areas,deltaA270={k:areas['A'][k]-areas['270'][k] for k in areas['A']},
                 deltaB270={k:areas['B'][k]-areas['270'][k] for k in areas['B']},
                 deltaBA={k:areas['B'][k]-areas['A'][k] for k in areas['B']},
                 comb_deficit={v:x['comb']-15408 for v,x in areas.items()},FIT=False,STA=False),
        hierarchy=hierarchies,disjoint_core_host_parser_comb=region,reference_target_comb=2382,
        ARM_stack={n:r['ARM']['stack_observed'] for n,r in results.items()},
        ARM_loaded_image_and_function_addresses=loaded(b/'test03/output.elf'),
        ELF_comparison='Each raw ELF hash is pinned separately; compare PT_LOAD bytes/addresses/sizes/flags, entry point and all function symbols. Raw ELF containers are not byte-identical.',
        guards=g['guards'],current_generator_exact_RTL_reproduction=repro,RAM_added_bits=0,source_register_context_bits_shared=120,
        host_header_and_typed_map_parser_retained=True,phase_RAM_chunk_buffer=False,
        board_test_difference='Existing270 board-only tile_closed267 output/continuous wire export; exact raw files pinned, only these two declarations normalized for comparison.',
        integrated_core_parser_single_FSM=False,full_path_ms=None,P2_selected=False,physical60fps=False,
        decision='Reject both slices for adoption: NES interpreter relocation and source register reuse do not recover whole-board combinational area.',
        limitations=['Only905..907 newly executed, not heavy954 or a new71-frame sweep.',
                     'CPI1/service IRQ bodies, not actual MCU cycles/full RUN/NVIC.',
                     '65816 ordinary bus traces, modeled map/tile/final display and synthetic ROM contenders.',
                     'Host admission and typed-map parser retained; not the complete271 removal boundary.',
                     'No phase RAM header/chunk buffering or single source/parser/receipt FSM proof.',
                     'Source input context sharing is phase gated; no independent endpoint-reset claim.'],
        input_hashes=pins,script_sha256=sha(Path(__file__)))
    (d/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:result[k] for k in ['passed','warm907','MAP','disjoint_core_host_parser_comb','transactions']},ensure_ascii=False,indent=2))


if __name__=='__main__':main()
