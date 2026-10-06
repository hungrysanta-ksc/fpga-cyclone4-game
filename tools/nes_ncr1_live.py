# SPDX-License-Identifier: MIT
"""047 actual pinned014/018 core -> PPU tap ->046 ->045 ->044, ideal ROM service."""
from pathlib import Path
import argparse,hashlib,json,re,shutil,subprocess,os,difflib
from nes_functional import VHDL,SV
from nes_h1_sampling import frontend,transport
ROOT=Path(__file__).resolve().parents[1]
CANDIDATE='NES-R2-NCR1-LIVE-047'
FILES=['nes_packet_queue_ram','nes_packet_cdc_ram','nes_host_stage','nes_snes_frontend','nes_transport','nes_packet_memory_producer','nes_ncr1_encoder','nes_ncr1_ppu_tap']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(p,s):p.write_text(s,encoding='utf-8',newline='\n')
def expose(s,module,ports,assigns=''):
 m=re.search(r'\bmodule '+module+r'\s*\(',s);assert m,module
 start=m.end();end=s.index(');',start)
 finish=s.index('endmodule',end)
 return s[:start]+'\n'+ports+',\n'+s[start:finish]+'\n'+assigns+'\n'+s[finish:]
def prepare(out):
 core=ROOT/'analysis/local-resource-018/ram-01';meta=json.loads((core/'result.json').read_text())
 for n,h in meta['sources'].items():
  assert sha(core/n)==h,n
  dst=out/n;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(core/n,dst)
 original={n:(out/n).read_text() for n in ['rtl/ppu.sv','rtl/nes.v','nes_probe.sv','cart_nrom.sv']}
 s=original['rtl/ppu.sv']
 s=expose(s,'PaletteRam','output wire [95:0] tap_palette', '\n'.join(f'assign tap_palette[{i*6}+:6]=palette[{i}];' for i in range(16)))
 s=s.replace('PaletteRam palette_ram(', 'PaletteRam palette_ram(\n.tap_palette(tap_palette),')
 s=expose(s,'VramAddressGen','output wire [14:0] tap_scroll','assign tap_scroll=vram_t;')
 s=s.replace('VramAddressGen vram0(', 'VramAddressGen vram0(\n.tap_scroll(tap_scroll),')
 s=expose(s,'BgPainter','output wire [1:0] tap_attribute','assign tap_attribute=current_attribute_table;')
 s=s.replace('BgPainter bg_painter(', 'BgPainter bg_painter(\n.tap_attribute(tap_attribute),')
 pports='output wire tap_bgp,tap_mode,tap_ppu_change,output wire [2:0] tap_fine,output wire [14:0] tap_scroll,output wire [95:0] tap_palette,output wire [1:0] tap_attribute'
 pass_ppu='\n'.join('.'+n+'('+n+'),' for n in ['tap_bgp','tap_mode','tap_ppu_change','tap_fine','tap_scroll','tap_palette','tap_attribute'])
 s=expose(s,'PPU',pports,"assign tap_bgp=bgp_en;\nassign tap_mode=enable_playfield && !enable_objects && playfield_clip && !bg_patt && !grayscale && emph_reg==0;\nassign tap_fine=fine_x_scroll;\nassign tap_ppu_change=(write && (ppu_ain==0 || ppu_ain==1 || ppu_ain>=5)) || (read && ppu_ain==7);")
 put(out/'rtl/ppu.sv',s)
 nports=pports+',output wire tap_ce,tap_mapper_change'
 s=expose(original['rtl/nes.v'],'NES',nports,"assign tap_ce=ppu_ce;\nassign tap_mapper_change=cart_ce && prg_write && (prg_addr[15:13]==3'b100 || prg_addr[15:13]==3'b101);")
 s=s.replace('PPU ppu(', 'PPU ppu(\n'+pass_ppu);put(out/'rtl/nes.v',s)
 s=expose(original['nes_probe.sv'],'nes_probe',nports+',input wire chr_32k')
 s=s.replace(".prg_mask(21'h1fffff)",".prg_mask(21'h00ffff)").replace(".chr_mask(20'hfffff)",".chr_mask(chr_32k?20'h07fff:20'h03fff)")
 s=s.replace('NES core(', 'NES core(\n'+pass_ppu+'\n.tap_ce(tap_ce),.tap_mapper_change(tap_mapper_change),')
 put(out/'nes_probe.sv',s)
 s=original['cart_nrom.sv']
 s=re.sub(r'input\s+\[9:0\] prg_mask', 'input [20:0] prg_mask',s)
 s=re.sub(r'input\s+\[9:0\] chr_mask', 'input [19:0] chr_mask',s)
 s=s.replace(" : {3'd0,mp};", " : prg_ain[15] ? {4'd0,(mp[20:0] & prg_mask)} : {3'd0,mp};")
 s=s.replace("(22'h200000|mc)","(22'h200000|(mc & {2'b0,chr_mask}))")
 assert 'mp[20:0] & prg_mask' in s and 'mc & {2\'b0,chr_mask}' in s
 put(out/'cart_nrom.sv',s)
 put(out/'tap-export.diff',''.join(''.join(difflib.unified_diff(old.splitlines(True),(out/n).read_text().splitlines(True),fromfile='018/'+n,tofile='047/'+n)) for n,old in original.items()))
 for n in FILES:shutil.copy2(ROOT/'src/nes'/(n+'.sv'),out/(n+'.sv'))
 put(out/'nes_snes_frontend.sv',frontend());put(out/'nes_transport.sv',transport())
 shutil.copy2(ROOT/'tests/nes-functional/ncr1_live_tb.sv',out/'ncr1_live_tb.sv')
 return {n:sha(out/n) for n in VHDL+SV+['cart_nrom.sv','nes_probe.sv','ncr1_live_tb.sv','tap-export.diff']+[n+'.sv' for n in FILES]}
def verify_case(out,case):
 from build_nes_chr_residency import decode
 from build_nes_trace_replay import convert
 c=out/case;rows=[v.split() for v in (c/'live.tsv').read_text().splitlines()]
 events=[v for v in rows if v[0]=='E'];starts=[v for v in rows if v[0]=='S'];ends=[v for v in rows if v[0]=='F'];desc=[v for v in rows if v[0]=='D']
 bus=bytes(int(v[2]) for v in rows if v[0]=='B');assert len(bus)==8032 and len(events)==65552 and len(starts)==len(ends)==len(desc)==4
 chrdata=bytes(int(v,16) for v in (c/'chr.hex').read_text().split());atlas=convert(chrdata).ljust(32768,b'\0')
 frames=[]
 for i in range(1,5):
  packet=bus[(i-1)*2008:i*2008];assert packet[5]==i and packet[6]==(case=='fine_x')
  pix=bytes(int(v,16) for v in (c/f'frame-{i}.hex').read_text().split());assert len(pix)==61440 and decode(packet,atlas)==pix
  e=[v for v in events if int(v[1])==i];assert len(e)==16388
  useful=[v for v in e if (0<=int(v[2])<240 and int(v[3])<=247) or (-1<=int(v[2])<239 and int(v[3])>=321)]
  assert len(useful)==15840 and int.from_bytes(packet[12:16],'little')==int(useful[-1][4])
  assert int(ends[i-1][2])<=int(desc[i-1][2])<int(starts[i][2]) if i<4 else int(ends[i-1][2])<=int(desc[i-1][2])
  (c/f'packet-{i}.bin').write_bytes(packet)
  frames.append({'frame':i,'window':packet[7],'fine_x':packet[6],'release_tick':int.from_bytes(packet[12:16],'little'),'pixels':len(pix),'pixel_sha256':sha(c/f'frame-{i}.hex'),'packet_sha256':sha(c/f'packet-{i}.bin')})
 log=(c/'simulation.log').read_text(errors='replace');assert 'PASS LIVE NES frames=4 bytes=8032' in log and not re.search(r'\*\* (?:Fatal|Error):',log)
 return {'case':case,'passed':True,'frames':frames,'fetches':len(events),'bus_bytes':len(bus),'raw_attributes':sorted(set(int(v[6]) for v in events))}
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--questa-bin',type=Path,required=True);a=p.parse_args();out=a.out.resolve()
 assert re.fullmatch(r'18000@(?:localhost|127\.0\.0\.1)',os.environ.get('SALT_LICENSE_SERVER',''))
 assert str(out).isascii() and not out.exists();out.mkdir();sources=prepare(out)
 meta={'candidate':CANDIDATE,'sources':sources,'passed':False,'cases':[],'scope':'Fresh actual RTL core execution under ideal synchronous ROM/RAM, diagnostic palette-only BG, no board image or timing signoff'}
 def save():put(out/'result.json',json.dumps(meta,indent=2)+'\n')
 def run(tool,args,log,cwd=out):
  with log.open('wb') as f:cp=subprocess.run([str(a.questa_bin/(tool+'.exe')),*args],cwd=cwd,stdout=f,stderr=subprocess.STDOUT,timeout=900)
  assert cp.returncode==0,str(log)
 save();run('vlib',['work'],out/'vlib.log')
 for i,n in enumerate(VHDL):run('vcom',['-2008',n],out/f'vcom-{i:02}.log')
 run('vlog',['-sv','-mfcu',*SV,'cart_nrom.sv','nes_probe.sv',*[n+'.sv' for n in FILES],'ncr1_live_tb.sv'],out/'vlog.log')
 for case in ('banks32','fine_x'):
  c=out/case;c.mkdir();src=ROOT/f'analysis/local-video-workloads-021/{case}/build'
  for n in ('prg.hex','chr.hex','manifest.json'):shutil.copy2(src/n,c/n)
  put(c/'modelsim.ini','[Library]\nwork = '+(out/'work').as_posix()+'\nothers = '+(a.questa_bin.parent/'modelsim.ini').as_posix()+'\n')
  run('vsim',['-c','-ini','modelsim.ini','work.ncr1_live_tb','+CHR32='+str(int(case=='banks32')),'-do','onerror {quit -code 1}; run -all; quit -f'],c/'simulation.log',c)
  meta['cases'].append(verify_case(out,case));save();print('PASS actual-core '+case,flush=True)
 meta['passed']=True;save();print(json.dumps(meta['cases'],indent=2))
if __name__=='__main__':main()
