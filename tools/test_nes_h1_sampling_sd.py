# SPDX-License-Identifier: MIT
from pathlib import Path
import argparse,json,shutil
import manage_nes_h1_sampling_sd as m
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser()
 for n in ('out','package'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();out=a.out.resolve();out.mkdir();cases=[]
 # Real041/044 MCU and FPGA; only GBC fixture hash is substituted.
 m.C44_GBC=m.hashlib.sha256(b'fixture gbc').hexdigest()
 def setup(name):
  sd=out/name/'sd';(sd/'sd2snes').mkdir(parents=True)
  shutil.copy2(ROOT/'analysis/local-h1-edge-041/arm/firmware.stm',sd/m.FIRMWARE)
  shutil.copy2(ROOT/'analysis/local-h1-edge-041/resource/fpga_nh1.bi3',sd/m.FPGA)
  for n,b in [('sd2snes/fpga_egbc.bi3',b'fixture gbc'),('sd2snes/fpga_base.bi3',b'base'),('sd2snes/m3nu.bin',b'menu'),('save.srm',b'precious'),('NES H1 037.nh1',b'marker')]: (sd/n).write_bytes(b)
  return sd,sd.parent/'backup'
 def tree(sd):return {f.relative_to(sd).as_posix():m.sha(f) for f in sd.rglob('*') if f.is_file()}
 def reject(fn):
  try:fn()
  except RuntimeError:return
  raise AssertionError('Expected rejection')
 sd,b=setup('normal');old=tree(sd);m.preflight(sd,a.package);assert tree(sd)==old
 m.install(sd,a.package,b);assert all(m.sha(sd/n)==m.EXPECTED[n] for n in m.ORDER)
 assert {n:h for n,h in tree(sd).items() if n not in m.ORDER}=={n:h for n,h in old.items() if n not in m.ORDER}
 (sd/'sd2snes/nes-h1-last-044.txt').write_bytes(b'fault evidence')
 m.restore(sd,b);assert m.sha(sd/m.FPGA)==old[m.FPGA] and m.sha(sd/m.FIRMWARE)==m.BASELINE_FW and (sd/'sd2snes/nes-h1-last-044.txt').read_bytes()==b'fault evidence'
 m.restore(sd,b);cases.append('install_restore_idempotent_preserves_evidence_and_save')
 sd,b=setup('interrupted');old=tree(sd);original=m.atomic
 def cut(p,data):
  original(p,data)
  if p==sd/m.FPGA:raise OSError('interruption after replacement')
 m.atomic=cut
 try:
  try:m.install(sd,a.package,b)
  except OSError:pass
  else:raise AssertionError('injection missed')
 finally:m.atomic=original
 m.restore(sd,b);assert tree(sd)==old;cases.append('interrupted_between_FPGA_and_MCU_recovers')
 for label,target in [('unknown_firmware',m.FIRMWARE),('wrong_fpga',m.FPGA),('missing_menu','sd2snes/m3nu.bin')]:
  sd,b=setup(label)
  if label=='missing_menu':(sd/target).unlink()
  else:(sd/target).write_bytes(b'unknown')
  old=tree(sd);reject(lambda:m.install(sd,a.package,b));assert tree(sd)==old and not b.exists();cases.append(label+'_rejected')
 sd,b=setup('backup_inside');old=tree(sd);reject(lambda:m.install(sd,a.package,sd/'backup'));assert tree(sd)==old;cases.append('backup_inside_rejected')
 sd,b=setup('modified');m.install(sd,a.package,b);(sd/m.FIRMWARE).write_bytes(b'changed');old=tree(sd);reject(lambda:m.restore(sd,b));assert tree(sd)==old;cases.append('modified_target_preserved')
 sd,b=setup('bad_backup');m.install(sd,a.package,b);(b/'original'/m.FIRMWARE).write_bytes(b'bad');old=tree(sd);reject(lambda:m.restore(sd,b));assert tree(sd)==old;cases.append('bad_backup_rejected')
 (out/'result.json').write_text(json.dumps({'passed':len(cases),'cases':cases,'scope':'Real041/044 MCU and FPGA bytes; synthetic SD folder/base/menu/GBC fixture; no physical SD'},indent=2))
 print('PASS edge SD pair update/recovery8 cases')
if __name__=='__main__':main()
