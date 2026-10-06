"""Extend the pinned RTL-006 build with a local Mapper4 adapter. SPDX-License-Identifier: MIT."""
from pathlib import Path
import hashlib,json,re,sys,shutil,difflib
import nes_functional as base
original_adapter=base.generate_adapter

def adapter(u,out):
 original_adapter(u,out)
 p=out/'nes_probe.sv';s=p.read_text().replace(".mapper_flags('0)",".mapper_flags(64'd4)").replace("21'h007fff","21'h00ffff").replace("20'h01fff","20'h03fff");p.write_text(s,encoding='utf-8',newline='\n')
 raw=(u/'rtl/mappers/MMC3.sv');assert base.sha(raw)=='a85f0324d941c7cf0bf3022b2b94a63e82ba989f882156090585d0d7cac04165'
 module=re.search(r'(?ms)^module MMC3\s*\(.*?^endmodule',raw.read_text())[0];normalized=base.normalize(module)
 shutil.copy2(raw,out/'MMC3.upstream.sv')
 (out/'mmc3-normalization.diff').write_text(''.join(difflib.unified_diff(module.splitlines(True),normalized.splitlines(True),fromfile='upstream/MMC3',tofile='local/MMC3')),encoding='utf-8',newline='\n')
 p=out/'cart_nrom.sv';header=p.read_text().split('module cart_top(',1)[1].split(');',1)[0];outputs=re.findall(r'output\s+(?:wire\s+)?(?:\[[^\]]+\]\s*)?(\w+)',header)
 values={'prg_aout':"prg_ain<16'h2000 ? (25'h380000|{14'd0,prg_ain[10:0]}) : prg_ain[15] ? {9'd0,mp[15:0]} : {3'd0,mp}",'prg_allow':"prg_ain<16'h2000 ? 1'b1 : pa",'chr_aout':"vc ? (22'h3a0000|{11'd0,va,chr_ain_orig[9:0]}) : (22'h200000|{8'd0,mc[13:0]})",'prg_dout':'pd','chr_dout':"8'hff",'chr_allow':'ca','vram_ce':'vc','vram_a10':'va','irq':'mi','audio':'audio_in'}
 body='''
wire [21:0] mp,mc;wire [7:0] pd;wire pa,ca,va,vc,mi;
wire [15:0] ignored_audio,ignored_flags;wire [63:0] ignored_state;
MMC3 mapper(.clk(clk),.ce(ce),.enable(!reset),.flags(32'd4),
.prg_ain(prg_ain),.prg_aout_b(mp),.prg_read(prg_read),.prg_write(prg_write),.prg_din(prg_din),.prg_dout_b(pd),.prg_allow_b(pa),
.chr_ain(chr_ain_orig),.chr_aout_b(mc),.chr_read(chr_read),.chr_allow_b(ca),.vram_a10_b(va),.vram_ce_b(vc),.irq_b(mi),
.audio_in(audio_in),.audio_b(ignored_audio),.flags_out_b(ignored_flags),.chr_ain_o(chr_ain_orig),.m2_inv(cpu_ce),.paused(paused),
.SaveStateBus_Din(64'd0),.SaveStateBus_Adr(10'd0),.SaveStateBus_wren(1'b0),.SaveStateBus_rst(1'b0),.SaveStateBus_load(1'b0),.SaveStateBus_Dout(ignored_state));
'''
 p.write_text('// Local-only Mapper4 integration; upstream license holds remain.\nmodule cart_top('+header+');\n'+body+'\n'.join(f'assign {n} = {values.get(n,"\u00270")};' for n in outputs)+'\nendmodule\n'+normalized+'\n',encoding='utf-8',newline='\n')

def main():
 assert base.sha(Path(base.__file__))=='28524fbf36ee98aae0675c070bf42883afb4489ed1ae499c0f3e4ef5c6a56d1e'
 out=Path(sys.argv[sys.argv.index('--out')+1]);diagnostic=Path(sys.argv[sys.argv.index('--diagnostic')+1]);m=json.loads((diagnostic/'manifest.json').read_text());assert m['mapper']==4 and m['prg_bytes']==65536 and m['chr_bytes']==16384
 base.generate_adapter=adapter
 try:base.main()
 finally:
  p=out/'build.json'
  if p.exists():
   r=json.loads(p.read_text());r['infrastructure_candidate']=r['candidate'];r['candidate']='NES-P2-MMC3-INTEGRATED-009';r['integration_driver_sha256']=base.sha(__file__);r['mapper_source_sha256']=base.sha(out/'MMC3.upstream.sv');r['scope']='Original Mapper4 integrated CPU/PPU under ideal memory; local adapted RTL, no fit/hardware/license clearance.';p.write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8',newline='\n')
if __name__=='__main__':main()
