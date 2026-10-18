# SPDX-License-Identifier: MIT
"""Read-only instrumentation of encoder240; never an installable RTL variant.

Executed writes are measured, while read masks deliberately include both
branches of each state. The only masked reads are the documented row-history
warmup and read addresses unused by the current RAM operation. These masks
support a conservative register-file access budget, not an instruction-level
implementation or a formal liveness proof.
"""
import re

# Keep admission snapshot, continuous lease check, independent query cursor,
# input capture, checksum and published-record fields in registers. Moving
# these requires a separate protocol change/proof, not a latency assumption.
FIELDS = dict(row_start=13, lit_at=13, byte_at=13, group_start=13, raw_limit=13,
              row_i=8, row_size=8, lit_len=8, lit_used=8, rows=8, build_i=8,
              gap=3, cheap_cost=4, cheap_i=4, spans=16, expanded=16,
              old_byte=8, old1=8, old2=8, new1=8, new2=8, xor_byte=8)
PINNED = dict(epoch=32, base_serial=32, generation=16, cursor=13,
              checksum=16, new_byte=8, rec_i=8, record_length=8)
PAYLOAD = {'O': (0,66), 'C': (80,12), 'M': (96,8),
           'N': (128,66), 'P': (208,20), 'L': (256,240)}


def inventory(source):
    states = re.search(r'typedef enum logic \[6:0\] \{(.*?)\} state_t;', source, re.S)[1]
    states = [s.strip() for s in states.split(',')]
    assert len(states) == 60
    start = source.index('    IDLE:if(start)begin')
    end = source.index('    default:begin fault<=6;', start)
    body = source[start:end]
    heads = list(re.finditer(r'^    ([A-Z][A-Z0-9_]*):', body, re.M))
    state_body = {h[1]: body[h.end(): heads[i+1].start() if i+1 < len(heads) else len(body)]
                  for i,h in enumerate(heads)}
    assert len(state_body) == 58
    reads = {}
    for state,text in state_body.items():
        text = re.sub(r'\b\w+\s*<=', '', text)  # LHS is not an operand read.
        reads[state] = {n for n in FIELDS if re.search(r'\b'+n+r'\b',text)}
    # Scratch/RAM routing outside the sequential case.
    extra = dict(HEADER='build_i', FSTORE='row_i lit_len',
                 ROWREAD='row_i', ROWVALUE='row_i', MAPLREAD='row_i', MAPLVALUE='row_i',
                 MASKREAD='row_i', MASKVALUE='row_i', MASKCHECK='row_i',
                 MASKSETREAD='row_i', MASKSETVALUE='row_i', MASKSETWRITE='row_i xor_byte',
                 RASTERREAD='row_i', RASTERVALUE='row_i', LAPPEND='lit_len',
                 LH0='cheap_cost lit_at', LH1='cheap_cost lit_at', LH2='cheap_cost lit_used',
                 COPYREAD='build_i cheap_cost', COPYWRITE='build_i cheap_cost',
                 SHIFTBUILD='build_i row_start', RASTERBUILD='build_i group_start rows',
                 CHEAPREAD='cheap_i', CHEAPVALUE='cheap_i',
                 GEOTRAILER='build_i spans expanded', ENDTRAILER='build_i spans expanded',
                 RAWWAIT='lit_len', SREAD='cheap_i', SBYTE='cheap_i')
    for state,names in extra.items(): reads[state].update(names.split())
    payload = {a for at,n in PAYLOAD.values() for a in range(at,at+n)}
    assert len(payload) == 412
    # Use holes already outside every payload view; no new RAM/width claim.
    free = [a for a in range(104,128)] + [a for a in range(228,256)]
    layout = {}; p = 0
    for name,width in FIELDS.items():
        n=(width+7)//8; layout[name]=free[p:p+n];p+=n
        assert len(layout[name])==n and not payload.intersection(layout[name])
    assert len({a for v in layout.values() for a in v})==p
    return dict(states=states,reads={k:sorted(v) for k,v in reads.items()},
                fields=FIELDS,pinned=PINNED,payload=PAYLOAD,layout=layout,
                operand_bytes=p,operand_bits=sum(FIELDS.values()),
                scratch_payload_bytes=len(payload),scratch_unused_bytes=512-len(payload))


def instrument(source):
    inv=inventory(source); names=list(FIELDS); n=len(names)
    # No synthesis run may accidentally accept this observer as a candidate.
    decl = ['// SIMULATION-ONLY NES242 operand observer. Production240 stays byte-exact.',
            'reg [63:0] prof_writes,prof_reads,prof_initialized=0;',
            'integer prof_alu,prof_fd=0,prof_index,prof_frame=0;',
            'longint unsigned prof_hist[longint unsigned];',
            'longint unsigned prof_key;',
            'task automatic prof_dump(input integer frame_id);',
            ' longint unsigned key; begin',
            ' if(!prof_fd)begin prof_fd=$fopen("operands.csv","w");',
            ' $fwrite(prof_fd,"frame,state,reads,writes,alu_bytes,ram_ops,cycles\\n");end',
            ' foreach(prof_hist[key])$fwrite(prof_fd,"%0d,%0d,%x,%x,%0d,%0d,%0d\\n",',
            f' frame_id,key[5:0],key[{6+n-1}:6],key[{6+2*n-1}:{6+n}],',
            f' key[{6+2*n+7}:{6+2*n}],key[{6+2*n+10}:{6+2*n+8}],prof_hist[key]);',
            ' $fflush(prof_fd);prof_hist.delete();end endtask',
            'task automatic prof_begin;',
            ' begin prof_writes=0;prof_alu=0;prof_reads=0;case(state)']
    for state,reads in inv['reads'].items():
        mask=sum(1<<names.index(x) for x in reads)
        decl.append(f' {state}:prof_reads=64\'h{mask:x};')
    decl += [' default:prof_reads=0;endcase',
             ' if(state==IDLE&&!start)prof_reads=0;',
             ' if(state==ROWVALUE)begin']
    def clear(field): return f"prof_reads[{names.index(field)}]=0;"
    decl += [f' if(row_i==0)begin {clear("old1")}{clear("new1")}end',
             f' if(row_i<2)begin {clear("old2")}{clear("new2")}end',
             ' end',
             f' if((state==SREAD||state==SBYTE)&&send_return!=S_CHEAP){clear("cheap_i")}',
             f' if(state==FSTORE)begin if(cold)begin {clear("row_i")}end else begin {clear("lit_len")}end end',
             # ENDTRAILER emits only header4 + CRC2, not spans/expanded.
             f' if(state==ENDTRAILER)begin {clear("spans")}{clear("expanded")}end',
             ' end endtask',
             'task automatic prof_end;',
             ' integer ram_ops;begin',
             ' if(reset)prof_initialized=0;',
             ' else if(!fault&&!abort_source&&(state!=IDLE||start))begin',
             ' if((prof_reads&~prof_initialized)!=0)$fatal(1,"OPERAND242 uninitialized state=%0d reads=%x init=%x",state,prof_reads,prof_initialized);',
             ' prof_initialized=prof_initialized|prof_writes;',
             # Count logical accesses only, not the unconditionally clocked idle reads.
             ' ram_ops=(a_we?1:0)+(b_we?1:0);',
             ' case(state)',
             ' ROWVALUE,MAPLVALUE,MASKVALUE,MASKSETVALUE,RASTERVALUE:ram_ops=ram_ops+2;',
             ' SBYTE,COPYWRITE,MASKDECIDE,CHEAPVALUE:ram_ops=ram_ops+1;',
             ' default:begin end endcase',
             " prof_key=64'(state);",
             f' prof_key=prof_key|(prof_reads<<6)|(prof_writes<<{6+n})|',
             f" (64'(prof_alu)<<{6+2*n})|(64'(ram_ops)<<{6+2*n+8});",
             ' if(prof_hist.exists(prof_key))prof_hist[prof_key]++;else prof_hist[prof_key]=1;',
             ' end end endtask']
    assert 6+2*n+11<=64
    # Mark actual executed assignments, including writes inside emit/resume tasks.
    # Only selected data fields: PC/flags/admission/CRC are unchanged.
    def mark(m):
        field,rhs=m.group(1),m.group(2)
        if field not in FIELDS:return m[0]
        # Arithmetic/XOR assignment cost is a byte-ALU opportunity count, NOT
        # the count of instructions needed for conditions, loads or addresses.
        cost=(FIELDS[field]+7)//8 if re.search(r'[+^]|(?<![\w\'])-(?!\w*\')',rhs) else 0
        return f'begin prof_writes[{names.index(field)}]=1;prof_alu=prof_alu+{cost};{field}<={rhs};end '
    transformed=re.sub(r'\b(\w+)\s*<=\s*([^;]+);',mark,source)
    needle=' always @(posedge clk)begin\n  if(reset)begin'
    assert transformed.count(needle)==1
    transformed=transformed.replace(needle,'\n'.join(decl)+'\n always @(posedge clk)begin\n  prof_begin();\n  if(reset)begin')
    end='  end\n end\nendmodule'
    assert transformed.endswith(end+'\n')
    transformed=transformed[:-len(end+'\n')]+'  end\n  prof_end();\n end\nendmodule\n'
    return transformed,inv
