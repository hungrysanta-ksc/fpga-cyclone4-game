"""Summarize pin-level simulations and full-board costs alongside the reset CPU traces."""
import argparse
import json
from pathlib import Path
import re

from analyze_nes_output822 import resources
from package_nes_trial872 import ROOT, read, sha


def report(temp, cpu, tests):
    cpu=read(cpu/'result.json')
    for run in cpu.values():
        assert [e['clock'] for e in run['events'][:3]]==[186,608,640]
    boards={}
    for variant,path in zip(('891','891B','891C','891D','891E'),tests,strict=True):
        board=temp/f'nes-trial816-board{variant}'
        runs=read(path/'result.json')
        assert sha(path/'nes_screen_status151.sv')==sha(board/'nes_screen_status151.sv')
        assert runs['872']['cases']==runs['890']['cases']
        legacy=runs['890']['cases']
        rows=runs['891']['cases']
        assert len(rows)==28
        examples=[]
        for i,(old,new) in enumerate(zip(legacy,rows,strict=True)):
            assert (int(new['phase']),int(new['case']))==divmod(i,7)
            assert all(old[k]==new[k] for k in old if k!='order')
            if i<7:
                examples.append(dict(new,prior_order=old['order']))
            else:
                assert all(new[k]==rows[i%7][k] for k in new if k!='phase')
        f=board/'output_files/board.fit.summary'
        fit=dict(summary_SHA256=sha(f),fit_pass='Fitter Status : Successful' in f.read_text())
        if fit['fit_pass']:
            fit.update(resources(temp,variant))
        else:
            fit['errors']=re.findall(r'^Error \(\d+\): (.+)$',(board/'fit.log').read_text(errors='replace'),re.M)
            assert fit['errors']
        boards[variant]=dict(board=fit,status_SHA256=sha(path/'nes_screen_status151.sv'),
                             simulation_SHA256=sha(path/'result.json'),cases_per_design=28,
                             phases_ns=[1,4,7,10],cases=examples)
    return dict(reference='MMC890',physical_891=False,cpu_mesen=cpu,variants=boards)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('temp',type=Path)
    p.add_argument('cpu',type=Path)
    p.add_argument('tests',type=Path,nargs=5)
    a=p.parse_args()
    (ROOT/'analysis/boot891-results.json').write_text(json.dumps(report(a.temp,a.cpu,a.tests),indent=2)+'\n')
