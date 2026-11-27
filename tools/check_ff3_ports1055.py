"""Check shipped checkpoint RTL at SPI1 /32 and replay the stair transition."""
import shutil
import tempfile
import subprocess
import sys
from pathlib import Path
from replay_nes_mask820 import simulate
from build_nes_game164 import RGB
from prepare_ff3_pair1055 import ROOT, OUT

def main():
    board = OUT.parent/'nes-pair1054/board-ram-retail'
    bins = Path('C:/altera_standard/25.1std/questa_fse/win64')
    temp_spi = tempfile.TemporaryDirectory(prefix='ff3-port-')
    port = Path(temp_spi.name)
    (OUT/'spi').mkdir(exist_ok=True)
    source = (ROOT/'tests/nes-functional/ff3_spi_tb.sv').read_text()
    # Sample mode 0 at the rising edge. The endpoint samples on the
    # asynchronous 21.477 MHz system clock, not the host SPI clock.
    source = source.replace('always #5 clk', 'always #23.28 clk').replace('#100;', '#2000;')
    source = source.replace('#60;sck=1;#45;', '#190.476;sck=1;').replace('#15;sck=0;', '#190.476;sck=0;')
    (port/'port.sv').write_text(source)
    def run(tool,args,log):
        with (OUT/'spi'/log).open('wb') as output:
            subprocess.run([bins/(tool+'.exe'),*args],cwd=port,stdout=output,stderr=subprocess.STDOUT,check=True)
    run('vlib',['work'],'lib.log')
    for name in ('nes_checkpoint_spi.sv','nes_run_observer134.sv'):
        shutil.copyfile(board/name,port/name)
    run('vlog',['-sv','nes_checkpoint_spi.sv','nes_run_observer134.sv','port.sv'],'vlog.log')
    for boot in (0,1):
        log=f'boot{boot}.log'
        run('vsim',['-c',f'-gBOOT={boot}','ff3_spi_tb','-do','onerror {quit -code 1}; run -all; quit -f'],log)
        assert 'PASS' in (OUT/'spi'/log).read_text() and '** Fatal' not in (OUT/'spi'/log).read_text()
    for first in (55,95,134,218):
        d=OUT/f'g{first}'
        if not d.exists():
            tower=OUT/'tower'
            subprocess.run([sys.executable,ROOT/'tools/prepare_nes_geometry230.py',
                            '--capture',tower,'--prior',tower,'--out',d,'--first',str(first),
                            '--last',str(first+3),'--chr-ram-type','56'],check=True)
        def adapt(text):
            fragment=(ROOT/'tests/nes-functional/ff3_checkpoint_tb.sv').read_text()
            k=fragment.index('    $display("GEOMETRY')
            fragment=fragment[k:fragment.index('   end\n  end',k)].replace('proof_frame','f').replace('collector.','frame.')
            return (text.replace('reg enable=0;', 'wire [7:0] clean_pages=0;wire fine_receipt=0,snapshot_conflict=0;reg enable=0;')
                    .replace('nes_native_frame201 frame(.*);',"nes_native_frame201 frame(.query_index({1'b0,query_index}),.*);")
                    .replace(".start_permitted(1'b1)",".clean_pages(clean_pages),.fine_receipt(fine_receipt),.chr_unchanged(&clean_pages),.start_permitted(1'b1)")
                    .replace('done=0;records=0;', fragment+'\n   done=0;records=0;'))
        with tempfile.TemporaryDirectory(prefix='ff3-stair-') as temp:
            work=Path(temp)
            core=work/'core'
            core.mkdir()
            for f in board.glob('*.sv'):shutil.copyfile(f,core/f.name)
            for f in d.glob('frame*'):shutil.copyfile(f,work/f.name)
            # RGB-black aliases palette codes 0x0d/0x0e/0x0f. Prefer the
            # observed universal color when RGB equal; keep all other colors.
            for f in work.glob('*.hex'):
                backdrop=int(f.with_suffix('.palette').read_text(),16)&63
                rows=[]
                for line in f.read_text().splitlines():
                    word=int(line,16)
                    if RGB[(word>>100)&63]==RGB[backdrop]:
                        word=word&~(63<<100)|backdrop<<100
                    rows.append(f'{word:027x}')
                f.write_text('\n'.join(rows)+'\n')
            try:simulate(core,work,[(first,first+3)],adapt=adapt)
            finally:
                for pattern in ('*.log','*.query'):
                    for f in work.glob(pattern):shutil.copyfile(f,d/f.name)

if __name__=='__main__':main()
