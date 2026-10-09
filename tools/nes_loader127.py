# SPDX-License-Identifier: MIT
"""Materialize the diagnostic127 loader/guard into the pinned126 core slice."""
from pathlib import Path
import hashlib,json,shutil,re
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(p,s):p.write_text(s,encoding='utf-8',newline='\n')
def replace(s,a,b):
 assert s.count(a)==1,a
 return s.replace(a,b)
def materialize(out,baseline126,baseline086,full=False):
 pins={}
 for base,meta,prefix in [(baseline126,'control126','fit02/candidate/'),(baseline086,'clock086','fit03/')]:
  m=json.loads((ROOT/f'analysis/{meta}-verification.json').read_bytes())
  assert sha(base/'manifest.json')==m['manifest_sha256']
  entries=json.loads((base/'manifest.json').read_bytes())['files']
  wanted=['nes_rom_boot.sv','nes_rom_spi.sv','nes_spi_boot.sv'] if meta=='clock086' else ['nes_rom_physical.sv']
  if full and meta=='control126':
   wanted=[n[len(prefix):] for n in entries if n.startswith(prefix) and (n.endswith(('.sv','.v','.vhd','.qsf','.sdc','.qpf')))]
  for n in wanted:
   src=base/prefix/n;assert sha(src)==entries[prefix+n],n
   dst=out/n;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
   pins[meta+'/'+n]=sha(src)
 for src,dst in [('nes_rom_loader127.sv','nes_rom_loader.sv'),('nes_diag_clock_guard127.sv','nes_diag_clock_guard127.sv'),('nes_diag_startup_guard.sv','nes_diag_startup_guard.sv'),('nes_domain_reset124.sv','nes_domain_reset124.sv')]:
  p=ROOT/'src/nes/diagnostic'/src;shutil.copy2(p,out/dst);pins['public/'+src]=sha(p)
 f=out/'nes_rom_spi.sv';s=replace(f.read_text(),"8'h63:fail(8); // 061 diagnostic never permits RUN","8'h63:if(verified && loaded && !run_enable)start<=1;else fail(8); // 127 verified RUN only")
 # CHECK's index changes only at command retirement, length is immutable during
 # CHECK, and offset is complete after byte3 of the8-byte frame. Precompute the
 # wide comparisons; DATA's live loaded_bytes/ready comparison stays immediate.
 s=replace(s,'reg [23:0] offset;', '''reg [23:0] offset;
 reg offset_matches_next,next_below_length,next_matches_length;
 always @(posedge mem_clk or posedge reset)
  if(reset)begin offset_matches_next<=0;next_below_length<=0;next_matches_length<=0;end
  else begin
   offset_matches_next <= offset=={7'd0,check_next};
   next_below_length <= check_next<loaded_bytes;
   next_matches_length <= check_next==loaded_bytes;
  end''')
 s=s.replace("offset!={7'd0,check_next}",'!offset_matches_next').replace('check_next>=loaded_bytes','!next_below_length').replace('check_next!=loaded_bytes','!next_matches_length')
 put(f,s)
 f=out/'nes_spi_boot.sv';put(f,replace(f.read_text(),".start(1'b0)",'.start(start)'))
 f=out/'nes_rom_boot.sv';put(f,replace(f.read_text(),'nes_rom_physical reader(', 'nes_rom_physical #(.READ_CYCLES(16)) reader('))
 if full:
  f=out/'nes_live_joint.sv';s=f.read_text()
  s=replace(s,'boot_reset=ext_reset||!locked','boot_reset=ext_reset||!locked||!external_memory_ready')
  pos=s.index('// Read-only feasibility slice.')
  end=s.index(' wire rom_cpu_address_valid',pos)
  block='''// Diagnostic127: actual loader/CHECK/RUN owns the single PSRAM bus.
 wire guard_allow,guard_fault,external_memory_ready,startup_ready,release_memory;
 wire guard_reset=ext_reset||!locked;
 nes_diag_clock_guard127 clock_guard(.mem_clk(mem_clk),.ref_clk(clk),.reset(guard_reset),.allow_memory(guard_allow),.fault(guard_fault));
 nes_domain_reset124 memory_release(.clk(mem_clk),.raw_reset(guard_reset||!guard_allow),.reset(release_memory));
 nes_diag_startup_guard #(.WAIT_CYCLES(33603)) startup(.clk(mem_clk),.reset(release_memory),.ready(startup_ready));
 assign external_memory_ready=guard_allow && !release_memory && startup_ready;
 nes_spi_boot loader_boot(.clk(clk),.mem_clk(mem_clk),.reset(!external_memory_ready),.read_reset(common_reset),
 .SPI_SS(ext_SPI_SS),.SPI_SCK(ext_SPI_SCK),.SPI_MOSI(ext_SPI_MOSI),
 .spi_miso(out_spi_miso),.spi_selected(out_spi_selected),.spi_fault(out_spi_fault),.spi_error(out_spi_error),
 .load_ready(load_ready),.loaded(loaded),.run_enable(run_enable),.boot_fault(boot_fault),.boot_error(boot_error),.loaded_bytes(loaded_bytes),.rom_chr32(chr_32k),
 .rom_request(rom_request),.rom_address(rom_address),.rom_ready(rom_ready),.rom_response(rom_response),.rom_error(rom_error),.rom_response_address(rom_response_address),.rom_data(rom_data),
 .psram_address(psram_address),.psram_1ce(psram_1ce),.psram_2ce(psram_2ce),.psram_oe(psram_oe),.psram_we(psram_we),.psram_bhe(psram_bhe),.psram_ble(psram_ble),.psram_data(ext_psram_data));
'''
  put(f,s[:pos]+block+s[end:])
  f=out/'live.qsf';s=f.read_text()
  for n in ['nes_rom_loader.sv','nes_rom_boot.sv','nes_rom_spi.sv','nes_spi_boot.sv','nes_diag_clock_guard127.sv','nes_diag_startup_guard.sv']:
   assert not re.search(r'_FILE '+re.escape(n)+r'\s',s);s+='\nset_global_assignment -name SYSTEMVERILOG_FILE '+n
  put(f,s+'\n')
 put(out/'materialization127.json',json.dumps(dict(inputs=pins,outputs={str(p.relative_to(out)).replace('\\','/'):sha(p) for p in out.rglob('*') if p.is_file()}),indent=2)+'\n')
