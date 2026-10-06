# SPDX-License-Identifier: MIT
"""Explicit-root H1 installer. No drive discovery, formatting, or recursive deletion."""
from pathlib import Path
import argparse,hashlib,json,os,tempfile
CANDIDATE='NES-H1-SAMPLING-044'
FIRMWARE='sd2snes/firmware.stm'
FPGA='sd2snes/fpga_nh1.bi3'
MARKER='NES H1 037.nh1'
ORDER=(FPGA,FIRMWARE)
EXPECTED={FIRMWARE:'1c3b40a3459d24114cb4d91ee9d861d1a08025a670ef25317ef489092203693b',FPGA:'71ffacd82227ae68b186dd3d3fab9619a69c4cdef73b5c44c55621caff4e0888'}
BASELINE_FW='ad88de3ad14bb192de7cd6e74150bca3ca09507d803d315edcb4359b30b7143a'
C44_GBC='0bdcb9f995496ea314a41a0b624f1b9c98bc702f2929ab578b5e300c1d4bf647'
PRESERVE=('sd2snes/fpga_base.bi3','sd2snes/fpga_egbc.bi3','sd2snes/m3nu.bin')
def require(ok,message):
 if not ok:raise RuntimeError(message)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def safe(p):
 p=Path(os.path.abspath(p))
 for node in (p,*p.parents):
  if node.exists() or node.is_symlink():
   require(not node.is_symlink() and not (getattr(node.lstat(),'st_file_attributes',0)&0x400),'Reparse/symlink path rejected: '+str(node))
 return p
def file_at(root,name):
 require(name in (*ORDER,*PRESERVE),'Unexpected target')
 p=safe(root/name);require(p.is_relative_to(root),'Path escaped root');return p
def digest(p):
 if not p.exists():return None
 require(p.is_file(),'Not a regular file: '+str(p));return sha(p)
def atomic(p,data):
 # Each target has an existing parent. Flush the file before replacing it.
 fd,tmp=tempfile.mkstemp(prefix='.nh1-',suffix='.tmp',dir=p.parent)
 try:
  with os.fdopen(fd,'wb') as f:f.write(data);f.flush();os.fsync(f.fileno())
  os.replace(tmp,p)
 finally:
  if os.path.exists(tmp):os.unlink(tmp)
 require(p.read_bytes()==data,'Readback mismatch: '+str(p))
def payload(package):
 package=safe(package);m=json.loads((package/'manifest.json').read_text(encoding='utf-8'))
 require(m['candidate']==CANDIDATE,'Wrong package')
 for e in m['files']:
  rel=Path(e['path']);require(not rel.is_absolute() and '..' not in rel.parts,'Unsafe package entry')
  f=safe(package/rel);require(f.is_file() and f.stat().st_size==e['bytes'] and sha(f)==e['sha256'],'Package mismatch: '+str(rel))
 data={n:(package/'sd-overlay'/n).read_bytes() for n in ORDER}
 for n in ORDER:require(hashlib.sha256(data[n]).hexdigest()==EXPECTED[n],'Wrong candidate pair: '+n)
 return data
def preflight(sd,package):
 sd=safe(sd);require(sd.is_dir(),'SD root missing');data=payload(package)
 require(digest(file_at(sd,FIRMWARE))==BASELINE_FW,'Expected041 installed firmware.stm; do not install over an unknown firmware')
 preserve={n:digest(file_at(sd,n)) for n in PRESERVE}
 require(preserve['sd2snes/fpga_egbc.bi3']==C44_GBC,'Expected released C44 GBC image')
 require(digest(file_at(sd,FPGA))=='b6c7d930a8fb618f1a1ae27724faf1b177c3407526601c8b465cb82472e1453f','Expected041 H1 FPGA')
 for n in PRESERVE:require(preserve[n] is not None and file_at(sd,n).stat().st_size>0,'Missing recovery dependency: '+n)
 for n in ORDER:digest(file_at(sd,n))
 return data,preserve
def install(sd,package,backup):
 sd=safe(sd);backup=safe(backup)
 require(not backup.exists(),'Backup directory must be fresh')
 require(not backup.is_relative_to(sd) and not sd.is_relative_to(backup),'Backup must be outside the SD root')
 data,preserve=preflight(sd,package)
 old={n:digest(file_at(sd,n)) for n in ORDER}
 backup.mkdir(parents=True)
 for n,h in old.items():
  if h is not None:
   p=backup/'original'/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(file_at(sd,n).read_bytes());require(sha(p)==h,'Backup verification failed')
 journal={'candidate':CANDIDATE,'sd_root':str(sd),'original':old,'installed':EXPECTED,'preserved':preserve,'complete':False}
 atomic(backup/'restore.json',(json.dumps(journal,indent=2)+'\n').encode())
 for n in ORDER:
  require(digest(file_at(sd,n))==old[n],'Target changed since backup: '+n)
  atomic(file_at(sd,n),data[n])
 require({n:digest(file_at(sd,n)) for n in PRESERVE}==preserve,'Preserved dependency changed')
 journal['complete']=True;atomic(backup/'restore.json',(json.dumps(journal,indent=2)+'\n').encode())
 return journal
def restore(sd,backup):
 sd=safe(sd);backup=safe(backup)
 require(not backup.is_relative_to(sd) and not sd.is_relative_to(backup),'Backup must be outside SD')
 j=json.loads((backup/'restore.json').read_text())
 require(j['candidate']==CANDIDATE and Path(j['sd_root'])==sd,'Backup belongs to another SD path/candidate')
 require(j['installed']==EXPECTED and set(j['original'])==set(ORDER) and set(j['preserved'])==set(PRESERVE),'Unexpected backup schema')
 # Validate every backup and destination BEFORE any restoration.
 for n in ORDER:
  h=j['original'][n]
  if h is not None:require(digest(safe(backup/'original'/n))==h,'Corrupt backup: '+n)
  require(digest(file_at(sd,n)) in (h,EXPECTED[n]),'Target changed after install: '+n)
 require({n:digest(file_at(sd,n)) for n in PRESERVE}==j['preserved'],'Base/GBC/menu changed since install')
 for n in reversed(ORDER):
  dest=file_at(sd,n);h=j['original'][n]
  if h is None:
   if dest.exists():dest.unlink() # Only this fixed, hash-verified added file.
  else:atomic(dest,(backup/'original'/n).read_bytes())
 require({n:digest(file_at(sd,n)) for n in ORDER}==j['original'],'Restore readback mismatch')
 return {'restored':True,'backup_retained':True}
def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('action',choices=('check','install','restore'));p.add_argument('--sd-root',type=Path,required=True)
 p.add_argument('--package',type=Path,default=Path(__file__).resolve().parent);p.add_argument('--backup',type=Path)
 a=p.parse_args()
 if a.action=='check':
  _,preserved=preflight(a.sd_root,a.package);result={'preflight':True,'preserved':preserved,'writes':False}
 else:
  require(a.backup is not None,'--backup required')
  result=install(a.sd_root,a.package,a.backup) if a.action=='install' else restore(a.sd_root,a.backup)
 print(json.dumps(result,indent=2))
if __name__=='__main__':main()
