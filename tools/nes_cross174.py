# SPDX-License-Identifier: MIT
"""174 cross-tile BG planes, bounded32-bit exceptions; no extra MCU storage.

Exception = low physical tile13 | linear cell13(row*33+column) | highY3 | lowY3.
Wire BEGIN1741 rejects1651 consumers; exception payload grows3 ->4 bytes.
Internal event cross bit61: low tile={60:57,24:16}; lowY55:53; mixed56.
Without cross, existing event byte layout remains exact. OBJ stays strict.
"""
from pathlib import Path
import argparse,json,shutil
from nes_game147 import sha

def planes(s):
 start=s.index(' wire split_pair=');end=s.index(' // RAM accesses',start)
 s=s[:start]+''' wire bg_pair=!is_obj && description[52:25]==pair_description[52:25];
 wire pair_ok=pair_pending && address_ok && logical_address[3] && (ordinary_pair || bg_pair);
 wire cross_tile=pair_address[16:4]!=physical_address[16:4];
 wire mixed_planes=cross_tile || pair_address[2:0]!=physical_address[2:0];
 wire [63:0] plane_extension=mixed_planes?{7'd0,1'b1,pair_address[2:0],53'd0}:64'd0;
 wire [63:0] cross_description={2'd0,1'b1,pair_address[16:13],description[56:25],pair_address[12:4],description[15:0]};
 wire mark_high=initialized && capturing && ppu_ce && relevant && high_event && pair_ok && !rom_fault && !extra_sprites;
 // Both sources enter the required set. A rejected frame cannot export it.
 // Low/high events are separated by PPU cycles; retain the RAM forwarding.
 wire mark_low=initialized && capturing && ppu_ce && relevant && low_event && address_ok && !logical_address[3] && !rom_fault && !extra_sprites;
 wire mark=mark_low || mark_high;
'''+s[end:]
 s=s.replace('event_valid<=1;event_data<=description|plane_extension;','if(mark_high)begin event_valid<=1;event_data<=(cross_tile?cross_description:description)|plane_extension;end')
 s=s.replace('// Actual pattern-load events. Same physical tile, separate BG plane fine-Y.', '//174 Actual pattern-load events. BG planes may use different physical tiles.')
 return s

def compact(s):
 s=s.replace('[19:0] exceptions','[31:0] exceptions').replace('[19:0] exception_q','[31:0] exception_q').replace("{44'd0,exception_q}","{32'd0,exception_q}")
 start=s.index(' wire invalid_extension=');end=s.index(' wire starting=',start)
 s=s[:start]+''' wire cross_tile=event_data[61];
 wire [12:0] low_tile=cross_tile?{event_data[60:57],event_data[24:16]}:tile;
 wire [12:0] cell_index={5'd0,row}*13'd33+{7'd0,position[5:0]};
 wire invalid_extension=event_data[63:62]!=0 ||
   (cross_tile?(!mixed_planes || obj || low_tile==tile):(event_data[60:57]!=0)) ||
   (mixed_planes?(obj || (!cross_tile && low_fine==fine)):(event_data[55:53]!=0));
'''+s[end:]
 s=s.replace('{row,position[5:0],fine,low_fine}','{low_tile,cell_index,fine,low_fine}')
 s=s.replace('128*20 =28384','128*32 =29920')
 return s

def receiver(s):
 for a,b in [('{2,1,7,3,7,1,2,8}','{2,1,7,4,7,1,2,8}'),('0x1651','0x1741'),('{15,8,49,20,49,6}','{15,8,49,32,49,6}'),
 ('case 3:if((v>>12)>=224||((v>>6)&63)>32)return fail(s,11);s->exceptions[index]=(uint32_t)v;break;',
 'case 3:if(((v>>6)&8191)>=7392)return fail(s,11);s->exceptions[index]=(uint32_t)v;require_tile(s,(unsigned)(v>>19),1);break;')]:
  assert s.count(a)==1,a;s=s.replace(a,b)
 return s

def converter(s):
 s=s.replace('if((v>>12)==y&&((v>>6)&63)==x)', 'if(((v>>6)&8191)==y*33+x)')
 s=s.replace('if(v>>20||(v>>12)>=224||((v>>6)&63)>32)', 'if(((v>>6)&8191)>=7392)')
 s=s.replace('(s->exceptions[j]>>6)==(v>>6)', '((s->exceptions[j]>>6)&8191)==((v>>6)&8191)')
 anchor='  unsigned previous=p->bg_count,slot=bg_slot(p,key);'
 assert s.count(anchor)==1
 s=s.replace(anchor,'''  /* Cross-tile cells use a unique per-frame key. Never hash pixel bytes or
   * silently alias another pattern; ordinary patterns retain exact dedupe. */
  for(unsigned i=0;i<s->counts[3];i++){
   uint32_t e=s->exceptions[i];unsigned pos=(e>>6)&8191,y=pos/33;
   if(pos%33==x && y>=first[g] && y<end[g] && (e>>19)!=(cell&8191)){
    const uint8_t *lo=tile(s,e>>19,1);if(!lo)return fail(p,6);
    b[fine(s,y,0,false)*2]=lo[e&7];key=(UINT64_C(1)<<63)|(g*33+x);
   }
  }
'''+anchor)
 return s

CHANGED=['nes_native_planes165.sv','nes_native_compact_planes165.sv','nes_native_spi165.sv','nes_native_export165.sv']

def prepare_mcu(prior,out):
 assert sha(prior/'src/obj-nes-100/firmware.stm')=='9b137807a07ffb2ebcb41e8bcddcbe585aa3e60bb8aa89cb7ee7534a031008d6'
 out.mkdir(parents=True,exist_ok=False)
 m=json.loads((prior/'preparation-profile173.json').read_bytes())
 pins=m['copied']|m['changed']|m['added'];r=dict(copied={},changed={},added={})
 for n,h in pins.items():
  assert sha(prior/n)==h,n
  p=out/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(prior/n,p);r['copied'][n]=h
 for n in ['src/nes_menu_diagnostic.c','src/nes_checkpoint112.c','src/VERSION']:
  s=(out/n).read_text()
  for a,b in [('NES-GAME-173','NES-GAME-174'),('GAME 173','GAME 174'),('game173.nes','game174.nes'),('fpga_n173.bi3','fpga_n174.bi3'),('last-173.txt','last-174.txt'),('NES173 seq=','NES174 seq='),('nes-progress-173.txt','nes-progress-174.txt'),('NES-GAME173-DEV','NES-GAME174-DEV')]:s=s.replace(a,b)
  (out/n).write_text(s,encoding='utf-8',newline='\n');r['changed'][n]=sha(out/n)
 for n,fn in [('src/nes_native165.c',receiver),('src/nes_native_video165.c',converter)]:
  (out/n).write_text(fn((out/n).read_text()),encoding='utf-8',newline='\n');r['changed'][n]=sha(out/n)
 for n in ['preparation-cross174.json','preparation-runlease165.json']:(out/n).write_text(json.dumps(r,indent=2)+'\n')
 return r
def prepare(baseline,client,out):
 assert not out.exists() and str(out).isascii();out.mkdir(parents=True)
 pins=json.loads((baseline/'preparation.json').read_bytes())['sources']
 for n,h in pins.items():
  assert sha(baseline/n)==h,n
  p=out/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(baseline/n,p)
 for n,fn in zip(CHANGED,[planes,compact,lambda s:s.replace('3:width=3','3:width=4'),lambda s:s.replace("16'h1651","16'h1741")]):
  (out/n).write_text(fn((out/n).read_text()),encoding='utf-8',newline='\n')
 assert sha(client/'sink-program.hex')=='e1c350b76fea340a1ed9fa643929ce80bd0371b748b374d57ce8d90d85188fc5'
 shutil.copy2(client/'sink-program.hex',out/'sink-program.hex')
 m={'sources':{n:sha(out/n) for n in pins},'baseline':pins,'changed':CHANGED+['sink-program.hex'],'public_sources':{'tools/nes_cross174.py':sha(Path(__file__))},'wire_magic':'1741','exception_bytes':4,'save_sram_used':False}
 (out/'preparation.json').write_text(json.dumps(m,indent=2)+'\n')
if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ['baseline','client','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();prepare(a.baseline,a.client,a.out)
