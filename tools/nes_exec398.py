# SPDX-License-Identifier: MIT
"""398 byte-program assembler and literal instruction semantics."""
class Program:
 def __init__(self):self.code=[];self.labels={};self.fix=[];self.serial=0
 def label(self,n):assert n not in self.labels,n;self.labels[n]=len(self.code)
 def fresh(self,p='L'):self.serial+=1;return p+str(self.serial)
 def emit(self,op,x=0):self.code.append(op<<14|x)
 def jump(self,label,condition=0):self.fix.append((len(self.code),label));self.emit(12,condition<<12)
 def call(self,label):self.fix.append((len(self.code),label));self.emit(13)
 def ret(self):self.emit(14)
 def rte(self):self.emit(15)
 def const(self,x):assert 0<=x<=255;self.emit(0,x)
 def load(self,x):self.emit(1,x)
 def store(self,x):self.emit(2,x)
 def add(self,x,carry=False):self.emit(3,x|int(carry)<<8)
 def sub(self,x,borrow=False):self.emit(4,x|int(borrow)<<8)
 def xor(self,x):self.emit(5,x)
 def AND(self,x):self.emit(6,x)
 def OR(self,x):self.emit(7,x)
 def shift(self,right=False,carry=False):self.emit(8,int(right)|int(carry)<<1)
 def compare(self,x):self.emit(9,x)
 def andc(self,x):self.emit(15,1<<8|x)
 def orc(self,x):self.emit(15,2<<8|x)
 def xorc(self,x):self.emit(15,3<<8|x)
 def addc(self,x):self.emit(15,4<<8|x)
 def subc(self,x):self.emit(15,5<<8|x)
 def index(self):self.emit(15,6<<8)
 def index_value(self):self.emit(15,7<<8)
 def loadind(self):self.emit(1,1<<9)
 def storeind(self):self.emit(2,1<<9)
 def read(self,x):self.emit(10,x)
 def write(self,x):self.emit(11,x)
 def readind(self):self.emit(10,1<<9)
 def writeind(self):self.emit(11,1<<9)
 def set(self,d,v):self.const(v);self.store(d)
 def copy(self,d,s):self.load(s);self.store(d)
 def readto(self,d,port):self.read(port);self.store(d)
 def out(self,port,s):self.load(s);self.write(port)
 def outc(self,port,c):self.const(c);self.write(port)
 def inc(self,d,one):self.load(d);self.add(one);self.store(d)
 def dec(self,d,one):self.load(d);self.sub(one);self.store(d)
 def add16(self,d,a,b):
  self.load(a);self.add(b);self.store(d);self.load(a+1);self.add(b+1,True);self.store(d+1)
 def equal(self,a,b,fail):self.load(a);self.sub(b);self.jump(fail,2)
 def eqc(self,a,b,fail):self.load(a);self.compare(b);self.jump(fail,2)
 def eq16(self,a,b,fail):self.equal(a,b,fail);self.equal(a+1,b+1,fail)
 def upper8(self,a,b,fail):
  ok=self.fresh();self.load(a);self.compare(b);self.jump(ok,1);self.jump(fail,3);self.label(ok)
 def upper16(self,a,b,fail):
  equal=self.fresh();ok=self.fresh();self.load(a+1);self.compare(b>>8);self.jump(equal,1);self.jump(fail,3);self.jump(ok);self.label(equal);self.upper8(a,b&255,fail);self.label(ok)
 def lower16(self,a,b,fail):
  ok=self.fresh();equal=self.fresh();self.load(a+1);self.compare(b>>8);self.jump(equal,1);self.jump(ok,3);self.jump(fail);self.label(equal);self.load(a);self.compare(b&255);self.jump(ok,3);self.jump(fail);self.label(ok)
 def nonzero16(self,a,fail):self.load(a);self.OR(a+1);self.jump(fail,1)
 def finish(self):
  for at,label in self.fix:
   assert label in self.labels,label;assert self.labels[label]<4096;self.code[at]|=self.labels[label]
  assert len(self.code)<=4088,len(self.code)
  return list(self.code)
