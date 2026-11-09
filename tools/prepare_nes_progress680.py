"""Connect an advisory map-DMA event without changing packet/final ACK meaning."""
import argparse,json,shutil
from pathlib import Path
from nes_raw506 import once,sha
from nes_entry665 import receiver,ORIGIN
from nes_rom636 import build
from build_nes_trace_replay import Code
from nes_native_local165 import call


def arm(base,out):
    ref=json.loads(Path('analysis/handoff678-verification.json').read_text())
    assert sha(base/'src/obj-nes-100/firmware.stm')==ref['firmware']
    shutil.copytree(base,out,ignore=shutil.ignore_patterns('obj-*','.dep-*','*.log','*.json'))
    p=out/'src/nes_sink_window184.c'
    s=once(p.read_text(),'if(rx[2]&0xf8)return fail(s,4);',
        '''/* Progress is advisory and belongs only to the fully retired identity.
  * Reserved/fault bits remain errors; never accept progress on a live head. */
 if((rx[2]&0xf0)||((rx[2]&8)&&((rx[2]&7)!=2)))return fail(s,4);''')
    p.write_text(s,newline='\n')
    p=out/'src/nes_plan_service200.c';s=p.read_text()
    s=once(s,'p->window->last[1]==2 && p->window->wait){',
        '(p->window->last[1]==2 || (p->window->last[1]==5 && p->window->last[0]==5)) && p->window->wait){')
    s=once(s,'!p->window->wait(p->window->ctx,p->window->guard,4,false))return fail(p,5);',
        '''(!(p->window->status_flags&8) &&
        !p->window->wait(p->window->ctx,p->window->guard,4,false)))return fail(p,5);''')
    s=s.replace('retire the real map queue, and service one','retire the real map or immutable fill queue, and service one')
    p.write_text(s,newline='\n')


def client(base,out,extra_edit=None):
    symbols={}
    def edit(original,labels):
        old,labels=receiver(original,labels)
        assert sha_bytes(old)==json.loads(Path('analysis/progress679-budget.json').read_text())['source_pins']['body']
        body=bytearray(old);c=Code(ORIGIN+len(body));c.labels.update(labels)
        c.label('dma_start680')
        # Capture the source class BEFORE the DMA and before interior retire
        # can move descriptors. Two bytes live only across this synchronous DMA.
        c.emit(0xc2,0x20);c.absolute(0xad,0x4302);c.emit(0x29,0,0x70,0x48,0xe2,0x20)
        c.store(0x420b,1);c.jump('dma_continue680')
        c.label('dma_retired680');c.emit(0x68,0xc9,0,0x50);c.branch(0xd0,'no_event680')
        c.emit(0xe2,0x20);c.store(0x601d,0xa5);c.emit(0xc2,0x20)
        c.label('no_event680');call(c,'service');c.jump('retired_continue680')
        start=labels['grant524']-ORIGIN
        assert body[start:start+5]==bytes.fromhex('a9018d0b42')
        c.labels['dma_continue680']=labels['grant524']+5
        body[start:start+5]=bytes([0x4c])+int(c.labels['dma_start680']&65535).to_bytes(2,'little')+bytes([0xea,0xea])
        end=labels['retired526']-ORIGIN
        assert body[end]==0x20
        c.labels['retired_continue680']=labels['retired526']+3
        body[end:end+3]=bytes([0x4c])+int(c.labels['dma_retired680']&65535).to_bytes(2,'little')
        body.extend(c.finish());symbols.update(c.labels)
        if extra_edit is not None:
            body,new_labels=extra_edit(body,symbols)
            symbols.update(new_labels)
        assert len(body)<=5984
        return bytes(body)
    result=build(base,out,edit_body=edit,allow_extension=True)
    (out/'labels.json').write_text(json.dumps(symbols,indent=2)+'\n')
    info=json.loads((out/'build.json').read_text())
    info.update(candidate='progress680',new_persistent_WRAM_B=0,extra_DMA_stack_B=2,
        body_free=5984-info['body_bytes'],progress_port='00601D',event_is_not_final_ACK=True)
    (out/'build.json').write_text(json.dumps(info,indent=2)+'\n')
    return info


def sha_bytes(b):
    import hashlib
    return hashlib.sha256(b).hexdigest()


def board(base,out,cpu):
    pins=json.loads(Path('analysis/entry665-verification.json').read_text())['board_inputs']['inputs']
    out.mkdir(parents=True,exist_ok=False)
    for name,digest in pins.items():
        source=base/name
        assert sha(source)==digest,name
        dest=out/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,dest)
    # QIP-relative generated inputs are included in the pinned manifest.
    shutil.copyfile(cpu/'sink-program.hex',out/'sink-program.hex')
    p=out/'nes_sink_bus165.sv';s=p.read_text()
    s=once(s,'output reg ack_write,','output reg map_progress,output reg ack_write,')
    s=once(s,"address[15:0]<=16'h601c","address[15:0]<=16'h601d")
    s=s.replace('ack_write<=0;ack_publish<=0;','map_progress<=0;ack_write<=0;ack_publish<=0;')
    s=once(s,"if(address_previous==24'h00601c&&data_previous==8'ha5)ack_publish<=1;",
        "if(address_previous==24'h00601c&&data_previous==8'ha5)ack_publish<=1;\n    if(address_previous==24'h00601d&&data_previous==8'ha5&&!stop&&!fault)map_progress<=1;")
    p.write_text(s,newline='\n')
    p=out/'nes_sink_spi165.sv';s=p.read_text()
    s=once(s,'input wire ack_publish,output reg fault','input wire ack_publish,map_progress,stop,output reg fault')
    s=once(s,'reg ack_valid,checking,check_wait;','reg ack_valid,checking,check_wait;\n reg progress;')
    s=once(s,"wire [7:0] flags={fault,4'd0,full,ack_valid,(used!=0)};",
        "wire [7:0] flags={fault,3'd0,(progress&&!stop&&!fault&&enable&&used==0&&ack_valid&&!checking),full,ack_valid,(used!=0)};")
    s=once(s,'accepted<=0;retired<=0;','progress<=0;accepted<=0;retired<=0;')
    # Last assignment wins: cancel/acceptance MUST dominate event publication.
    s=once(s,'if(crc_busy)begin',
        '''if(map_progress&&enable&&!fault&&!stop&&used==0&&ack_valid&&!checking)progress<=1;
   if(!enable||stop||fault||ack_write||ack_publish)progress<=0;
   if(crc_busy)begin''')
    s=once(s,"else begin lengths[accepted[1:0]]<=expected_length[8:0];accepted<=accepted+1'b1;end",
        "else begin progress<=0;lengths[accepted[1:0]]<=expected_length[8:0];accepted<=accepted+1'b1;end")
    p.write_text(s,newline='\n')
    p=out/'nes_sink_bridge165.sv';s=p.read_text()
    s=once(s,'wire ready,aw,ap;','wire ready,aw,ap,mp;')
    s=once(s,'.ack_publish(ap),.fault(fault));','.ack_publish(ap),.map_progress(mp),.stop(stop),.fault(fault));')
    s=once(s,'.ack_publish(ap),.pad_commit','.ack_publish(ap),.map_progress(mp),.pad_commit')
    p.write_text(s,newline='\n')
    changed={n:sha(out/n) for n in pins if sha(out/n)!=pins[n]}
    assert set(changed)=={'sink-program.hex','nes_sink_bus165.sv','nes_sink_spi165.sv','nes_sink_bridge165.sv'}
    (out/'inputs680.json').write_text(json.dumps(dict(base=pins,changed=changed),indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('base-arm','arm','base-client','client','base-board','board'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();arm(a.base_arm,a.arm);r=client(a.base_client,a.client);board(a.base_board,a.board,a.client)
    print(json.dumps({k:r[k] for k in ('body_bytes','body_free','prefix_B','encoded_B','physical_free_B')}))
