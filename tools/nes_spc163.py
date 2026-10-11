# SPDX-License-Identifier: MIT
"""Bounded native SNES/SPC bootstrap; no NES APU or board RTL changes."""
import importlib.util
from pathlib import Path

def payload():
    path=Path(__file__).resolve().parents[1]/'src/renderer/base/g9_snes_io.py'
    spec=importlib.util.spec_from_file_location('gbc_spc_reference163',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module.spc_program()

def emit(c):
    # Entry: native A8, X/Y16, DBR=DP=0, PBR=7E. Scratch DP10 is private.
    # $7001 is the existing sticky error byte, repurposed for this candidate:
    # A9=FLG20 readback, E1..E5=IPL/start/byte/ready/FLG failure. Write once.
    # All wait loops are bounded; failure resumes the unchanged video client.
    data=payload()
    def wait(name,expected,fail):
        c.emit(0xa0,0xff,0xff);c.label(name)
        c.absolute(0xad,0x2140)
        if expected is None:c.emit(0xc5,0x10)
        else:c.emit(0xc9,expected)
        c.branch(0xf0,name+'_ok');c.emit(0x88);c.branch(0xd0,name)
        c.store(0x7001,fail);c.jump('spc_done');c.label(name+'_ok')
    c.store(0x2140,0xf0) # Existing GBC driver can return to IPL after warm reset.
    c.emit(0xa0,0xff,0xff);c.label('spc_ipl')
    c.absolute(0xad,0x2140);c.emit(0xc9,0xaa);c.branch(0xd0,'spc_ipl_retry')
    c.absolute(0xad,0x2141);c.emit(0xc9,0xbb);c.branch(0xf0,'spc_ipl_ok')
    c.label('spc_ipl_retry');c.emit(0x88);c.branch(0xd0,'spc_ipl')
    c.store(0x7001,0xe1);c.jump('spc_done');c.label('spc_ipl_ok')
    for a,v in [(0x2142,0),(0x2143,1),(0x2141,1),(0x2140,0xcc)]:c.store(a,v)
    wait('spc_start',0xcc,0xe2)
    c.emit(0xa2,0,0);c.label('spc_upload')
    pos=len(c.data);c.long(0xbf,0) # LDA long,X of payload copied with body to WRAM.
    c.absolute(0x8d,0x2141);c.emit(0x8a,0x85,0x10);c.absolute(0x8d,0x2140)
    wait('spc_byte',None,0xe3)
    c.emit(0xe8,0xe0);c.word(len(data));c.branch(0xd0,'spc_upload')
    for a,v in [(0x2142,0),(0x2143,1),(0x2141,0),(0x2140,len(data)+1)]:c.store(a,v)
    wait('spc_ready',0xa9,0xe4)
    c.absolute(0xad,0x2141);c.emit(0xc9,0x20);c.branch(0xf0,'spc_flg_ok')
    c.store(0x7001,0xe5);c.jump('spc_done');c.label('spc_flg_ok')
    c.store(0x7001,0xa9);c.jump('spc_done')
    address=c.base+len(c.data);c.data[pos+1:pos+4]=address.to_bytes(3,'little')
    c.emit(*data);c.label('spc_done')
    return dict(payload_bytes=len(data),payload_address=address,scratch_dp=0x10,status_address=0x7001,
                success=0xa9,expected_dsp_flg=0x20,failures=dict(IPL=0xe1,START=0xe2,BYTE=0xe3,READY=0xe4,FLG=0xe5),wait_iterations=65535)
