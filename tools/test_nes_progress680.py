"""Actual M4/65816 replay with board-tested advisory E0 progress semantics.

The SPI endpoint remains a timing model, separately checked against actual RTL.
DMA notifications originate only in execution of the new CPU store, never in
ARM receipt or an inferred idle interval. Eight host clocks charge publication.
"""
import inspect,json,math,runpy,textwrap
from unittest.mock import patch
import test_nes_raw506_joint as joint
import nes_transfer512_rpc as transport
import trace_nes_map527 as checked
from nes_raw506 import once


def lua(original):
    def build(a):
        original(a)
        p=a.out/'capture.lua';s=p.read_text(encoding='utf8')
        s=once(s,'local consumed={};local retiredEvents={};',
            'local consumed={};local retiredEvents={};local progressEvents={};')
        s=once(s,"  f:write('\\n');f:close();consumed={};retiredEvents={}",
            """  f:write('\\n')
  for _,e in ipairs(progressEvents)do f:write(string.format('%d:%d;',e[1],e[2]))end
  f:write('\\n');f:close();consumed={};retiredEvents={};progressEvents={} """)
        s=once(s,'emu.addMemoryCallback(function()rpc()end,emu.callbackType.exec,0x7e0000,0x7effff)',
            '''local progressLog=assert(io.open(ROOT..'/progress680.csv','w'))
progressLog:write('clock,retired,sent,packet\\n');progressLog:flush()
emu.addMemoryCallback(function(a,v)
 assert(v==0xa5,'progress payload')
 local t=emu.getState().masterClock
 progressEvents[#progressEvents+1]={t,retired}
 progressLog:write(string.format('%d,%d,%d,%d\\n',t,retired,sent,packet and 1 or 0));progressLog:flush()
end,emu.callbackType.write,0x601d)
emu.addMemoryCallback(function()rpc()end,emu.callbackType.exec,0x7e0000,0x7effff)''')
        p.write_text(s,encoding='utf8',newline='\n')
    return build


def rpc_method():
    s=textwrap.dedent(inspect.getsource(joint.Link.rpc))
    s=once(s,'    self.future.sort()',
        '''    for item in (lines[5] if len(lines)>5 else '').split(';'):
        if not item:continue
        clock,index=map(int,item.split(':'))
        self.future.append((clock+math.ceil(8*joint.MASTER/joint.ARM_HZ),2,index,None))
    self.future.sort()''')
    s=once(s,'        if kind:',
        '''        if kind==2:
            accepted=self.retired==self.sent and self.retired==index and bool(index)
            if accepted:self.progress680=True
            self.progress_events680.append(dict(clock=clock,retired=index,sent=self.sent,accepted=accepted))
        elif kind:''')
    s=once(s,'self.retired=index;self.last=ack','self.retired=index;self.last=ack;self.progress680=False')
    ns=dict(vars(joint),joint=joint);exec(compile(s,'progress680-rpc','exec'),ns)
    return ns['rpc']


def pipe_init():
    # PipeLink replaces the file reply writer AFTER lua_rpc has run. Preserve
    # the extra event channel in that replacement as well as in file mode.
    s='\n'.join(line[4:] if line.startswith('    ') else line
        for line in inspect.getsource(transport.PipeLink.__init__).splitlines())
    s=once(s,"  ans[6]=table.concat(c);ans[7]=table.concat(e);consumed={};retiredEvents={}",
        """  ans[6]=table.concat(c);ans[7]=table.concat(e);consumed={};retiredEvents={}
  local p={};for _,v in ipairs(progressEvents)do p[#p+1]=string.format('%d:%d;',v[1],v[2])end
  ans[8]=table.concat(p);progressEvents={} """)
    # An extracted method has no __class__ cell for zero-argument super().
    s=once(s,'super().__init__(a)','super(PipeLink,self).__init__(a)')
    s=once(s,'path.write_text(s,encoding="utf8")','path.write_text(interior_lua(s,a),encoding="utf8")')
    ns=dict(vars(transport),interior_lua=interior_lua);exec(compile(s,'progress680-pipe','exec'),ns)
    return ns['__init__']


def interior_lua(s,a):
    labels=json.loads((a.client/'labels.json').read_text())
    if 'late_map680' in labels:
        s=once(s,'  if word(0x4000+tail)==src then i=tail end',
            '''  local match=nil
  for j=i,tail,8 do
   if word(0x4000+j)==src and word(0x4002+j)==dst then assert(not match);match=j end
  end
  assert(match,'unowned interior map');i=match''')
    return s


def checked_exchange():
    s=textwrap.dedent(inspect.getsource(checked.CheckedLink.exchange))
    s=once(s,'super().exchange(seq,target,operation,args)',
        'super(CheckedLink,self).exchange(seq,target,operation,args)')
    s=once(s,'len(reply)!=5','len(reply)!=6')
    ns=dict(vars(checked));exec(compile(s,'progress680-reply','exec'),ns)
    return ns['exchange']


def init(original):
    def wrapped(self,a):
        self.progress680=False;self.progress_events680=[]
        original(self,a)
    return wrapped


def accept(original):
    def wrapped(self,tx,t):
        if tx[0]==0xe1:self.progress680=False
        return original(self,tx,t)
    return wrapped


def response(original):
    def wrapped(self,tx):
        result=bytearray(original(self,tx))
        if tx[0]==0xe0 and self.progress680 and self.sent==self.retired and self.retired:
            result[2]|=8;result[19]=joint.crc(result[1:19],8,7,0)
        return bytes(result)
    return wrapped


if __name__=='__main__':
    instances=[]
    original_init=init(joint.Link.__init__)
    def track(self,a):instances.append(self);original_init(self,a)
    try:
        with patch.object(transport.PipeLink,'__init__',pipe_init()), \
             patch.object(checked.CheckedLink,'exchange',checked_exchange()), \
             patch.object(joint,'lua_rpc',lua(joint.lua_rpc)),patch.object(joint.Link,'__init__',track), \
             patch.object(joint.Link,'rpc',rpc_method()),patch.object(joint.Link,'accept',accept(joint.Link.accept)), \
             patch.object(joint.Link,'response',response(joint.Link.response)):
            runpy.run_module('test_nes_idle676',run_name='__main__')
    finally:
        for link in instances:
            (link.a.out/'progress680-events.json').write_text(json.dumps(link.progress_events680,indent=2)+'\n')
