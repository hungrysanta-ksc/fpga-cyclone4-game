# SPDX-License-Identifier: MIT
"""Source-pinned architecture preflight; no new ROM, firmware, FIT or FPS claim.

Reads old/current fitted resources and actual C->65816 packet/ACK fixtures.
Direct cartridge DMA is a hypothetical transport lower bound to WRAM, not a
new implemented endpoint and not permission to DMA VRAM during active video.
"""
from pathlib import Path
import argparse,hashlib,json,math,re

SPI=2_625_000
MASTER=21_477_272

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def fitted(p):
    # Quartus report has non-UTF8 locale bytes; semicolon numeric fields are ASCII.
    text=p.read_bytes().decode('latin1');entities={}
    for line in text.splitlines():
        f=[s.strip() for s in line.split(';')]
        if len(f)>18 and f[1].startswith('|') and 'altsyncram' not in f[-3]:
            entities[f[1]]=dict(logic_cells=int(f[2].split()[0]),memory_bits=int(f[5]),m9k=int(f[6]))
    def number(label):
        match=re.search(r';\s*'+re.escape(label)+r'\s*;\s*([\d,]+) / ([\d,]+)',text)
        assert match,label
        used,total=(int(s.replace(',','')) for s in match.groups())
        return dict(used=used,total=total,free=total-used)
    return dict(le=number('Total logic elements'),lab=number('Total LABs:  partially or completely used'),
                m9k=number('M9Ks'),entities=entities)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--workspace',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();b=a.workspace.resolve();r=b/'repository-nes-milestone';out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
    pins={}
    def pin(p):pins[p.relative_to(b).as_posix()]=sha(p);return p
    oldroot=b/'probes/nes-game164/evidence/asm';newroot=b/'probes/nes-window184-coupled/evidence/route02'
    old=fitted(pin(oldroot/'output_files/board.fit.rpt'));new=fitted(pin(newroot/'output_files/board.fit.rpt'))
    assert [old[k]['used'] for k in ['le','lab','m9k']]==[14711,960,56]
    assert [new[k]['used'] for k in ['le','lab','m9k']]==[13466,939,42]
    # Non-overlapping hierarchy subtrees only; never add parent and child.
    remove=['|nes_native_frame181:native_frame|','|nes_native_fill165:native_fill|',
            '|nes_native_spi165:native_spi|','|nes_sink_bridge165:sink|']
    removed=sum(new['entities'][n]['m9k'] for n in remove)
    oldframe=old['entities']['|nes_game_frame150:framebuffer|']['m9k']
    oldbus=old['entities']['|nes_game_bus151:consumer|']['m9k']
    reversion=new['m9k']['used']-removed+oldframe+oldbus
    assert (removed,oldframe,oldbus,reversion)==(22,38,2,60)
    # Pin deployed source proving clocks/ownership/mapper/caching limitations.
    names=['board.qsf','nes_native_frame181.sv','nes_native_planes165.sv','nes_native_export181.sv',
           'nes_probe.sv','cart_nrom.sv','rtl/nes.v','nes_rom_physical.sv']
    texts={n:pin(newroot/n).read_text(encoding='utf8') for n in names}
    assert '.mapper_flags(64\'d4)' in texts['nes_probe.sv']
    assert '.MMC5           (1\'b0)' in texts['rtl/nes.v']
    assert 'required_tiles[0:8191]' in texts['nes_native_planes165.sv']
    assert 'physical_address[16:4]' in texts['nes_native_planes165.sv']
    assert 'scanline==7 && dot==257' in texts['nes_native_planes165.sv']
    assert 'scanline==232 && dot==1' in texts['nes_native_planes165.sv']
    assert 'COMMIT:if(tx_ready)begin release_frame<=1' in texts['nes_native_export181.sv']
    for n in ['nes_native_runtime165.c','nes_native_video165.c','nes_native_sink165.c','nes_sink_window184.c']:
        pin(b/'probes/nes-paired186/arm01/src'/n)
    pin(r/'tools/build_nes_game164.py');pin(r/'docs/nes-native-commands165-contract.ko.md')
    # Frozen synthetic fixtures, not real scrolling or an end-to-end model.
    case=b/'probes/nes-copy186/evidence/coupled03/inherit';groups={}
    requests=sorted(case.glob('req-*.bin'));assert len(requests)==259
    for p in requests:
        packet=pin(p).read_bytes();ordinal=int(p.stem.split('-')[1]);ack=pin(case/f'ack-{ordinal:04}.bin').read_bytes()
        assert len(packet)>=16 and len(packet)==16+int.from_bytes(packet[12:14],'little')
        assert len(ack)==12 and ack[1]==packet[0] and ack[2:10]==packet[2:10] and ack[10:]==bytes.fromhex('659a')
        assert ack[0]==(1 if packet[0]==3 else 0)
        gen=int.from_bytes(packet[8:10],'little');g=groups.setdefault(gen,dict(requests=0,bytes=0,begin=0,seal=0,copy=0,by_section={}))
        g['requests']+=1;g['bytes']+=len(packet);g['begin']+=packet[0]==1;g['seal']+=packet[0]==3;g['copy']+=packet[0]==6
        key=f'op{packet[0]}_section{packet[1]}';g['by_section'][key]=g['by_section'].get(key,0)+len(packet)
    for g in groups.values():
        assert g['begin']==g['seal']==1
        # E1 request+CRC is unavoidable; omit all status, gaps, compute, decoding.
        g['egress_spi_min_ms']=(g['bytes']+3*g['requests'])*8/SPI*1000
        g['hypothetical_cart_to_wram_dma_min_ms']=g['bytes']*8/MASTER*1000
        g['spi_egress_alone_exceeds_60hz']=g['egress_spi_min_ms']>1000/60
    hw=json.loads(pin(r/'analysis/game186-hardware01-verification.json').read_bytes())['comparison']['current186']
    pixels=256*224;gap_dots=262*341-((232-7)*341+1-257)
    result=dict(kind='architecture187_preflight',scope='Resource accounting and necessary conditions only; no new hardware implementation or timing/FPS signoff.',
       source_pins=pins,resources=dict(old164=old,current186=new,
           direct_add_old_frame_m9k=42+38,remove_native_subtrees=remove,removed_m9k=removed,
           replacement_estimate_m9k=reversion,replacement_scope='Arithmetic estimate using current optimized OAM and old consumer. Not a synthesis result; packing/shared logic/removing other blocks may change it.',
           spare_raw_bits=14*9216,spare_raw_bytes=14*9216//8,frame6_bits=pixels*6,frame6_min_m9k=math.ceil(pixels*6/9216),frame9_min_m9k=math.ceil(pixels*9/9216)),
       rates=dict(spi_hz=SPI,master_hz=MASTER,target_hz=60,spi_total_bytes_per_target_frame=SPI/8/60,
           ideal_cart_dma_bytes_per_second=MASTER/8,raw8_bytes=pixels,raw8_full_dma_min_ms=pixels*8/MASTER*1000,
           raw8_vblanks_with_old_chunk=math.ceil(pixels/5632),old_complete_frame_upper_hz=60/math.ceil(pixels/5632),
           raw6_packed_bytes=pixels*6//8,raw6_dma_min_ms=(pixels*6//8)*8/MASTER*1000,
           vblank_gross_bytes_224_ntsc=(262-225)*1364/8,
           limitations='DMA figures exclude setup/HDMA/refresh/CPU/PPU work. Packed6 is not a SNES native mode. Cartridge-to-WRAM DMA can run outside vblank but halts CPU; VRAM uploads require vblank or blanking.'),
       lease=dict(gap_dots=gap_dots,gap_ms_reference60hz=gap_dots/(262*341)*1000/60,
           scrub_cycles=8192,export_release='transport COMMIT accepted, not SNES display ACK',
           issue='Single capture lifetime must release/scrub before next start or overlap via safe streaming/snapshot. Egress cache alone cannot fix missed source captures.'),
       packet_fixtures=dict(frames=groups,source='Synthetic7 actualC+65816 packet+ACK archive; no shared-clock end-to-end performance; frames are not SMB3 scrolling.',
           direct_model='Only hypothetically replaces delivery of the same packet bytes with prepared cartridge aperture->WRAM DMA. Still needs FPGA producer/transform, buffer lifetime, decoder cost, read timing, coherent bank/ACK and VRAM budget.'),
       hardware186=hw,decision=dict(keep='SNES tile/scroll/OBJ output and accurate FPGA CPU/PPU/APU/mapper',
           change='Do not treat full-scene serial FPGA->SPI->MCU->SPI->SNES as final60fps architecture. Evaluate stable patterns and source-side changes WITH capture overlap and parallel cartridge bulk path before next COPY-only trial.',
           mapper='Currently fixedMMC3/128KiB CHR lookup; MMC4 latch and MMC5 PPU data/ExRAM/audio/state are not automatically supported. Plan mapper-family bitstreams if needed; no fit guarantee.',
           next='Actual scrolling workload paired ingress/egress budget, then bounded parallel aperture/ownership and snapshot prototype under available resources. No extra hardware request or unchanged FIT.'),
       tests=dict(requests_verified=len(requests),ack_tokens_verified=len(requests),generations_verified=len(groups),new_simulation=False,new_firmware=False))
    (out/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(dict(resources={n:result['resources'][n] for n in ['replacement_estimate_m9k','spare_raw_bytes','frame6_min_m9k']},rates=result['rates'],lease=result['lease'],frames=groups),indent=2))
if __name__=='__main__':main()
