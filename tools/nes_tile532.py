# SPDX-License-Identifier: MIT
"""Build accepted-tile selectors with 64/128-byte map grants and checked cross-map tile merging."""
import argparse
import inspect
import json
from pathlib import Path
from unittest.mock import patch
import nes_dirty212
import nes_prefix523 as prefix
from nes_idle524 import arbitrate, packet
from nes_map526 import LateMapRows
from nes_raw506 import once


class SmallTiles(LateMapRows):
    map_last_line = 254

    @classmethod
    def map_length(cls,c,label):
        c.emit(0xa0,64,0)
        if cls.map_chunk==128:
            c.long(0xbf,0x7e4004);c.emit(0xc9,128,0);c.branch(0x90,label)
            c.emit(0xa0,128,0);c.label(label)

    @classmethod
    def select(cls,c):
        # X indexes the accepted 8-byte list, Y is the byte count for this DMA.
        # A tail tile may be reopened only until its synchronous transfer retires.
        c.absolute(0xae,0x1252);c.absolute(0xec,0x1250);c.branch(0xf0,'empty526')
        c.long(0xbf,0x7e4000);c.emit(0x29,0,0x70,0xc9,0,0x50);c.branch(0xf0,'tail532')
        c.long(0xbf,0x7e4004);c.emit(0xc9,161,0);c.branch(0xb0,'tail532')
        c.emit(0xa8);c.branch(0x80,'selected526')
        c.label('tail532');c.absolute(0xad,0x1250);c.emit(0x38,0xe9,8,0,0xaa)
        c.long(0xbf,0x7e4000);c.emit(0x29,0,0x70,0xc9,0,0x50);c.branch(0xf0,'row526')
        c.absolute(0xec,0x1252);c.branch(0xf0,'empty526')
        c.absolute(0xae,0x1252)
        c.long(0xbf,0x7e4000);c.emit(0x29,0,0x70,0xc9,0,0x50);c.branch(0xf0,'row526')
        c.long(0xbf,0x7e4004);c.emit(0xc9,1,8);c.branch(0xb0,'empty526')
        c.emit(0xa8);c.branch(0x80,'selected526')
        c.label('empty526');c.jump('skip523')
        c.label('row526');cls.map_length(c,'normal_length532')
        c.label('selected526')

    @classmethod
    def late_beam(cls,c,defer):
        c.emit(0xc9,233);c.branch(0x90,'map_beam_ok526')
        c.emit(0xc9,cls.map_last_line+1);c.branch(0xb0,defer)
        c.long(0xbf,0x7e4001);c.emit(0x29,0x70,0xc9,0x50);c.branch(0xf0,'map_beam_ok526')
        # A tile no longer fits. Give the still-eligible map tail this blank.
        c.emit(0xc2,0x20);c.absolute(0xad,0x1250);c.emit(0x38,0xe9,8,0,0xaa,0xe2,0x20)
        c.long(0xbf,0x7e4001);c.emit(0x29,0x70,0xc9,0x50);c.branch(0xd0,defer)
        if cls.map_chunk>64:c.emit(0xc2,0x20)
        cls.map_length(c,'fallback_length532')
        if cls.map_chunk>64:c.emit(0xe2,0x20)
        c.label('map_beam_ok526')


class PairedMap(SmallTiles):
    map_chunk=128


class InteriorTiles(PairedMap):
    @staticmethod
    def select(c):
        # Delay selection until the fresh beam test; active-video polls skip the scan.
        c.absolute(0xad,0x1250);c.absolute(0xcd,0x1252);c.branch(0xd0,'live532')
        c.emit(0x60);c.label('live532')  # Equal pointers already set carry.

    @classmethod
    def late_beam(cls,c,defer):
        # A is 8-bit at the live beam test and must be 8-bit again at arbitration.
        c.emit(0xc9,255);c.branch(0xb0,defer)
        c.emit(0xc9,233);c.branch(0xb0,'late532')
        c.emit(0xc2,0x20);c.absolute(0xae,0x1252);c.emit(0xa0,8,0)
        c.label('scan532');c.long(0xbf,0x7e4000);c.emit(0x29,0,0x70,0xc9,0,0x50);c.branch(0xf0,'scan_next532')
        c.long(0xbf,0x7e4004);c.emit(0xc9,161,0);c.branch(0x90,'tile532')
        c.label('scan_next532');c.emit(0x8a,0x18,0x69,8,0,0xaa);c.absolute(0xec,0x1250);c.branch(0xb0,'head532')
        c.emit(0x88);c.branch(0xd0,'scan532')
        c.label('head532');c.absolute(0xae,0x1252)
        c.long(0xbf,0x7e4000);c.emit(0x29,0,0x70,0xc9,0,0x50);c.branch(0xf0,'row526')
        c.long(0xbf,0x7e4004);c.emit(0xc9,1,8);c.branch(0xb0,'skip_scan532')
        c.label('tile532');c.emit(0xa8);c.branch(0x80,'selected526')
        c.label('late532');c.emit(0xc2,0x20);c.absolute(0xad,0x1250);c.emit(0x38,0xe9,8,0,0xaa)
        c.long(0xbf,0x7e4000);c.emit(0x29,0,0x70,0xc9,0,0x50);c.branch(0xf0,'row526')
        c.label('skip_scan532');c.emit(0x38,0x60)
        c.label('row526');cls.map_length(c,'normal_length532')
        c.label('selected526');c.emit(0xe2,0x20)

    @classmethod
    def retire(cls,c):
        # Move the oldest live entry into the completed interior slot. Only
        # execute after synchronous MDMAEN; a deferred request changes no entry.
        c.absolute(0xec,0x1252);c.branch(0xf0,'retire_regular532')
        c.emit(0x8a,0x18,0x69,8,0);c.absolute(0xcd,0x1250);c.branch(0xf0,'retire_regular532')
        c.emit(0x8a,0x18,0x69,0,0x40,0xa8)
        c.absolute(0xad,0x1252);c.emit(0x18,0x69,0,0x40,0xaa)
        c.emit(0xa9,7,0,0x8b,0x54,0x7e,0x7e,0xab)
        c.absolute(0xae,0x1252);c.branch(0x80,'whole526')
        c.label('retire_regular532');super().retire(c)


def merge_emitter(edit=None):
    s=inspect.getsource(nes_dirty212.emit)
    anchor="c.label('append212');lda(0x1250);cond(0xf0,'append_new212');c.emit(0x38,0xe9,8,0,0xaa)"
    s=once(s,anchor,anchor+"""
 # Only live entries can be extended. Changing X reuses append212's existing
 # source, destination and size checks for the descriptor before a map tail.
 c.long(0xbf,0x7e4000);c.emit(0x29,0,0x70,0xc9,0,0x50);c.branch(0xd0,'merge532')
 lda(0x70);c.emit(0x29,0,0x70,0xc9,0,0x50);c.branch(0xb0,'merge532')
 c.absolute(0xec,0x1252);c.branch(0xf0,'merge532')
 c.emit(0x8a,0x38,0xe9,8,0,0xaa)
 c.label('merge532')""")
    s=once(s," lda(0x78);c.long(0x9f,0x7e4004);"," c.label('merge_written532');lda(0x78);c.long(0x9f,0x7e4004);")
    if edit is not None:
        s=edit(s)
    ns=dict(vars(nes_dirty212))
    exec(compile(s,'tile532-append','exec'),ns)
    return ns['emit']


def build(out,before_beam=None,paired=False,interior=False,policy=None):
    policy=policy or (InteriorTiles if interior else PairedMap if paired else SmallTiles)
    emitter=prefix.emit
    if interior:
        s=inspect.getsource(emitter)
        start=s.index('    c.emit(0xe2,0x20);load(0x4212)')
        end=s.index('    if rows and rows.late_beam',start)
        beam=s[start:end].replace(',defer)',",'no_beam532')")
        beam=once(beam,"c.branch(0x10,'no_beam532')","c.branch(0x30,'active532');c.label('no_beam532');c.emit(0xc2,0x20,0x38,0x60);c.label('active532')")
        ns=dict(vars(prefix))
        exec(compile(s[:start]+beam+s[end:],'tile532-beam','exec'),ns)
        emitter=ns['emit']
    def priority(c):
        if not interior:return arbitrate(c)
        c.label('priority524');c.absolute(0xad,0x6001);c.branch(0x10,'ready524')
        c.store(0x1236,1);c.jump('skip8_523')
        c.label('ready524');c.absolute(0xad,0x6000);c.emit(0x29,1);c.branch(0xf0,'grant524')
        c.jump('skip8_523');c.label('grant524')
    with patch.object(nes_dirty212,'emit',merge_emitter()):
        result=prefix.build(out,emitter=lambda c:emitter(c,before_beam,priority,policy),
                            fill=True,packet_edit=packet,upload_edit=prefix.upload)
    result.update(candidate='tile532',small_tile_B=160,map_chunk_B=policy.map_chunk,tile_last_line=232,map_last_line=254,final_last_line=246)
    (out/'build.json').write_text(json.dumps(result,indent=2)+'\n',newline='\n')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True)
    p.add_argument('--paired-map',action='store_true')
    p.add_argument('--interior',action='store_true')
    a=p.parse_args();print(build(a.out,paired=a.paired_map,interior=a.interior)['body_bytes'])
