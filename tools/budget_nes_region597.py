"""597 isolated resource ledger and single-page packet producer timing."""
import argparse
import json
from functools import partial
from pathlib import Path

from check_nes_region595 import ROOT, RTL, Link, mapping, simulate, sources, sha, exercise
from map_nes_budget596 import replace, variants


def pack(s):
    s = replace(s,' reg [7:0] ordinal,',' reg [7:0] page_end;\n reg [7:0] ordinal,')
    size = ' wire [7:0] block_items=limit-cursor<32 ? limit-cursor : 32;'
    s = replace(s, size, size+'''
 wire [8:0] literal_bytes = width==7 ? ({1'b0,block_items}<<3)-block_items :
                            width==4 ? ({1'b0,block_items}<<2) : block_items;''')
    s = replace(s,'kind<=1;cursor<=0;phase<=2;', 'kind<=1;cursor<=0;phase<=2;page_end<=2;')
    s = replace(s,'phase<=3;kind<=6;', 'phase<=3;page_end<=2;kind<=6;')
    s = replace(s,'if(kind==5 || kind==6)begin state', '''if((kind==5 || kind==6) && page_end!=2)begin seal_page(NONMAP,page_end);page_end<=2;end
     else if(kind==5 || kind==6)begin state''')
    s = replace(s,'end else begin chunk<=block_items;left<=block_items;addr<=5;',
                '''end else if({1'b0,page_end}+9'd3+literal_bytes>9'd254)begin seal_page(NONMAP,page_end);page_end<=2;end
     else begin chunk<=block_items;left<=block_items;addr<=page_end+3;''')
    s = replace(s,'write_addr=2+pos;', 'write_addr=page_end+pos;')
    return replace(s,'if(pos==2)seal_page(NONMAP,(linear_run||equal_run)?5+width:addr);',
                   'if(pos==2)begin page_end<=(linear_run||equal_run)?page_end+3+width:addr;state<=NONMAP;end ')


def value_header(s):
    # Keep the last complete value stable until the next query response.
    s = replace(s,'value,first,previous;', 'value;')
    s = replace(s,'first<=data;previous<=data;', '')
    s = replace(s,'data==first;', 'data==value;')
    s = replace(s,'data==raster_next(previous);previous<=data;', 'data==raster_next(value);')
    s = replace(s,'value<=value>>8;', '')
    s = replace(s,' reg [15:0] field;', ' wire [7:0] lane_byte=value[8*lane[2:0]+:8];\n reg [15:0] field;reg [7:0] field_hi;')
    s = s.replace('value[7:0]', 'lane_byte')
    s = replace(s,'pos[0]?field[15:8]:field[7:0]', 'pos[0]?field_hi:field[7:0]',4)
    return replace(s,' wire [7:0] block_items', ''' always @(posedge clk) if(!pos[0])field_hi<=field[15:8];
 wire [7:0] block_items''')


def response(s):
    # Keep the first-byte snapshot. Fold its CRC as the reply is shifted out.
    s = replace(s,'wire [7:0] status_crc='+s.split('wire [7:0] status_crc=')[1].split(';')[0]+';',
                'reg [7:0] status_crc;')
    s = replace(s,'reg [55:0] snapshot;', 'reg [31:0] snapshot;')
    s = replace(s,'1:reply=snapshot[55:48];2:reply=snapshot[47:40];3:reply=snapshot[39:32];',
                "1:reply=8'hd6;2:reply=snapshot[31:24];3:reply=snapshot[23:16];")
    s = replace(s,'4:reply=snapshot[31:24];5:reply=snapshot[23:16];6:reply=snapshot[15:8];7:reply=snapshot[7:0];',
                '4:reply=snapshot[15:8];5:reply=0;6:reply=snapshot[7:0];7:reply=status_crc;')
    s = replace(s,"snapshot<={8'hd6,flags,token,8'd0,used,status_crc};",
                'snapshot<={flags,token,used};status_crc<=0;')
    s = replace(s,'if(byte_at<6)crc8_calc', "if(byte_at>=1 && byte_at<=6 && cmd!=8'hd1)status_crc<=c8(status_crc,reply);\n     if(byte_at<6)crc8_calc")
    s = replace(s,'crc_read,crc_cmd,','crc_read,')
    s = replace(s,"crc_read<=16'hffff;crc_cmd<=16'hffff;", "crc_read<=16'hffff;")
    s = replace(s,"crc8_calc<=0;crc_cmd<=16'hffff;", 'crc8_calc<=0;')
    return s.replace('crc_cmd','crc_read')


def free_producers(nes,spi):
    # Sensitivity cut only. Add independent oracle inputs, so synthesis cannot
    # exploit a constant header/status or correlate them with real SPI traffic.
    nes = replace(nes,'module nes_region595(input wire clk', '''module nes_region595(input wire [7:0] external_header,external_status,
 input wire external_equal,external_linear,input wire clk''')
    nes = replace(nes,'data==value;', 'external_equal;')
    nes = replace(nes,'data==raster_next(value);', 'external_linear;')
    nes = replace(nes,'pos[0]?field_hi:field[7:0]', 'external_header',4)
    nes = replace(nes,'nes_spi595 spi(.clk','nes_spi595 spi(.external_status(external_status),.clk')
    spi = replace(spi,'module nes_spi595(input wire clk','module nes_spi595(input wire [7:0] external_status,input wire clk')
    start = spi.index('end else case(byte_at)')
    end = spi.index('endcase',start)+len('endcase')
    return nes, spi[:start]+'end else reply=external_status;'+spi[end:]


def build(name):
    def emit(d):
        sources(d)
        nes,spi = [d/f for f in RTL]
        body = nes.read_text()
        if name not in ('control','packed'):
            body = variants(body)['joint']
            if name in ('value_header','joint_core','joint','free'):
                body = value_header(body)
            if name in ('response','joint_core','joint','free'):
                host = response(spi.read_text())
                if name=='free':
                    body,host=free_producers(body,host)
                spi.write_bytes(host.encode())
        if name in ('packed','joint','free'):
            body = pack(body)
        nes.write_bytes(body.encode())
    return emit


def instrument(d, out):
    p=d/'nes_region595_tb.sv'
    s=p.read_text()
    p.write_text(replace(s,'endmodule',''' integer tick597=0,start597=0;reg active597=0;
 always @(posedge clk)begin
  tick597<=tick597+1;
  if(reset)active597<=0;
  else if(dut.state==dut.NONMAP && !active597)begin start597<=tick597;active597<=1;end
  else if(dut.state==dut.SEND && dut.seal_ready)begin
   if(active597 && dut.after_pop==dut.NONMAP)
    $display("PAGE597 %0d %0d %0d %0d",generation,dut.phase,dut.length,tick597-start597);
   active597<=0;
  end
 end
endmodule'''))


class StatusLink(Link):
    def spi(self,tx):
        rx=super().spi(tx)
        self.ops[-1].append(rx[2] if tx[0]==0xd0 else None)
        return rx


def measure_status(d,a,link):
    result=exercise(d,a,link,normal_only=True)
    offset=0
    result['polls']=[]
    for frame in result['frames']:
        counts=dict(pop_confirm=0,request_confirm=0,prepare_confirm=0,ready=0,empty=0)
        previous=None
        for op,_,_,flags in link.ops[offset:offset+frame['calls']]:
            if op==0xd0:
                owner={0xd2:'pop_confirm',0xd4:'request_confirm',0xd3:'prepare_confirm'}.get(previous)
                counts[owner or ('ready' if flags&1 else 'empty')]+=1
            previous=op
        offset+=frame['calls']
        result['polls'].append(counts)
    assert offset==len(link.ops)
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode',choices=('map','map-combined','map-free','sim','poll'))
    p.add_argument('out',type=Path)
    p.add_argument('--arm',type=Path)
    p.add_argument('--archive',type=Path)
    a=p.parse_args()
    a.last=906
    a.out.mkdir(exist_ok=False,parents=True)
    pins=json.loads((ROOT/'analysis/region595-verification.json').read_bytes())['RTL']
    assert all(sha(ROOT/'rtl'/f)==pins[f] for f in RTL)
    names={'map':('value_header','response'),'map-combined':('packed','joint_core','joint'),
           'map-free':('free',),'sim':('packed','control'),'poll':('packed','control')}[a.mode]
    for name in names:
        dest=a.out/name
        dest.mkdir()
        if a.mode.startswith('map'):
            mapping(dest,build(name))
        else:
            assert a.arm and a.archive
            args=argparse.Namespace(**{**vars(a),'out':dest})
            if a.mode=='poll':
                simulate(args,build(name),runner=measure_status,link_type=StatusLink)
            else:
                simulate(args,build(name),instrument,partial(exercise,normal_only=name=='control'))


if __name__=='__main__':
    main()
