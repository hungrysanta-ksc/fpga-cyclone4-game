# SPDX-License-Identifier: MIT
"""Actual65816 comparison: per-range checks versus per-batch cached context.

Both read/check bank and generation and write all four token bytes for every
consume. Cached tokens advance in software, with32-bit carry. Core still checks
the exact token, byte consumption, range receipt and final display ACK.
Non-map production in THIS CPU experiment is the unchanged262 fixture boundary.
"""
import inspect,struct,json
from pathlib import Path
from nes_delta231 import once,sha,ROOT
from build_nes_trace_replay import Code
from probe_nes_joint262 import prepare as old_prepare
import probe_nes_joint261_coupled as old

def common_sources():
 from nes_joint262 import sources
 src=sources()
 src['nes_mux260.sv']=once(src['nes_mux260.sv'],"   8'h51:control=receipt_committed;", "   8'h53:control=state==DMA&&batch?remaining:0;\n   8'h51:control=receipt_committed;")
 return src

def prepare(d,last):
 src,pins,stats=old_prepare(d,last)
 for n,s in common_sources().items():(d/n).write_text(s,encoding='utf-8',newline='\n')
 for n in ['probe_nes_common263.py','nes_joint263.py']:
  p=ROOT/'tools'/n;pins[p.as_posix()]=sha(p)
 return src,pins,stats

def rom(d,cached):
 c=Code(0x8000);c.emit(0x78,0x18,0xfb,0xc2,0x30,0xa2,0xff,0x1f,0x9a,0xa9,0,0,0x5b,0xe2,0x20)
 for a,v in [(0x4200,0),(0x420c,0),(0x2100,0x80),(0x2115,0x80)]:c.store(a,v)
 c.emit(0x64,0x20) # remaining count, zero at admission
 c.label('next');c.absolute(0xad,0x6040);c.branch(0xd0,'dma')
 c.absolute(0xad,0x6052);c.branch(0xf0,'next');c.jump('display')
 c.label('dma')
 if cached:c.emit(0xa5,0x20);c.branch(0xd0,'context_ready')
 c.absolute(0xad,0x6041);c.emit(0xc9,2);c.branch(0xf0,'bank_ok');c.jump('fault');c.label('bank_ok')
 c.emit(0xc2,0x20);c.absolute(0xad,0x6046);c.emit(0xc9,1,0);c.branch(0xf0,'gen_ok');c.jump('fault');c.label('gen_ok')
 c.absolute(0xad,0x6048);c.emit(0x85,0x24);c.absolute(0xad,0x604a);c.emit(0x85,0x26);c.emit(0xe2,0x20)
 if cached:
  c.absolute(0xad,0x6053);c.branch(0xd0,'count_nonzero');c.jump('fault');c.label('count_nonzero')
  c.emit(0xc9,48);c.branch(0x90,'count_ok');c.jump('fault');c.label('count_ok');c.emit(0x85,0x20)
 c.label('context_ready');c.emit(0xc2,0x20);c.absolute(0xad,0x6044);c.emit(0x18,0x69,0,0x40);c.absolute(0x8d,0x2116)
 c.absolute(0xad,0x6042);c.absolute(0x8d,0x4305);c.emit(0xe2,0x20)
 for a,v in [(0x4300,1),(0x4301,0x18),(0x4302,0),(0x4303,8),(0x4304,0x40),(0x420b,1)]:c.store(a,v)
 c.emit(0xc2,0x20,0xa5,0x24);c.absolute(0x8d,0x604c);c.emit(0xa5,0x26);c.absolute(0x8d,0x604e);c.emit(0xe2,0x20);c.store(0x6050,0xa5)
 if cached:
  c.emit(0xc6,0x20,0xc2,0x20,0xe6,0x24);c.branch(0xd0,'no_carry');c.emit(0xe6,0x26);c.label('no_carry');c.emit(0xe2,0x20)
 c.jump('next')
 c.label('display');c.label('active');c.absolute(0xad,0x4212);c.branch(0x30,'active')
 c.label('blank');c.absolute(0xad,0x4212);c.branch(0x10,'blank')
 c.store(0x2107,0x40);c.store(0x2100,15)
 for i in range(4):c.absolute(0xad,0x6048+i);c.absolute(0x8d,0x604c+i)
 c.store(0x6058,0x5a);c.label('done');c.branch(0x80,'done')
 c.label('fault');c.emit(0xe2,0x20);c.store(0x6057,0xee);c.branch(0x80,'fault');data=c.finish()
 r=bytearray([255])*32768;r[:len(data)]=data;r[0x7fc0:0x7fd5]=b'NES263 COMMON CONTEXT '.ljust(21,b' ')[:21];r[0x7fd5:0x7fdc]=bytes([0x20,0,5,0,1,0,0])
 for p in range(0x7fe0,0x8000,2):struct.pack_into('<H',r,p,0x8000)
 checksum=sum(r)&65535;struct.pack_into('<HH',r,0x7fdc,checksum^65535,checksum);(d/'joint.sfc').write_bytes(r);return len(data)

def main():
 s=inspect.getsource(old.main)
 s=once(s,"p.add_argument('--out'", "p.add_argument('--cached',action='store_true');p.add_argument('--out'")
 s=s.replace('body=rom(d)','body=rom(d,a.cached)').replace('joint261_tb','joint262_tb').replace('finished261','finished261')
 s=s.replace('scope=__doc__,cpu=cpu_result','scope=__doc__,cached=a.cached,cpu=cpu_result')
 lua=old.LUA.replace('0x6040,0x6052','0x6040,0x6053').replace(' if a==0x6050 then', " assert(a~=0x6057,'CPU context validation failed')\n if a==0x6050 then")
 ns=dict(old.__dict__);ns.update(prepare=prepare,rom=rom,LUA=lua,__doc__=__doc__)
 exec(compile(s,'common263-coupled','exec'),ns);ns['main']()

if __name__=='__main__':main()
