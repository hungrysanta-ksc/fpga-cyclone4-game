# SPDX-License-Identifier: MIT
"""498 actual C callback + RTL + old65816 functional join; no shared M4/IRQ clock."""
from pathlib import Path
import runpy,sys,subprocess
FRAMES=1
PREPARE_ONLY='--prepare-only' in sys.argv
if PREPARE_ONLY:sys.argv.remove('--prepare-only')
if '--frames' in sys.argv:
 i=sys.argv.index('--frames');FRAMES=int(sys.argv[i+1]);del sys.argv[i:i+2]
assert FRAMES in (1,2)
read=Path.read_text
write=Path.write_text
MONITOR=r"""
 always @(posedge dut.core.clk)if(dut.run_enable&&!dut.core_reset&&(dut.native_spi_fault||dut.sink_fault||dut.rom_fault))
 $fatal(1,"FAULT498 native=%b inputSPI=%b directH=%b directN=%b lease=%b exportError=%0d exportState=%0d closed=%b drain=%b generation=%0d saved=%0d tile=%b batch=%b bulk=%b command=%b consume=%b sink=%b ROM=%b",
 dut.native_spi_fault,dut.core.native_spi_fault,dut.core.direct_fault204,dut.core.direct_nes_fault204,dut.core.lease_fault204,
 dut.core.native_export_error,dut.core.native_export.state,dut.core.plan_closed204,dut.core.reader_drained204,dut.core.native_generation,dut.core.native_export.generation,
 dut.core.direct_path.tile_fault,dut.core.direct_path.batch_fault,dut.core.direct_path.bulk_fault,dut.core.direct_path.command_error,dut.core.direct_path.consume_error,dut.sink_fault,dut.rom_fault);
"""
def watched(self,s,*args,**kwargs):
 if self.name=='join208_tb.sv' and 'FAULT498' not in s:
  assert s.count('endmodule')==1
  s=s.replace('endmodule',MONITOR+'\nendmodule')
 return write(self,s,*args,**kwargs)
Path.write_text=watched

def patched(self,*args,**kwargs):
 s=read(self,*args,**kwargs)
 if self.name=='test_nes_supply485_live.py':
  s=s.replace('quiet="""static unsigned quiet485_calls;', 'quiet="""static bool (*saved498)(void *,bool (*)(void *),unsigned,bool);\nstatic unsigned quiet485_calls;')
  needle='return guard(ctx);\n}\n"""';assert s.count(needle)==1
  s=s.replace(needle,'return guard(ctx);\n}\nstatic bool joined498(void *ctx,bool (*guard)(void *),unsigned reason,bool progress){\n return saved498(ctx,guard,reason,progress)&&quiet485(ctx,guard,reason,progress);\n}\n"""')
  assert s.count('runtime.transport.wait=quiet485;')==1
  s=s.replace('runtime.transport.wait=quiet485;','saved498=runtime.transport.wait;runtime.transport.wait=joined498;')
  marker="f.write_text(text.replace(needle,' saved498=runtime.transport.wait;runtime.transport.wait=joined498;\\n'+needle))"
  assert marker in s
  s=s.replace(marker,"text=text.replace('received.state!=NES_NATIVE165_IDLE','(received.state!=NES_NATIVE165_IDLE&&received.state!=NES_NATIVE165_RECEIVING&&received.state!=NES_NATIVE165_COMPLETE)');"+marker)
  marker="runner.write_text(s,encoding='utf8',newline='\\n')"
  assert s.count(marker)==1
  s=s.replace(marker,"assert s.count(\"consumer['commits']==1\")==1\ns=s.replace(\"consumer['commits']==1\",\"consumer['commits']=="+str(FRAMES)+"\")\n"+marker)
 return s
original_run=subprocess.run
def compile_hook(cmd,*args,**kwargs):
 if FRAMES==2 and 'host.c' in list(map(str,cmd)) and 'host.exe' in list(map(str,cmd)):
  d=Path(kwargs['cwd']);p=d/'host.c';s=p.read_text()
  assert s.count('while(qacks!=1)')==1
  s=s.replace('while(qacks!=1)','while(qacks!=retired+1)')
  assert s.count('fprintf(f,"1\\n");')==1
  s=s.replace('fprintf(f,"1\\n");','fprintf(f,"2\\n");')
  needle='(void)ctx;unsigned cmd=tx[0];harvest();'
  assert s.count(needle)==1
  s=s.replace(needle,needle+r'''
 if(cmd==0xd3&&tx[4]==1){assert(qacks==retired&&retired==runtime.frames);FILE *e=fopen("ownership498.txt","a");assert(e);fprintf(e,"COMMIT %u ack=%u retired=%u frames=%u\n",256u*tx[2]+tx[3],qacks,retired,(unsigned)runtime.frames);fclose(e);}
 if(cmd==0xea){FILE *e=fopen("ownership498.txt","a");assert(e);fprintf(e,"EA %u ack=%u retired=%u frames=%u\n",runtime.sink.last_generation,qacks,retired,(unsigned)runtime.frames);fclose(e);}
''')
  p.write_text(s)
  p=d/'native_fixture.inc';s=p.read_text().replace('while(!runtime.frames&&','while(runtime.frames<2&&').replace('runtime.frames!=1','runtime.frames!=2').replace('qacks!=1||retired!=1','qacks!=2||retired!=2');p.write_text(s)
 if PREPARE_ONLY and 'host.c' in list(map(str,cmd)):
  print('Prepared498 sources and final runner; no compile or simulation executed.');raise SystemExit(0)
 return original_run(cmd,*args,**kwargs)
subprocess.run=compile_hook
Path.read_text=patched
runpy.run_path(str(Path(__file__).with_name('test_nes_status495_live.py')),run_name='__main__')
