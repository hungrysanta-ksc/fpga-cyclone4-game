# SPDX-License-Identifier: MIT
"""Experimental compact EB progress; full E0 identity ACK remains mandatory.

Reuses489 SPI snapshot/CRC, leaves known-good SNES program byte identical.
No installer or physical timing claim; Flash/FIT/ownership gates select it.
"""
import argparse,json,shutil,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def once(s,a,b):
    assert s.count(a)==1,a[:90]
    return s.replace(a,b)
def arm(s):
    s=once(s,'uint8_t tx[20]={0xe0},rx[20];if(!io(s,tx,rx,20))return false;',
           'unsigned n=ack?20:8;uint8_t tx[20]={0},rx[20];tx[0]=ack?0xe0:0xeb;if(!io(s,tx,rx,n))return false;')
    s=once(s,'i<19;i++','i<n-1;i++')
    s=once(s,'rx[1]!=0xf7||rx[19]!=c','rx[1]!=(ack?0xf7:0xf8)||rx[n-1]!=c')
    s=once(s,'s->ack_status=(rx[2]&2)?rx[7]:0;','s->ack_status=(ack&&(rx[2]&2))?rx[7]:0;')
    s=once(s,'s->retired=r;memcpy(ack,rx+7,12);','s->retired=r;if(ack)memcpy(ack,rx+7,12);')
    start=s.index('static bool credit(');end=s.index('static bool send(',start)
    q=s[start:end];q=once(q,' uint8_t ack[12];\n','');q=once(q,'status(s,ack)','status(s,NULL)');s=s[:start]+q+s[end:]
    start=s.index('bool nes_window184_drain(');end=s.index('bool nes_window184_barrier(',start)
    q=s[start:end];q=once(q,'status(s,ack)','status(s,s->last[0]==3?NULL:ack)')
    q=once(q,'  if(s->retired==s->sent){','  if(s->retired==s->sent){\n   if(s->last[0]==3&&!status(s,ack))return false;')
    return s[:start]+q+s[end:]
def rtl(s):
    s=once(s,"wire ours=command==8'he0||command==8'he1;","wire ours=command==8'he0||command==8'heb||command==8'he1;")
    s=once(s,"if(command==8'he0&&byte_count>=1&&byte_count<=19)","if((command==8'he0||command==8'heb)&&byte_count>=1&&byte_count<=19)")
    s=once(s,"if(crc_position==17)begin snapshot[7:0]<=crc8(status_crc,snapshot[151-crc_position*8-:8]);crc_busy<=0;end",
      "if(crc_position==(command==8'heb ? 5'd5 : 5'd17))begin\n     if(command==8'heb)snapshot[103:96]<=crc8(status_crc,snapshot[151-crc_position*8-:8]);\n     else snapshot[7:0]<=crc8(status_crc,snapshot[151-crc_position*8-:8]);\n     crc_busy<=0;end")
    s=once(s,"if(command==8'he0)begin if(byte_count!=20||bit_count!=0)fault<=1;end",
      "if(command==8'he0||command==8'heb)begin if(byte_count!=(command==8'heb ? 8 : 20)||bit_count!=0)fault<=1;end")
    return once(s,"snapshot[151:144]<=8'hf7;","snapshot[151:144]<=incoming==8'heb ? 8'hf8 : 8'hf7;")
def boot(s):
    # Invalid owner/range still latches check_failed on this SAME memory edge.
    # Reader reset cancels SETUP before CE/OE can assert on its following edge.
    # Legal reads already meet owner_valid/IDLE in the physical controller.
    return once(s,'.check_request(check_request && raw_check_ready && address_valid && !check_failed)',
                  '.check_request(check_request)')
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['arm','board','out']:p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--direct-check',action='store_true')
    a=p.parse_args();assert sha(a.arm/'obj-nes-100/firmware.stm')==json.loads((ROOT/'analysis/boot493-package.json').read_text())['firmware_SHA256']
    a.out.mkdir(parents=True,exist_ok=False);patch=a.out/'patch';patch.mkdir()
    n='nes_sink_window184.c';(patch/n).write_text(arm((a.arm/n).read_text()),encoding='utf8',newline='\n')
    pins=json.loads((ROOT/'analysis/output489-verification.json').read_text())['FPGA']['whole_board_inputs'];board=a.out/'board';board.mkdir()
    for n,h in pins.items():
        assert sha(a.board/n)==h,n;d=board/n;d.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(a.board/n,d)
    f=board/'nes_sink_spi165.sv';f.write_text(rtl(f.read_text()),encoding='utf8',newline='\n')
    if a.direct_check:
        f=board/'nes_rom_boot.sv';f.write_text(boot(f.read_text()),encoding='utf8',newline='\n')
    r={'experimental':True,'scope':__doc__,'ARM_baseline_SHA256':sha(a.arm/'obj-nes-100/firmware.stm'),
       'board_inputs':{n:sha(board/n)for n in pins},'changed_board_files':[n for n in pins if sha(board/n)!=pins[n]],
       'SNES_program_unchanged':sha(board/'sink-program.hex')==pins['sink-program.hex'],'new_RAM_B':0,'new_SPI_snapshot_FF':0}
    assert set(r['changed_board_files'])==({'nes_sink_spi165.sv','nes_rom_boot.sv'}if a.direct_check else {'nes_sink_spi165.sv'});(a.out/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps({'changed_board':r['changed_board_files'],'SNES_unchanged':r['SNES_program_unchanged']}))
