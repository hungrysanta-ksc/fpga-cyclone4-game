"""Reuse E0 snapshot storage as the CRC/serial cursor and share ACK bus decode."""
import argparse,json,shutil
from pathlib import Path
from nes_raw506 import once,sha

def prepare(base,out,owner=False,compact=False,length=False):
    proof=json.loads(Path('analysis/owner688-board.json').read_text())
    pins={n:proof['inputs']['changed'].get(n,h) for n,h in proof['inputs']['base'].items()}
    out.mkdir(parents=True,exist_ok=False)
    for n,h in pins.items():
        assert sha(base/n)==h,n
        p=out/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(base/n,p)
    p=out/'nes_sink_bus165.sv';s=p.read_text()
    s=once(s,"wire control=local_bank&&(address[15:0]<=16'h6005&&address[15:0]>=16'h6000 || address[15:0]>=16'h6010&&address[15:0]<=16'h601d);",
        "wire control=address[23:5]==19'h00300&&(address[4:0]<=5'd5||(address[4]&&address[3:0]<=4'd13));")
    start=s.index("    if(address_previous>=24'h006010")
    end=s.index('\n   end',start)
    s=s[:start]+'''    // One synchronized ACK/progress aperture; no raw bus event is published.
    if(address_previous[23:4]==20'h00601)begin
     if(address_previous[3:0]<12)begin
      ack_write<=1;ack_index<=address_previous[3:0];ack_byte<=data_previous;
     end else if(data_previous==8'ha5)begin
      if(address_previous[3:0]==12)ack_publish<=1;
      if(address_previous[3:0]==13&&!stop&&!fault)map_progress<=1;
     end
    end'''+s[end:]
    p.write_text(s,newline='\n')
    p=out/'nes_sink_spi165.sv';s=p.read_text()
    s=once(s,"wire [7:0] flags={fault,3'd0,(progress&&!stop&&!fault&&enable&&used==0&&ack_valid&&!checking),full,ack_valid,(used!=0)};",
        "wire idle_receipt=enable&&!fault&&used==0&&ack_valid&&!checking;\n wire [7:0] flags={fault,3'd0,(progress&&!stop&&idle_receipt),full,ack_valid,(used!=0)};")
    s=once(s,'if(map_progress&&enable&&!fault&&!stop&&used==0&&ack_valid&&!checking)progress<=1;',
        'if(map_progress&&!stop&&idle_receipt)progress<=1;')
    s=once(s,"if(command==8'he0&&byte_count>=1&&byte_count<=19)reply=snapshot[8*(19-byte_count)+:8];",
        "if(command==8'he0&&byte_count>=1&&byte_count<=19)reply=byte_count==1?8'hf7:snapshot[151:144];")
    s=once(s,'''   if(crc_busy)begin
    status_crc<=crc8(status_crc,snapshot[151-crc_position*8-:8]);
    if(crc_position==17)begin snapshot[7:0]<=crc8(status_crc,snapshot[151-crc_position*8-:8]);crc_busy<=0;end
    else crc_position<=crc_position+1'b1;
   end''','''   // Rotate eighteen immutable status bytes through the existing CRC tap.
   // A nineteenth rotation installs CRC and restores byte order. The first
   // SPI byte is the constant F7 while the internal scan completes.
   if(crc_busy)begin
    snapshot<={snapshot[143:0],crc_position==18?status_crc:snapshot[151:144]};
    if(crc_position==18)crc_busy<=0;
    else begin status_crc<=crc8(status_crc,snapshot[151:144]);crc_position<=crc_position+1'b1;end
   end''')
    s=once(s,"     end else if(command==8'he1)begin", "     end else if(command==8'he0)begin\n      snapshot<={snapshot[143:0],snapshot[151:144]};\n     end else if(command==8'he1)begin")
    s=once(s,"buffer[{accepted[1:0],8'd0}+byte_count-1'b1]<=incoming;", "buffer[{accepted[1:0],(byte_count[7:0]-8'd1)}]<=incoming;")
    if compact:
        # F7 is constant; the CRC byte already lives in status_crc. Keep only
        # the seventeen changing bytes, not two duplicate serial registers.
        s=once(s,'reg [151:0] snapshot;', 'reg [135:0] snapshot;')
        s=once(s,"reply=byte_count==1?8'hf7:snapshot[151:144];", "reply=byte_count==1?8'hf7:byte_count==19?status_crc:snapshot[135:128];")
        start=s.index('   // Rotate eighteen immutable')
        end=s.index('   if(ack_write',start)
        s=s[:start]+'''   // Seventeen changing bytes share one CRC/serial rotation. F7 has
   // already seeded CRC; the CRC register supplies the last response byte.
   if(crc_busy)begin
    snapshot<={snapshot[127:0],snapshot[135:128]};
    status_crc<=crc8(status_crc,snapshot[135:128]);
    if(crc_position==16)crc_busy<=0;else crc_position<=crc_position+1'b1;
   end
'''+s[end:]
        s=once(s,"snapshot[151:144]<=8'hf7;snapshot[143:136]<=flags;", 'snapshot[135:128]<=flags;')
        s=once(s,'snapshot[135:120]<=accepted;snapshot[119:104]<=retired;snapshot[7:0]<=0;', 'snapshot[127:112]<=accepted;snapshot[111:96]<=retired;')
        s=once(s,'status_crc<=0;crc_position<=0;crc_busy<=1;', "status_crc<=crc8(8'd0,8'hf7);crc_position<=0;crc_busy<=1;")
        s=once(s,'snapshot[103-j*8-:8]', 'snapshot[95-j*8-:8]')
        s=once(s,'      snapshot<={snapshot[143:0],snapshot[151:144]};', '      if(byte_count>=2&&byte_count<=18)snapshot<={snapshot[127:0],snapshot[135:128]};')
    if length:
        # Legal E1 payloads are at most240B. Preserve the high-byte rejection
        # separately, rather than carrying eight invalid address bits through
        # every RAM/CRC/end comparison. Invalid records never publish credit.
        s=once(s,'reg [7:0] shift,command;reg [15:0] payload_size,request_crc,received_crc;',
            'reg [7:0] shift,command,payload_size;reg payload_high;reg [15:0] request_crc,received_crc;')
        s=once(s,"wire [16:0] expected_length={1'b0,payload_size}+17'd16;", "wire [8:0] expected_length={1'b0,payload_size}+9'd16;")
        s=s.replace('payload_size<=0;', 'payload_size<=0;payload_high<=0;')
        s=once(s,'payload_size>240||', 'payload_high||payload_size>240||')
        s=once(s,'payload_size[7:0]<=incoming;', 'payload_size<=incoming;')
        s=once(s,'payload_size[15:8]<=incoming;', "payload_high<=incoming!=0;")
    p.write_text(s,newline='\n')
    if owner:
        # STA689: command[7:4] -> collision -> STOP -> E0 and DMA progress.
        # Capture ownership on the existing command edge, no added cycle.
        p=out/'nes_rom_spi.sv';s=p.read_text()
        s=once(s,"wire ours=command[7:4]==4'h6;",'reg ours;')
        s=once(s,'assign spi_selected=!reset && !SPI_SS && ours && byte_count!=0;',
            'assign spi_selected=!reset && !SPI_SS && ours;')
        s=s.replace('begin command<=0;offset_zero_command<=0;', 'begin ours<=0;command<=0;offset_zero_command<=0;')
        s=once(s,'   command<=incoming;',"   ours<=incoming[7:4]==4'h6;command<=incoming;")
        p.write_text(s,newline='\n')
        # The token is consumed only with the registered consume strobe.
        # Sample staged continuously on the same edge as before; remove the
        # long reset/eligibility decode from thirty-two data enables.
        p=out/'nes_bulk_control194.sv';s=p.read_text()
        s=once(s,'   consume<=0;command_error<=0;', '   consume_token<=staged;consume<=0;command_error<=0;')
        s=once(s,'consume<=1;consume_token<=staged;', 'consume<=1;')
        p.write_text(s,newline='\n')
    changed={n:sha(out/n) for n,h in pins.items() if sha(out/n)!=h}
    expected={'nes_sink_bus165.sv','nes_sink_spi165.sv'}
    if owner:expected|={'nes_rom_spi.sv','nes_bulk_control194.sv'}
    assert set(changed)==expected
    (out/'inputs689.json').write_text(json.dumps(dict(base=pins,changed=changed,owner=owner,compact=compact,length=length,ARM='unchanged688',CPU='unchanged685',constraints_changed=False,seed_changed=False),indent=2)+'\n',newline='\n')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--base',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--owner',action='store_true');p.add_argument('--compact',action='store_true');p.add_argument('--length',action='store_true')
    a=p.parse_args();prepare(a.base,a.out,a.owner,a.compact,a.length)
