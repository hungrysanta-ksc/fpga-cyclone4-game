"""Compile a minimal local NES functional probe without changing pinned upstream.
SPDX-License-Identifier: MIT. Generated/adapted HDL retains its original notices.
"""
from pathlib import Path
import argparse,hashlib,json,re,subprocess,shutil,difflib,os
PIN='49a0a662e244469ca77b2155746a066df704ffae'
VHDL=['rtl/bus_savestates.vhd']+[f'rtl/t65/{n}.vhd' for n in ['T65_Pack','T65_ALU','T65_MCode','T65']]+['rtl/statemanager.vhd','rtl/savestates.vhd']
SV=['rtl/regs_savestates.sv','rtl/cheatcodes.sv','rtl/ppu.sv','rtl/apu.sv','rtl/nes.v','rtl/composite_board.sv','rtl/compat.v','sys/iir_filter.v']
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def normalize(text):
    """Hoist module-scope declarations; preserve continuous net initializers as assigns.
    Only unindented declarations in this fixed upstream are selected. Never moves
    procedural blocks, clocks or assignments; only constant-zero register initializers move.
    """
    def module(m):
        source=m[0];name=re.match(r'module\s+(\w+)',source)[1]
        variables={'ClockGen':{'vblank_start_sl','vblank_end_sl','vsync_start_sl','skip_en'},'SpriteAddressGenEx':{'load_temp'},'PPU':{'vram_a'}}.get(name,set())
        for variable in variables:source=re.sub(r'(?m)^wire(\s+(?:\[[^\]]+\]\s*)?'+variable+r'\s*;)',r'reg\1',source)
        outputs={'OAMEval':['Savestate_OAMReadData'],'debug_dots':['new_color'],'PPU':['vram_r_ex']}.get(name,[])
        for output in outputs:source=re.sub(r'(\boutput\s+)(\[[^\]]+\]\s*)?('+output+r')\b',lambda d:d[1]+'reg '+(d[2] or '')+d[3],source)
        split=source.index(');')+2;header,body=source[:split],source[split:]
        params=[];decls=[]
        pattern=r'(?m)^(wire|reg|localparam|parameter)\s+([^;]+);'
        def take(d):
            kind,tail=d[1],d[2]
            if kind in ('localparam','parameter'):params.append(d[0]);return ''
            if kind=='reg' and '=' in tail and not re.fullmatch(r"\s*(?:\d+)?(?:'[bdh])?0\s*",tail.split('=',1)[1]):return d[0]
            if kind=='wire' and '=' in tail:
                lhs,rhs=tail.split('=',1);name=re.search(r'(\w+)\s*$',lhs)[1]
                decls.append('wire '+lhs.rstrip()+';');return 'assign '+name+' ='+rhs+';'
            decls.append(d[0]);return ''
        body=re.sub(pattern,take,body)
        imports=re.findall(r'(?m)^import [^;]+;',body)
        for imp in imports:body=body.replace(imp,'',1)
        return header+'\n'+'\n'.join(imports+params+decls)+'\n'+body
    return re.sub(r'(?ms)^module\b.*?^endmodule',module,text)

def generate_adapter(u,out):
    header=(u/'rtl/nes.v').read_text().split('module NES(',1)[1].split(');',1)[0]
    header=re.sub(r'//[^\n]*','',header)
    ports=re.findall(r'\b(input|output)\s+(signed\s+)?(\[[^\]]+\]\s*)?(\w+)',header)
    live={'clk','reset_nes','cold_reset','cpumem_din','ppumem_din','joypad1_data','joypad2_data'}
    observed={'sample','color','emphasis','joypad_clock','joypad_out','cpumem_addr','cpumem_read','cpumem_write','cpumem_dout','ppumem_addr','ppumem_read','ppumem_write','ppumem_dout','cycle','scanline','apu_ce','hsync','vsync','hblank','vblank'}
    constants={'dejitter_timing':"1'b1",'gg':"1'b1",'gg_reset':'reset_nes','int_audio':"1'b1",'audio_channels':"5'b11111",'prg_mask':"21'h007fff",'chr_mask':"20'h01fff"}
    decl=[];conn=[]
    for direction,signed,width,name in ports:
        if name in observed or name in live:
            decl.append(f'{direction} wire {signed}{width}{name}');conn.append(f'.{name}({name})')
        else:conn.append(f'.{name}({"" if direction=="output" else constants.get(name,"\u00270")})')
    (out/'nes_probe.sv').write_text('// SPDX-License-Identifier: GPL-3.0-or-later\n// Original NROM-only wrapper; upstream port interface.\nmodule nes_probe(\n'+',\n'.join(decl)+'\n);\nNES core(\n'+',\n'.join(conn)+'\n);\nendmodule\n',encoding='utf-8',newline='\n')
    cart=(u/'rtl/cart.sv').read_text().split('module cart_top (',1)[1].split(');',1)[0];cart=re.sub(r'//[^\n]*','',cart)
    outputs=re.findall(r'output\s+(?:reg\s+)?(?:\[[^\]]+\]\s*)?(\w+)',cart)
    values={'prg_aout':"(prg_ain < 16'h2000) ? (25'h380000 | {14'b0,prg_ain[10:0]}) : {10'b0,prg_ain[14:0]}",
      'prg_allow':"(prg_ain < 16'h2000) || (prg_ain[15] && !prg_write)",
      'chr_aout':"chr_ain_orig[13] ? (22'h3a0000 | {11'b0,(flags[14] ? chr_ain_orig[10] : chr_ain_orig[11]),chr_ain_orig[9:0]}) : (22'h200000 | {9'b0,chr_ain_orig[12:0]})",
      'vram_ce':'chr_ain_orig[13]','vram_a10':'flags[14] ? chr_ain_orig[10] : chr_ain_orig[11]',
      'chr_allow':"flags[15]",'prg_dout':"8'hff",'chr_dout':"8'hff",'audio':'audio_in'}
    (out/'cart_nrom.sv').write_text('// SPDX-License-Identifier: GPL-3.0-or-later\n// Original NROM adapter; no mapper expansion/savestates.\nmodule cart_top('+cart.replace('output reg','output wire')+');\n'+'\n'.join(f'assign {n} = {values.get(n,"\u00270")};' for n in outputs)+'\nendmodule\n',encoding='utf-8',newline='\n')

def main():
    p=argparse.ArgumentParser();p.add_argument('--upstream',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--questa-bin',type=Path,required=True);p.add_argument('--diagnostic',type=Path);p.add_argument('--testbench',type=Path);a=p.parse_args()
    if a.testbench and not re.fullmatch(r"\d+@(?:localhost|127\.0\.0\.1)",os.environ.get('SALT_LICENSE_SERVER','')):
        p.error('Simulation requires the established local FLOAT endpoint. Use tools/run_nes_functional.ps1; do not use the inherited uncounted license file.')
    u=a.upstream.resolve();out=a.out.resolve();assert str(out).isascii(), "Questa work database requires ASCII output path";out.mkdir(parents=True,exist_ok=False)
    rev=subprocess.check_output(['git','-c','safe.directory='+u.as_posix(),'-C',str(u),'rev-parse','HEAD'],text=True).strip();assert rev==PIN
    changes=[];inventory=[]
    for file in VHDL+SV+['COPYING','rtl/cart.sv']:
        src=u/file;dst=out/file;dst.parent.mkdir(parents=True,exist_ok=True);original=src.read_text();data=original
        if file in SV and file!='rtl/regs_savestates.sv':
            if file=='rtl/nes.v':
                # Mixed-language ports require exact widths; preserve zero values.
                data=data.replace('.mode   (0)', ".mode   (2'b00)").replace('.BCD_en (0)', ".BCD_en (1'b0)")
                data=data.replace('wire [15:0] cpu_addr;', 'wire [15:0] cpu_addr;\nwire [23:0] cpu_addr_full;\nassign cpu_addr = cpu_addr_full[15:0];')
                data=data.replace('.A      (cpu_addr)', '.A      (cpu_addr_full)')
                data=data.replace('T65 cpu(', "T65 cpu(\n.Abort_n(1'b1), .SO_n(1'b1),")
                data=data.replace('PPU ppu(', 'PPU ppu(\n.cold_reset(cold_reset),')
                data=data.replace('APU apu(', "APU apu(\n.allow_us(1'b0),")
                # Deterministic reset of timing state (otherwise X skips each fourth CPU slot).
                anchor='if (reset_nes) begin\n\t\tcorepause_active'
                assert anchor in data
                data=data.replace(anchor,'if (reset_nes) begin\n\t\tcpu_tick_count <= 0;\n\t\tfaux_pixel_cnt <= 0;\n\t\tfreeze_clocks <= 0;\n\t\tcorepause_active')
            if file=='rtl/cheatcodes.sv':
                parameters=re.findall(r'(?m)^parameter\s+[^;]+;',data)
                for param in parameters:data=data.replace(param,'',1)
                data=data.replace('module CODES(', 'module CODES #(\n'+',\n'.join(v.replace('parameter ','',1)[:-1] for v in parameters)+'\n) (')
                data=data.replace('output genie_ovr','output reg genie_ovr').replace('output [DATA_WIDTH - 1:0] genie_data','output reg [DATA_WIDTH - 1:0] genie_data')
            if file=='rtl/ppu.sv':
                # Cold boot status starts clear (as in the reference); preserve warm-reset behavior.
                anchor='if (SaveStateBus_load) begin\n\t\tsprite0_hit_bg <= SS_PPU[0];'
                assert anchor in data
                data=data.replace(anchor,"if (cold_reset) begin\n\t\tsprite0_hit_bg <= 1'b0;\n\tend else "+anchor)
            data=normalize(data)
        dst.write_text(data,encoding='utf-8',newline='\n')
        inventory.append(dict(path=file,upstream_sha256=sha(src),compiled_sha256=sha(dst),changed=data!=original))
        if data!=original:changes+=list(difflib.unified_diff(original.splitlines(True),data.splitlines(True),fromfile='upstream/'+file,tofile='simulation/'+file))
    (out/'simulation-only.diff').write_text(''.join(changes),encoding='utf-8',newline='\n')
    generate_adapter(u,out)
    result=dict(candidate='NES-P2-RTL-006',upstream_commit=rev,sources=inventory,source_sha256=sha(__file__),license_route='local FLOAT' if a.testbench else 'compile only',scope='NROM local CPU/PPU/APU with ideal synchronous external memory; no board or licensed adoption claim',phases={})
    def run(exe,args,name):
        with (out/(name+'.log')).open('wb') as log:r=subprocess.run([str(a.questa_bin/(exe+'.exe')),*args],cwd=out,stdout=log,stderr=subprocess.STDOUT)
        result['phases'][name]=r.returncode;(out/'build.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
        if r.returncode:raise SystemExit('Failed '+name+'; inspect raw '+str(out/(name+'.log')))
    run('vlib',['work'],'vlib')
    for i,file in enumerate(VHDL):run('vcom',['-2008',file],f'vcom-{i:02}')
    run('vlog',['-sv','-mfcu',*SV,'cart_nrom.sv','nes_probe.sv'],'vlog')
    print('PASS minimal compilation',flush=True)
    if a.testbench:
        assert a.diagnostic and json.loads((a.diagnostic/'manifest.json').read_text())['original_diagnostic']
        for name in ['prg.hex','chr.hex','manifest.json']:shutil.copy2(a.diagnostic/name,out/name)
        tb=a.testbench.read_text();hdr=(out/'nes_probe.sv').read_text().split('module nes_probe(',1)[1].split(');',1)[0]
        extra=[]
        for direction,signed,width,name in re.findall(r'\b(input|output)\s+wire\s+(signed\s+)?(\[[^\]]+\]\s*)?(\w+)',hdr):
            if direction=='output' and not re.search(r'\b'+name+r'\s*[;,]',tb):extra.append(f'wire {signed}{width}{name};')
        tb=tb.replace('nes_probe dut(.*);','\n'.join(extra)+'\nnes_probe dut(.*);')
        (out/'nes_tb.sv').write_text(tb,encoding='utf-8',newline='\n')
        result['testbench_source_sha256']=sha(a.testbench)
        result['generated_inputs']={n:sha(out/n) for n in ['nes_probe.sv','cart_nrom.sv','nes_tb.sv','prg.hex','chr.hex','manifest.json']}
        result['adaptations']=['declaration normalization','exact T65 port widths and inactive input levels','reset timing counters','connect PPU cold_reset and clear sprite-zero-hit only on cold boot','disable unused APU ultrasonic extension','original NTSC timing, no de-jitter padding','disable/reset unused cheat path']
        run('vlog',['-sv','nes_tb.sv'],'vlog-tb')
        run('vsim',['-c','nes_tb','-do','onerror {quit -code 1}; run -all; quit -f'],'simulation')
        log=(out/'simulation.log').read_text(errors='replace')
        result['diagnostic_passed']='PASS NES DIAGNOSTIC' in log and not re.search(r'\*\* (?:Fatal|Error):',log)
        (out/'build.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
        if not result['diagnostic_passed']:raise SystemExit('Simulation did not produce a clean diagnostic PASS; inspect raw evidence')
        print('PASS NES DIAGNOSTIC (actual RTL execution)',flush=True)
if __name__=='__main__':main()
