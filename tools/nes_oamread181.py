# SPDX-License-Identifier: MIT
"""Half-cycle primary OAM read candidate; no change to positive-edge writes."""
from pathlib import Path
import argparse,json,re,shutil
from nes_game147 import sha
from nes_clip178 import replace

def transform(s):
    start=s.index('module OAMEval(');end=s.index('endmodule',start);body=s[start:end]
    # Keep the asynchronous observation and synchronous savestate port intact.
    # The production collector does not consume that observation port.
    ports={'main':'oam_read_addr[7:3]','copy':'oam_row_last',
           'extra':'oam_addr_ex[5:1]','repeat':'oam_addr[7:3]'}
    prefetch='\n// Internal consumers sample at the positive edge. Addresses must settle\n// before the preceding negative edge; the fitter must check this half cycle.\n'
    for name,addr in ports.items():
        prefetch+=f'reg [63:0] primary_{name};\nalways @(negedge clk) primary_{name} <= {{'+','.join(f'oam_bank{i}[{addr}]' for i in reversed(range(8)))+'};\n'
    body=replace(body,'assign native_oam_data=oam_read(native_oam_address);',prefetch+'\nassign native_oam_data=oam_read(native_oam_address);')
    body=body.replace('oam_read(oam_read_addr)','primary_main[oam_read_addr[2:0]*8+:8]')
    for i in range(3):
        body=body.replace("oam_read({oam_addr[7:2], 2'b"+f'{i:02b}'+"})",f"primary_repeat[{{oam_addr[2],2'd{i}}}*8+:8]")
    body=body.replace("oam_read({oam_addr_ex, 2'b00})","primary_extra[{oam_addr_ex[0],2'b00}*8+:8]")
    body=body.replace("oam_read({oam_addr_ex,2'b00}+temp_index%4)","primary_extra[(oam_addr_ex[0]*4+temp_index%4)*8+:8]")
    for i in range(8):
        body=replace(body,f'oam_copy_write ? oam_bank{i}[oam_row_last] :',f'oam_copy_write ? primary_copy[{i*8}+:8] :')
    calls=re.findall(r'oam_read\(([^\n;]*)',body)
    assert len(calls)==3,calls # function declaration + native + savestate
    return s[:start]+body+s[end:]

def owned_storage(s):
    # Two independent writers may target different addresses on the same edge.
    # Replicate single-writer RAM per read port, select the last writer per byte.
    start=s.index('module OAMEval(');end=s.index('endmodule',start);b=s[start:end]
    for i in range(8):b=replace(b,f'reg [7:0] oam_bank{i}[0:31];',f'wire [7:0] oam_bank{i}[0:31];')
    lo=b.index('always @(posedge clk)begin\n if(Savestate_OAMWrEn');hi=b.index('// Per-byte priority',lo)
    assert b[lo:hi].count('always @(posedge clk)begin')==8
    b=b[:lo]+b[hi:]
    declaration='''
// A bit per byte names the latest writer. Same-byte collisions retain runtime
// priority; different-address writes both survive. No reset of OAM contents.
reg [7:0] primary_owner[0:31];
wire [63:0] primary_copy;
wire [7:0] primary_cpu_mask = oam_cpu_write ? (8'b1 << oam_read_addr[2:0]) : 8'd0;
wire [7:0] primary_run_mask = oam_copy_write ? 8'hff : primary_cpu_mask;
wire [63:0] primary_run_data = oam_copy_write ? primary_copy :
 {8{is_attr_byte ? (oam_din & 8'he3) : oam_din}};
wire [7:0] primary_ss_mask = Savestate_OAMWrEn ? (8'b1 << Savestate_OAMAddr[2:0]) : 8'd0;
integer owner_byte;
always @(posedge clk)begin
 for(owner_byte=0;owner_byte<8;owner_byte=owner_byte+1)begin
  if(primary_ss_mask[owner_byte])primary_owner[Savestate_OAMAddr[7:3]][owner_byte]<=0;
  if(primary_run_mask[owner_byte])primary_owner[oam_write_row][owner_byte]<=1;
 end
end
'''
    ports={'main':'oam_read_addr[7:3]','copy':'oam_row_last','extra':'oam_addr_ex[5:1]','repeat':'oam_addr[7:3]','state':'Savestate_OAMAddr[7:3]'}
    for name,addr in ports.items():
        old=f'reg [63:0] primary_{name};\nalways @(negedge clk) primary_{name} <= {{'+','.join(f'oam_bank{i}[{addr}]' for i in reversed(range(8)))+'};\n'
        if name!='state':b=replace(b,old,'')
        declaration+=f'''
(* ramstyle="M9K" *) reg [63:0] primary_ss_{name}[0:31],primary_run_{name}[0:31];
reg [63:0] primary_ss_q_{name},primary_run_q_{name};reg [7:0] primary_owner_q_{name};
{'' if name=='copy' else f'wire [63:0] primary_{name};'}
integer wb_{name};
always @(posedge clk)begin
 for(wb_{name}=0;wb_{name}<8;wb_{name}=wb_{name}+1)begin
  if(primary_ss_mask[wb_{name}])primary_ss_{name}[Savestate_OAMAddr[7:3]][wb_{name}*8+:8]<=Savestate_OAMWriteData;
  if(primary_run_mask[wb_{name}])primary_run_{name}[oam_write_row][wb_{name}*8+:8]<=primary_run_data[wb_{name}*8+:8];
 end
end
always @(negedge clk)begin
 primary_ss_q_{name}<=primary_ss_{name}[{addr}];
 primary_run_q_{name}<=primary_run_{name}[{addr}];
 primary_owner_q_{name}<=primary_owner[{addr}];
end
genvar rb_{name};
generate for(rb_{name}=0;rb_{name}<8;rb_{name}=rb_{name}+1)begin:read_{name}
 assign primary_{name}[rb_{name}*8+:8]=primary_owner_q_{name}[rb_{name}] ?
  primary_run_q_{name}[rb_{name}*8+:8] : primary_ss_q_{name}[rb_{name}*8+:8];
end endgenerate
'''
    # Preserve native observation and debug byte arrays. No producer uses this
    # native output in the selected board; MAP must establish whether it prunes.
    declaration+='genvar observed_row;\ngenerate for(observed_row=0;observed_row<32;observed_row=observed_row+1)begin:primary_observation\n'
    for i in range(8):declaration+=f' assign oam_bank{i}[observed_row]=primary_owner[observed_row][{i}] ? primary_run_main[observed_row][{i*8}+:8] : primary_ss_main[observed_row][{i*8}+:8];\n'
    declaration+='end endgenerate\n'
    b=replace(b,'assign native_oam_data=oam_read(native_oam_address);',declaration+'\nassign native_oam_data=oam_read(native_oam_address);')
    b=replace(b,'Savestate_OAMReadData  <= oam_read(Savestate_OAMAddr);','Savestate_OAMReadData  <= primary_state[Savestate_OAMAddr[2:0]*8+:8];')
    return s[:start]+b+s[end:]

def prepare(prior,out,storage='prefetch'):
    assert str(out).isascii() and not out.exists();out.mkdir(parents=True)
    m=json.loads((prior/'preparation.json').read_bytes());pins=m['sources']
    for n,h in pins.items():
        assert sha(prior/n)==h,n;p=out/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(prior/n,p)
    p=out/'rtl/ppu.sv';text=transform(p.read_text())
    if storage=='owned':text=owned_storage(text)
    else:assert storage=='prefetch'
    p.write_text(text,encoding='utf8',newline='\n')
    changed=[n for n in pins if sha(out/n)!=pins[n]];assert changed==['rtl/ppu.sv']
    m.update(baseline_oamread_sources=pins,sources={n:sha(out/n) for n in pins},changed=changed,
      oamread_generator_sha256=sha(Path(__file__)),storage=storage,adopted=False,hardware=False,
      contract='Internal row prefetch at negedge; consumers/writes at posedge. Requires actual half-cycle STA; native and savestate semantics retained.')
    (out/'preparation.json').write_text(json.dumps(m,indent=2)+'\n',encoding='utf8',newline='\n');return m

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ['prior','out']:p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--storage',choices=['prefetch','owned'],default='prefetch')
    a=p.parse_args();m=prepare(a.prior,a.out,a.storage);print(json.dumps(dict(changed=m['changed'],adopted=False)))
