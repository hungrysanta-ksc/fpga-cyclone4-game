# SPDX-License-Identifier: MIT
"""Read post-fit EDA RAM atom constants, not merely the MIF source file."""
from pathlib import Path
import argparse,hashlib,json,re
from nes_game147 import ROOT,sha
def main():
 p=argparse.ArgumentParser()
 for n in ['netlist','expected','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
 want=bytes.fromhex(a.expected.read_text());assert len(want)==4096
 files=sorted(a.netlist.glob('*.vo'));assert len(files)==4
 checks=[]
 for path in files:
  vo=path.read_text();rows=re.findall(r'defparam \\sink\|bus\|program_rom_rtl_0\|auto_generated\|ram_block1a(\d+) \.mem_init(\d) = 2048\'h([0-9A-F]+);',vo)
  assert len(rows)==16 and {(int(i),int(j)) for i,j,v in rows}=={(i,j) for i in [0,2,4,6] for j in range(4)}
  rom=bytearray(4096)
  for bit in [0,2,4,6]:
   prefix=f'defparam \\sink|bus|program_rom_rtl_0|auto_generated|ram_block1a{bit} .'
   for k,v in [('operation_mode','"rom"'),('port_a_address_width','12'),('port_a_data_width','2'),('port_a_first_bit_number',str(bit)),('port_a_logical_ram_depth','4096'),('port_a_logical_ram_width','8')]:assert prefix+k+' = '+v+';' in vo,(path,k,bit)
   value=sum(int(v,16)<<(2048*int(j)) for i,j,v in rows if int(i)==bit)
   for addr in range(4096):rom[addr]|=((value>>(2*addr))&3)<<bit
  assert rom==want,path
  checks.append({'file':path.name,'netlist_sha256':sha(path),'rom_sha256':hashlib.sha256(rom).hexdigest(),'matched_bytes':len(rom)})
 result={'passed':True,'checks':checks,'reset_vector':want[0xffc:0xffe].hex(),'expected_hex_sha256':sha(a.expected),'scope':'Post-fit EDA atom constants at three corners and default; no RBF bit extraction or physical readback. Original routed database cloned before EDA export.','public_sources':{'tools/inspect_nes_startup170_rom.py':sha(ROOT/'tools/inspect_nes_startup170_rom.py')}}
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS170 post-fit ROM atoms:4 netlists x4096 bytes; reset008000')
if __name__=='__main__':main()
