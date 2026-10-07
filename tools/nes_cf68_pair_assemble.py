# SPDX-License-Identifier: MIT
"""ASM/CPF only from pinned068 fit03, into a new independent ASCII folder."""
from pathlib import Path
import argparse,hashlib,json,shutil,subprocess
ROOT=Path(__file__).resolve().parents[1]
def digest(data):return hashlib.sha256(data).hexdigest()
def inventory(root):
    return {p.relative_to(root).as_posix():digest(p.read_bytes())
            for d in ['db','incremental_db'] for p in (root/d).rglob('*') if p.is_file()}
def assemble(fit,out,quartus):
    m=json.loads((ROOT/'analysis/cf68-pair-inputs.json').read_text())
    def validate(root):
        assert inventory(root)==m['database'],'068 database lineage mismatch'
        for n,h in {**m['fit_inputs'],**m['fit_reports']}.items():
            assert digest((root/n).read_bytes())==h,n
    # Historical068 IO inventory pins db/ only; unused incremental_db is omitted.
    for n,h in {**m['database'],**m['fit_inputs'],**m['fit_reports']}.items():
        assert digest((fit/n).read_bytes())==h,n
    assert {n:h for n,h in inventory(fit).items() if n.startswith('db/')}==m['database']
    if out.exists() or not str(out.resolve()).isascii() or out.resolve().is_relative_to(fit.resolve()):
        raise ValueError('New independent ASCII output required')
    out.mkdir(parents=True)
    for n in {**m['database'],**m['fit_inputs'],**m['fit_reports']}:
        dest=out/n;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(fit/n,dest)
    validate(out)
    (out/'input-lineage.json').write_text(json.dumps(m,indent=2)+'\n')
    for phase,args in [('asm',['quartus_asm.exe','board']),('cpf',['quartus_cpf.exe','-c','output_files/board.sof','output_files/board.rbf'])]:
        with (out/(phase+'-071.log')).open('wb') as stream:
            result=subprocess.run([quartus/args[0],*args[1:]],cwd=out,stdout=stream,stderr=subprocess.STDOUT,timeout=300)
        log=(out/(phase+'-071.log')).read_text(errors='replace')
        if result.returncode or 'successful. 0 errors, 0 warnings' not in log or 'SC Standard Edition' not in log or '25.1std.0 Build 1129' not in log:
            raise ValueError('Inspect raw '+str(out/(phase+'-071.log')))
    # ASM is allowed to create/change its own DB files; original input remains immutable.
    for n,h in {**m['database'],**m['fit_inputs'],**m['fit_reports']}.items():
        assert digest((fit/n).read_bytes())==h,n
    for n,h in m['fit_inputs'].items():assert digest((out/n).read_bytes())==h,n
    for n,h in m['fit_reports'].items():
        if '.fit.' in n or '.sta.' in n or '.map.' in n:assert digest((out/n).read_bytes())==h,n
    raw=(out/'output_files/board.rbf').read_bytes()
    value=dict(candidate='NES-CF68-PAIR-071',rbf_sha256=digest(raw),rbf_bytes=len(raw),input_lineage=m,new_map_fit_sta=False,hardware_execution=False,installable=False)
    (out/'assembly-071.json').write_text(json.dumps(value,indent=2)+'\n')
    print('PASS071 Standard ASM/CPF '+json.dumps(dict(rbf_bytes=len(raw),rbf_sha256=digest(raw))))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--fit',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--quartus-bin',type=Path,required=True)
    a=p.parse_args();assemble(a.fit,a.out,a.quartus_bin)
