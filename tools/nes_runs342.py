# SPDX-License-Identifier: MIT
"""Single region run source; removes MASK/SHIFT encoding, retains independent checks."""
import binascii,struct,re
from nes_delta231 import once
import nes_hybrid340 as old

def encode342(before,new,raw,prior_raw,serial,generation):
 ref=old.encode340(before,new,raw,prior_raw,serial,generation);h=bytearray(ref[0]);h[2]=4
 rr=[bytes(h)];spans=expanded=0
 for rid,(at,n) in enumerate(old.REGIONS):
  a=(prior_raw or bytes(len(raw))) if rid==8 else before[at:at+n]
  b=raw if rid==8 else new[at:at+n]
  items=old.runs(rid,a,b,bool(h[3]&(2 if rid==8 else 1)));rr+=items
  if rid<7:spans+=len(items);expanded+=sum((r[3]&63)+1 for r in items)
  if rid==6:rr.append(b'\xff\xff\0\3'+struct.pack('<HHH',spans,expanded,0))
 rr.append(b'\xff\xff\0\4\0\0');out=[];c=65535
 for r in rr:
  tail=r[:4] in (b'\xff\xff\0\3',b'\xff\xff\0\4');c=binascii.crc_hqx(r[:-2] if tail else r,c);out.append(r[:-2]+struct.pack('<H',c) if tail else r)
 return out

def decoder():
 s=old.decoder().replace('p[2]!=3','p[2]!=4').replace('s->blocks!=32','s->ends[0]!=2112').replace('p[0]>=65','p[0]>=64')
 a=s.index('  }else{\n   unsigned index=p[0]&127,at,len;')
 # End of old MASK/SHIFT branch; retain common CRC and framing code.
 # Locate exact common suffix by original decoder text.
 # inspect via structural brace scan instead of guessing suffix.
 opening=s.index('{',a);depth=1;i=opening+1
 while depth:
  if s[i]=='{':depth+=1
  elif s[i]=='}':depth-=1
  i+=1
 s=s[:a]+'  }else return reject();'+s[i:]
 return s

def apply(d):
 old.apply(d);p=d/'nes_core257.sv';s=p.read_text()
 s=s.replace('reg [10:0] offset340','reg [11:0] offset340').replace("{5'd0,offset340[10:8]}","{4'd0,offset340[11:8]}")
 s=s.replace('2:header_byte=3;','2:header_byte=4;').replace('{H,MASK,SHIFT,GEO,ENDREC,RUN340}','{H,GEO,ENDREC,RUN340}')
 s=s.replace('region340!=0&&region340!=3&&run340!=0&&','region340!=3&&run340!=0&&')
 a=s.index('  if(kind==MASK)a_addr=');b=s.index('  if(kind==RUN340)',a);s=s[:a]+s[b:]
 a=s.index('   FSTORE:if(region340==0)begin');b=s.index('    a_addr={2\'d0,run340}',a);s=s[:a]+'   FSTORE:begin\n'+s[b:]
 a=s.index('  if(kind==MASK&&');b=s.index('  if(kind==RUN340)',a);s=s[:a]+s[b:]
 a=s.index(' task automatic next_block;');b=s.index(' task automatic emit_run340',a);s=s[:a]+s[b:]
 s=s.replace('end else if(region340!=0)begin\n     if(stop_run340)', 'end else begin\n     if(stop_run340)')
 a=s.index('    end else begin\n     cursor<=cursor+1\'b1;if(changed)diff_count');b=s.index('    REQUEST:',a);s=s[:a]+'    end\n'+s[b:]
 s=s.replace('H:state<=FETCH;MASK,SHIFT:next_block();GEO:', 'H:state<=FETCH;GEO:')
 # No retained MASK/SHIFT datapath or mask RAM write arbitration.
 for line in s.splitlines():
  if 'wire [7:0] mask_next=' in line or 'wire shift_ok=' in line:s=s.replace(line+'\n','')
 names=['mask_bytes','mask_acc','old1','old2','new1','new2','edge0','edge1','left_row','right_row','shift_left','block_id','row_i','row_size','diff_count']
 # Remove old declarations separately, then their reset-only assignments.
 s=s.replace(' reg [3:0] mask_bytes;reg [7:0] mask_acc,new_byte,old1,old2,new1,new2,edge0,edge1;',' reg [7:0] new_byte;')
 s=s.replace('reg base_valid,cold,raw_mode,left_row,right_row,shift_left;','reg base_valid,cold,raw_mode;')
 s=s.replace('BLOCKEND,','').replace(' reg [6:0] block_id,row_i,row_size,diff_count;','')
 a=s.index(' reg mask_pending278;');b=s.index(' assign ram_b_addr=',a)
 s=s[:a]+" assign ram_a_addr={1'b1,a_addr};\n assign ram_a_we=live&&a_we;assign ram_a_w=a_w;\n"+s[b:]
 for n in names:s=re.sub(r'\b'+n+r'<=.*?;','',s)
 # Remaining unused declarations may be combined with live declarations; harmless
 # declarations are pruned, but no active expression may reference removed state.
 p.write_text(s,newline='\n')

def host(d):
 old.host(d)
 p=d/'nes_mux260.sv';s=p.read_text()
 s=s.replace(' reg run_zero313;','')
 s=s.replace('reg [8:0] manifest_byte313;','')
 # Fields have mutually exclusive metadata versus DMA production lifetimes.
 s=s.replace('run_zero313','zero325').replace('manifest_byte313','expanded325[8:0]')
 s=s.replace('expanded325[8:0][8]','expanded325[8]').replace('expanded325[8:0][7:0]','expanded325[7:0]')
 decl=' reg [31:0] seed325;reg [11:0] expanded325;reg zero325;'
 s=once(s,decl,'');s=once(s,' wire requirements313=',decl+'\n wire requirements313=')
 # Shared synchronous queue reader removes duplicated port scheduling.
 a=s.index('     MCAP313:begin');b=s.index('     MISSUE313:',a)
 body=s[a:b].removeprefix('     MCAP313:begin\n').removesuffix('     end\n');s=s[:a]+s[b:]
 s=once(s,'     MREAD313:if(header[0]!=3)state<=MCAP313;else if(range_ready)state<=MSEALWAIT313;\n','')
 s=once(s,'MREAD313=42,MCAP313=43,','MREAD313=PREAD,MCAP313=PCAP,')
 s=once(s,' wire metadata313=(', ' wire metadata313=(header[0]==15||header[0]==10||header[0]==11||header[0]==3)&&(')
 s=once(s,'     PREAD:state<=PCAP;','     PREAD:if(header[0]!=3)state<=PCAP;else if(range_ready)state<=MSEALWAIT313;')
 s=once(s,'     PCAP:begin\n      if(header[0]==1)','     PCAP:begin\n      if(metadata313)begin\n'+body+'      end else if(header[0]==1)')
 p.write_text(s,newline='\n')
