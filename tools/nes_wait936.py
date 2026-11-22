"""Narrow advisory OAM waits without changing the accepted 935 DMA consumer."""
import argparse
import shutil
from pathlib import Path
from nes_chain935 import fit_arm, replay
from nes_raw506 import once, sha


def work(mode):
    return fit_arm().parent.parent/'nes-wait936'/mode


MODES = ('receipt', 'finishobj', 'twobatch', 'batchcredit', 'batchfast', 'batchhold', 'batchroom',
         'retireinput', 'tailinput')


def prepare(mode):
    if mode not in MODES:
        raise ValueError(mode)
    base = fit_arm()/'link'
    assert sha(base/'src/obj-nes-100/firmware.stm') == '973ca233089137432d65cc62af554caf20f71ee35b8fdf32c3274fb73bd7bf5c'
    link = work(mode)/'link'
    shutil.copytree(base, link)
    sink = link/'src/nes_native_sink165.c'
    code = sink.read_text()
    original = '!wait_map880(s->plan->window,12)'
    if mode == 'receipt':
        policy = '!wait_map880(s->plan->window,1)'
    elif mode == 'batchcredit':
        policy = '!wait_map880(s->plan->window,s->plan->sent>2 ? 1 : 12)'
    elif mode in ('finishobj','batchhold','batchroom'):
        # Before the repeated OAM fill, finish checked tile receipts for a
        # short OBJ predecessor. Keep the separate large-to-tail DMA window.
        condition = {'finishobj':'', 'batchhold':'s->plan->sent>2 && ',
                     'batchroom':'s->plan->bulk_pending && '}[mode]
        policy = ('!('+condition+'s->plan->bulk[2]==32 && !s->plan->bulk[3] && !s->plan->finished ? '
                  'nes_plan200_progress(s->plan,NES_FINAL553) : wait_map880(s->plan->window,12))')
    else:
        policy = original
    code = once(code,original,policy)
    if mode in ('retireinput','tailinput'):
        # After the checked retirement, leave the queue available to the
        # 65816 and use the bus budget of one short OBJ for input status.
        anchor='s->plan->window->last[1]==1 &&\n    !wait_map880(s->plan->window,12))return fail(s,5);'
        code=once(code,anchor,'''s->plan->window->last[1]==1){
  struct nes_sink_window184 *w=s->plan->window;
  if(!wait_map880(w,12))return fail(s,5);
  if(s->plan->sent>2 && w->wait)
   for(unsigned i=0;i<4;i++)if(!w->wait(w->ctx,w->guard,4,false))return fail(s,5);
 }''')
        if mode=='tailinput':
            code=once(code,'i<4;i++)if(!w->wait','i<2;i++)if(!w->wait')
    if mode not in ('receipt','finishobj'):
        code = once(code,'if(fixed && s->plan->bulk[2]==32',
                         'if(fixed && s->plan->sent<=2 && s->plan->bulk[2]==32')
    sink.write_text(code,newline='\n')
    runtime = link/'src/nes_native_runtime165.c'
    if mode in ('batchfast','batchhold','batchroom','retireinput','tailinput'):
        code = once(runtime.read_text(),'? 84u*96u : s->plan.tile_service',
                                        '? 0 : s->plan.tile_service')
        runtime.write_text(code,newline='\n')
    if mode == 'receipt':
        return
    menu = link/'src/nes_menu_diagnostic.c'
    report = menu.read_text()
    guard = ' if(n<=0||(size_t)n>=4096)return;'
    assert report.count(guard)==2
    # Packed appends propagate negative offsets and return offsets < capacity.
    # Check before the external formatter and before persisting the report.
    report = report.replace(guard,'',1).replace(guard,' if(n<=0)return;')
    report = once(report,' if(n<0)return;\n n=nes_packed828',' n=nes_packed828')
    if mode in ('finishobj','batchhold','batchroom','retireinput','tailinput'):
        report = once(report,'for(unsigned i=0,off=0;i<sizeof geometry_delta;i++){',
                             'const char *b=modes;\n for(unsigned i=0;i<sizeof geometry_delta;i++){')
        report = once(report,'const char *a=name,*b=modes+off;','const char *a=name;')
        report = once(report,'while(*b)b++;\n  off=(unsigned)(b-modes)+1;', 'while(*b++){}')
    menu.write_text(report,newline='\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=('prepare','replay','guards','proof'))
    p.add_argument('mode',choices=MODES);p.add_argument('temp',type=Path)
    p.add_argument('phase',type=int,choices=(1,2),nargs='?')
    p.add_argument('cache',choices=('warm','cold'),nargs='?')
    a=p.parse_args()
    if a.action=='prepare':
        prepare(a.mode)
    elif a.action=='replay':
        if a.phase is None or a.cache is None:
            p.error('replay requires PHASE and CACHE')
        replay(a.temp,'final',a.phase,a.cache,'bounded',work_arm=work(a.mode),tag='936'+a.mode)
    elif a.action=='guards':
        from unittest.mock import patch
        import nes_obj923
        import nes_return920
        from nes_chain935 import output
        from check_nes_chain935 import run
        rom=output('bounded')
        tag='936'+a.mode
        with patch.object(nes_obj923,'client',lambda _:rom), patch.object(nes_return920,'client',lambda _:rom):
            nes_return920.guards(a.temp,'first',tag=tag,destination=work(a.mode)/'final-guards.json')
            nes_obj923.obj_stops(a.temp,'first',tag=tag,destination=work(a.mode)/'final-stops.json')
        for phase in (1,2):
            for case in ('head','stop'):
                run(a.temp,'bounded',phase,case,tag=tag)
    else:
        from check_nes_supply905_arm import run
        run(Path.home()/'Downloads/test/Takahashi Meijin no Boukenjima 4 (J).nes',work(a.mode),925,short_header=True)
