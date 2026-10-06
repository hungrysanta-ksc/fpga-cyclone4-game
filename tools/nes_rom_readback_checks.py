# SPDX-License-Identifier: MIT
"""058 CHECK-port feasibility, public pin-model tests and private joint fit."""
from pathlib import Path
import argparse,json,os,re,shutil
from nes_rom_readback import ROOT,PORTS,CONNECT,materialize
from nes_rom_geometry import replace
from nes_spi_boot import put,sha,run


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--mode',choices=['unit','diff','mutation','fit'],required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--baseline',type=Path)
    p.add_argument('--questa-bin',type=Path)
    p.add_argument('--quartus-bin',type=Path)
    a=p.parse_args();out=a.out.resolve();assert str(out).isascii()
    out.mkdir(parents=True,exist_ok=False)
    for name in ['nes_rom_readback.py','nes_rom_readback_checks.py']:
        shutil.copy2(ROOT/'tools'/name,out/name)
    result=dict(candidate='NES-READBACK-PORT-058',mode=a.mode,passed=False,
                hardware_image=False,spi_mcu_connected=False,integrity_gate=False)
    if a.mode=='fit':
        previous=json.loads((a.baseline/'result.json').read_text())
        assert previous['candidate']=='NES-ROM-GEOMETRY-057' and previous['passed']
        for name,digest in previous['sources'].items():
            assert sha(a.baseline/name)==digest,name
            (out/name).parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(a.baseline/name,out/name)
        names=list(previous['sources'])
        materialize(out)
        s=(out/'nes_live_joint.sv').read_text()
        s=replace(s,'module nes_live_joint(','module nes_live_joint(\n'+PORTS)
        s=replace(s,'nes_spi_boot physical(','nes_spi_boot physical('+CONNECT)
        put(out/'nes_live_joint.sv',s)
        qsf=(out/'live.qsf').read_text()
        for name in ['check_enable','check_request','check_address[*]','check_ready','check_response',
                     'check_response_address[*]','check_data[*]','check_fault']:
            qsf+='\nset_instance_assignment -name VIRTUAL_PIN ON -to '+name
        put(out/'live.qsf',qsf+'\n')
        result['baseline_result_sha256']=sha(a.baseline/'result.json')
    else:
        assert re.fullmatch(r'18000@(?:localhost|127\.0\.0\.1)',os.environ.get('SALT_LICENSE_SERVER',''))
        materialize(out)
        for name in ['rom_boot_model.sv','rom_readback_tb.sv','rom_readback_diff.sv']:
            shutil.copy2(ROOT/'tests/nes-functional'/name,out/name)
        names=['nes_rom_loader.sv','nes_rom_boot.sv','nes_rom_physical.sv','rom_boot_model.sv','rom_readback_tb.sv']
        if a.mode=='diff':
            s=(ROOT/'src/nes/nes_rom_physical.sv').read_text()
            put(out/'nes_rom_physical_reference.sv',replace(s,'module nes_rom_physical #','module nes_rom_physical_reference #'))
            names=['nes_rom_physical.sv','nes_rom_physical_reference.sv','rom_readback_diff.sv']
    result['sources']={n:sha(out/n) for n in names}
    result['driver_sha256']=sha(Path(__file__))
    result['generator_sha256']=sha(ROOT/'tools/nes_rom_readback.py')
    def save():put(out/'result.json',json.dumps(result,indent=2)+'\n')
    save()
    if a.mode=='fit':
        for phase in ['map','fit']:run([a.quartus_bin/('quartus_'+phase+'.exe'),'live'],out,phase,3600)
        result['fit_summary']=(out/'output_files/live.fit.summary').read_text(errors='replace')
        print(result['fit_summary'],flush=True)
    elif a.mode=='mutation':
        # Keep each bad generated design and its exact causal failure log.
        for mutation in ['chip','lane','chr']:
            folder=out/mutation;folder.mkdir()
            for n in names:shutil.copy2(out/n,folder/n)
            if mutation=='chr':
                path=folder/'nes_rom_boot.sv';s=path.read_text()
                s=replace(s,"{1'b1,5'b0,check_address[15:0]}","{1'b0,5'b0,check_address[15:0]}")
                reason='returned accepted address tag'
            else:
                path=folder/'nes_rom_physical.sv';s=path.read_text()
                bit=1 if mutation=='chip' else 0
                s=replace(s,f'{mutation}<=selected_address[{bit}];',f'{mutation}<=~selected_address[{bit}];')
                reason='returned accepted address tag'
            put(path,s)
            for tool,args in [('vlib',['work']),('vlog',['-sv',*names])]:
                log=run([a.questa_bin/(tool+'.exe'),*args],folder,tool,1200)
                assert not re.search(r'\*\* (?:Fatal|Error)(?:\s|:)',log)
            log=run([a.questa_bin/'vsim.exe','-c','rom_readback_tb','-do','onerror {quit -code 1}; run -all; quit -f'],folder,'vsim',1200)
            fatal=re.findall(r'\*\* Fatal: ([^\r\n]+)',log)
            assert len(fatal)==1 and reason in fatal[0] and 'PASS READBACK PORT' not in log,fatal
            result.setdefault('negative_controls',[]).append(dict(mutation=mutation,expected_failure=fatal[0],incorrect_design_passed=False,sources={n:sha(folder/n) for n in names}))
            save();print('PASS expected failure '+mutation+': '+fatal[0],flush=True)
    else:
        top='rom_readback_diff' if a.mode=='diff' else 'rom_readback_tb'
        for tool,args in [('vlib',['work']),('vlog',['-sv',*names]),
                          ('vsim',['-c',top,'-do','onerror {quit -code 1}; run -all; quit -f'])]:
            log=run([a.questa_bin/(tool+'.exe'),*args],out,tool,1200)
            assert not re.search(r'\*\* (?:Fatal|Error)(?:\s|:)',log),str(out/(tool+'.log'))
        marker=re.search(r'PASS READBACK (?:PORT|RUN DIFF) [^\r\n]+',log);assert marker
        result['marker']=marker[0];print(marker[0],flush=True)
    result['passed']=True;save()


if __name__=='__main__':main()
