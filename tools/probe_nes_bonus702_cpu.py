"""Extend699 T65 boundary through the following CPU fetch, without changing RTL."""
import argparse,json
from pathlib import Path
import probe_nes_bonus699_cpu as prior
from nes_game147 import sha

def prepare(board,rom,out,phase):
    prior.prepare(board,rom,out,phase,True)
    p=out/'game147_tb.sv';s=p.read_text()
    assert 'if(step699>=59)break;' in s
    s=s.replace('if(step699>=59)break;','if(step699>=79)break;')
    s=s.replace("if(ppumem_addr!==dut.core.chr_linaddr || ppumem_addr!==22'h21fbe7 || native_chr_logical!==14'h1fe7)",
                "if(ppumem_addr!==dut.core.chr_linaddr || (step699<=59 && (ppumem_addr!==22'h21fbe7 || native_chr_logical!==14'h1fe7)))")
    marker='    if(step699>=79)break;'
    s=s.replace(marker,'''    if(start699>=0)$display("MEM702 scenario=%0d step=%0d cpu_sample=%b valid=%b need=%b ppu_need=%b ready=%b busy=%b owner_ppu=%b age=%0d pending=%h demand=%h context=%h ppu=%h",
      scenario,step699,rom_cpu_sample,rom_cpu_valid,rom_service.cpu_need,rom_service.ppu_need,rom_ready,rom_service.busy,rom_service.pending_ppu,rom_service.age,rom_service.pending_address,cpumem_addr,fault_context,ppu_fault_state154);
'''+marker)
    p.write_text(s,encoding='utf8',newline='\n')
    m=json.loads((out/'inputs.json').read_text());m['stage']=702;m['sources']['game147_tb.sv']=sha(p)
    m['scope']='699 actual T65/arbiter fixture extended step59->79; next CPU fetch with unchanged hardware. Not full-game replay.'
    (out/'inputs.json').write_text(json.dumps(m,indent=2)+'\n',newline='\n')

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('board','rom','out'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--phase',type=float,required=True)
    a=p.parse_args();prepare(a.board,a.rom,a.out,a.phase)
