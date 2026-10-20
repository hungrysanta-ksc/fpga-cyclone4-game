# SPDX-License-Identifier: MIT
"""Joint raw MASK and common source/plan/output SPI context on live output ARM."""
import inspect,shutil,json,csv
from pathlib import Path
import probe_nes_refill278 as prior
import probe_nes_refill267 as old
from nes_delta231 import BASE,ROOT,sha,once
from nes_joint280 import apply


def tb(s):
    s=s.replace('[48:0] link270','[106:0] link270')
    s=once(s,'tx[0:258],rx[0:258]','tx[0:1023],rx[0:1023]')
    s=s.replace('dut.core.encoder.base_addr>=4398','dut.core.encoder.base_addr>=4910')
    s=once(s,'if(dut.core.in_valid&&dut.core.in_ready)begin',
        'if(dut.core.in_valid&&dut.core.in_ready&&!dut.core.encoder.raw_mode)begin')
    a=s.index(' initial begin : consumer');b=s.index(' initial begin\n  if(!$value',a)
    s=s[:a]+r'''
 reg [31:0] source_cost280[0:1023],source_length280[0:1023],control280[0:5];
 reg [31:0] transaction_cost280[0:8191];
 reg [7:0] source_expected280[0:131071];integer source_at280=0;
 initial begin
  $readmemh("source-cost280.hex",source_cost280);$readmemh("source-length280.hex",source_length280);
  $readmemh("source-expected280.hex",source_expected280);$readmemh("control280.hex",control280);
  $readmemh("transaction-cost280.hex",transaction_cost280);
 end
 task exchange280(input reg pop,input reg final_ack);
  integer i,b,size;reg [7:0] c;
  begin
   for(i=0;i<1024;i++)tx[i]=0;
   tx[0]=final_ack?8'hd5:8'hd4;tx[1]=token[15:8];tx[2]=token[7:0];
   tx[3]=generation[7:0];tx[4]=generation[15:8];tx[5]=final_ack?3:pop;
   c=0;for(i=0;i<6;i++)c=c8(c,tx[i]);tx[6]=c;tx[7]=8'ha5;
   size=final_ack?8:13;
   #(transaction_cost280[token*5+(final_ack?2:pop?1:0)]*CPI*1000.0/84.0);
   #2000;ss=0;#2000;
   for(i=0;i<size;i++)begin
    rx[i]=0;
    for(b=7;b>=0;b--)begin
     mosi=tx[i][b];#190.476190476;sck=1;rx[i][b]=selected?miso:0;#190.476190476;sck=0;
    end
    if(i==9&&rx[8][0])size=15+rx[9];
   end
   #2000;ss=1;#2000;wirebytes+=size;
   if(!final_ack)begin
    c=0;for(i=8;i<12;i++)c=c8(c,rx[i]);
    if(rx[8][7:3]!==5'b10101||rx[8][2]!==0||c!==rx[12])$fatal(1,"exchange header %h crc%h/%h",rx[8],c,rx[12]);
    token={rx[10],rx[11]};length=rx[9];
    #(transaction_cost280[token*5+(rx[8][0]?4:3)]*CPI*1000.0/84.0);
    if(rx[8][0])begin
     if(!length||length>248)$fatal(1,"exchange length");
     crc=16'hffff;for(i=13;i<13+length;i++)begin
      if($isunknown(rx[i]))$fatal(1,"unknown SPI payload");crc=c16(crc,rx[i]);
     end
     if(crc!=={rx[13+length],rx[14+length]})$fatal(1,"exchange payload CRC");
     if(length!=source_length280[token])$fatal(1,"ARM trace block length");
     for(i=13;i<13+length;i++)begin
      if(rx[i]!==source_expected280[source_at280])$fatal(1,"ARM trace payload %0d",source_at280);
      source_at280++;
     end
     #(source_cost280[token]*CPI*1000.0/84.0);
    end else if(length!=0)$fatal(1,"empty length");
   end
  end
 endtask
 initial begin : consumer
  integer hf,k;reg ended,pop;
  wait(!reset);wait(first!=0);bf=$fopen("blocks.txt","w");hf=first;token=0;
  while(hf<=last)begin
   wait(enable);ended=0;pop=0;
   while(!ended)begin
    exchange280(pop,0);pop=0;
    if(rx[8][0])begin
     $fwrite(bf,"%0d %0d %0d ",hf,token,length);
     for(k=13;k<13+length;k++)$fwrite(bf,"%02x",rx[k]);$fwrite(bf,"\n");
     ended=length>=6&&rx[13+length-6]==255&&rx[13+length-5]==255&&rx[13+length-4]==0&&rx[13+length-3]==4;
     pop=1;blocks++;
    end
   end
   #(control280[5]*CPI*1000.0/84.0);
   exchange280(1,1);token++;acks++;hf++;
  end
  $fclose(bf);
 end
'''+s[b:]
    return s


def prepare(*args,**kwargs):
    src,pins=prior.prepare(*args,**kwargs);d=args[0];apply(d)
    p=d/'joint266_tb.sv';p.write_text(tb(p.read_text()),encoding='utf-8',newline='\n')
    # Replay measured ARM source-codec instructions at the verified block
    # boundary. Output ARM remains live. This is not a full RUN/source driver.
    evidence=Path('C:/Users/mohallo/AppData/Local/Temp/nes-joint280/arm04')
    from probe_nes_decode280 import chunks,records
    rows=list(csv.DictReader((evidence/'blocks.csv').open()))
    for name,field in [('source-cost280.hex','instructions'),('source-length280.hex','length')]:
        (d/name).write_text(' '.join(f'{int(r[field]):08x}' for r in rows)+'\n')
    blob=b''.join(b for f in range(905,976) for b in chunks(records(evidence/f'frame{f}.records')))
    (d/'source-expected280.hex').write_text(blob.hex(' ')+'\n')
    c=json.loads((evidence/'control.json').read_text())
    (d/'control280.hex').write_text(' '.join(f'{r["instructions"]:08x}' for r in c['cases'])+
        f' {c["complete_instructions"]:08x}\n')
    from probe_nes_arm264 import ARM,crc
    arm=ARM(evidence/'decoder.elf',None);costs=[]
    for token,row in enumerate(rows):
        for flags in (0,1,3):
            before=arm.instructions
            assert arm.call('prefix280',[0x20018000,token,int(row['frame'])-904,flags])==1
            costs.append(arm.instructions-before)
        for ready in (0,1):
            header=bytes([0xaa|ready,int(row['length']) if ready else 0,token>>8,token&255])
            arm.uc.mem_write(0x20018000,header+bytes([crc(header,8)]));before=arm.instructions
            assert arm.call('reply280',[0x20018000,token])==1
            costs.append(arm.instructions-before)
    (d/'transaction-cost280.hex').write_text(' '.join(f'{v:08x}' for v in costs)+'\n')
    for name in ('blocks.csv','control.json','decoder.elf','nes_decode280.c'):
        shutil.copyfile(evidence/name,d/('source-ARM-'+name));pins['source-ARM-'+name]=sha(evidence/name)
    for name in ['nes_joint280.py','nes_exchange280.inc','nes_source_exchange280.inc','probe_nes_refill280.py']:
        shutil.copyfile(ROOT/'tools'/name,d/name);pins[name]=sha(ROOT/'tools'/name)
    return src,pins


def main():
    ns=dict(old.__dict__);ns.update(prepare=prepare,build=prior.build,worker=prior.worker,__file__=__file__,__doc__=__doc__)
    exec(compile(inspect.getsource(old.main),'refill280-main','exec'),ns);ns['main']()


if __name__=='__main__':main()
