# SPDX-License-Identifier: MIT
"""Real filesystem recovery tests with explicitly synthetic pre-existing C44 bytes."""
from pathlib import Path
import argparse,json,shutil
import manage_nes_h1_sd as m

def main():
 p=argparse.ArgumentParser()
 for n in ('out','package'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();out=a.out.resolve();out.mkdir();results=[]
 # Only the pre-existing fixture firmware/GBC hashes are substituted.
 # Candidate payload pins, backup/restore code and all filesystem actions are real.
 fw=b'fixture original firmware';gbc=b'fixture GBC';m.C44_FW=m.hashlib.sha256(fw).hexdigest();m.C44_GBC=m.hashlib.sha256(gbc).hexdigest()
 def setup(name,existing=False):
  sd=out/name/'sd';(sd/'sd2snes').mkdir(parents=True)
  for n,b in [(m.FIRMWARE,fw),('sd2snes/fpga_base.bi3',b'base'),('sd2snes/fpga_egbc.bi3',gbc),('sd2snes/menu.bin',b'menu'),('save.srm',b'precious save')]: (sd/n).write_bytes(b)
  if existing:
   (sd/m.FPGA).write_bytes(b'older H1');(sd/m.MARKER).write_bytes(b'older marker')
  return sd,sd.parent/'backup'
 def tree(p):return {f.relative_to(p).as_posix():m.sha(f) for f in p.rglob('*') if f.is_file()}
 def reject(fn):
  try:fn()
  except RuntimeError:return
  raise AssertionError('Operation should have been rejected')
 sd,b=setup('check');old=tree(sd);m.preflight(sd,a.package);assert tree(sd)==old;results.append('read_only_preflight')
 for existing in (False,True):
  sd,b=setup('existing' if existing else 'absent',existing);old=tree(sd);j=m.install(sd,a.package,b)
  assert j['complete'] and {n:m.sha(sd/n) for n in m.ORDER}==m.EXPECTED
  assert (sd/'save.srm').read_bytes()==b'precious save'
  m.restore(sd,b);assert tree(sd)==old;m.restore(sd,b);assert tree(sd)==old
  results.append('restore_preexisting' if existing else 'restore_added_and_idempotent')
 sd,b=setup('interrupted');old=tree(sd);atomic=m.atomic
 def fail_marker(p,data):
  if p==sd/m.MARKER:raise OSError('injected interruption after FPGA write')
  return atomic(p,data)
 m.atomic=fail_marker
 try:
  try:m.install(sd,a.package,b)
  except OSError:pass
  else:raise AssertionError('injection not reached')
 finally:m.atomic=atomic
 assert m.sha(sd/m.FPGA)==m.EXPECTED[m.FPGA] and m.sha(sd/m.FIRMWARE)==m.C44_FW
 m.restore(sd,b);assert tree(sd)==old;results.append('interrupted_install_restore')
 sd,b=setup('wrong_fw');(sd/m.FIRMWARE).write_bytes(b'unknown');old=tree(sd)
 reject(lambda:m.install(sd,a.package,b));assert tree(sd)==old and not b.exists();results.append('unknown_firmware_rejected_before_write')
 sd,b=setup('backup_inside');old=tree(sd);reject(lambda:m.install(sd,a.package,sd/'backup'));assert tree(sd)==old;results.append('backup_on_SD_rejected')
 sd,b=setup('backup_exists');b.mkdir();old=tree(sd);reject(lambda:m.install(sd,a.package,b));assert tree(sd)==old;results.append('existing_backup_rejected')
 sd,b=setup('changed_target');m.install(sd,a.package,b);(sd/m.FIRMWARE).write_bytes(b'new external modification');old=tree(sd)
 reject(lambda:m.restore(sd,b));assert tree(sd)==old;results.append('changed_target_preserved')
 sd,b=setup('corrupt_backup');m.install(sd,a.package,b);(b/'original'/m.FIRMWARE).write_bytes(b'broken backup');old=tree(sd)
 reject(lambda:m.restore(sd,b));assert tree(sd)==old;results.append('corrupt_backup_rejected_before_write')
 sd,b=setup('other_root');m.install(sd,a.package,b);other,_=setup('other_SD');old=tree(other)
 reject(lambda:m.restore(other,b));assert tree(other)==old;results.append('different_SD_root_rejected')
 sd,b=setup('changed_dependency');m.install(sd,a.package,b);(sd/'sd2snes/fpga_base.bi3').write_bytes(b'changed base');old=tree(sd)
 reject(lambda:m.restore(sd,b));assert tree(sd)==old;results.append('changed_base_rejected')
 sd,b=setup('bad_package');bad=out/'tampered-package';shutil.copytree(a.package,bad)
 (bad/'sd-overlay'/m.FPGA).write_bytes(b'tampered');old=tree(sd)
 reject(lambda:m.install(sd,bad,b));assert tree(sd)==old and not b.exists();results.append('tampered_payload_rejected_before_write')
 result={'passed':len(results),'cases':results,'scope':'Synthetic existing firmware/GBC fixture hash constants only; actual pinned candidate payload; filesystem operations real; no physical SD or power-cut test.'}
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
