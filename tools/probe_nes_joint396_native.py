# SPDX-License-Identifier: MIT
"""Actual65816 service for bounded internal repeat fragments;ABI unchanged."""
import inspect
import probe_nes_jobs394_native as old
s=inspect.getsource(old.fixtures)
s=s.replace("sizes=j['fragments']if r[9]>=2 else[len(data)]", "sizes=j['fragments']if r[9]>=2 else[len(data)]\n  if r[9]>=2 and (r[6]>>2)&3>1 and not r[6]&64:sizes=[min(512,len(data)-i)for i in range(0,len(data),512)]")
ns=dict(old.__dict__);exec(compile(s,'repeat396-fixtures','exec'),ns);fixtures=ns['fixtures'];old.fixtures=fixtures
if __name__=='__main__':old.main()
