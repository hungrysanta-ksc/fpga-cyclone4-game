"""Report observable waits on one 952-board timebase. Zero-grant tiles have no ROM timestamps."""
import json
from pathlib import Path
import sys
from read_nes_supply905 import MS, decode


def report(path):
    trace=decode(path,956)
    if trace['mode']!=0:
        raise ValueError('requires the normal MMC3 marker')
    slots=[]
    for index in trace['selected']:
        if not index:
            slots.append(None)
            continue
        row=trace['rows'][index-1]
        if 'detail' not in row:
            raise ValueError('incomplete target identity or input/ACK')
        banks={}
        chunks=[]
        for c in row['detail']:
            returned=banks.get(c['bank'])
            request=c['first_ROM_request_ms']
            requests=[dict(tile=i,first_request_ms=t['first_request_ms'],
                           first_grant_ms=t['first_grant_ms'],last_grant_ms=t['last_grant_ms'],grants=t['grants'])
                      for i,t in enumerate(c['tiles']) if t['grants']]
            chunks.append(dict(token=c['token'],bank=c['bank'],kind=c['kind'],B=c['bytes'],
                previous_same_bank_return_ms=returned,request_after_previous_return_ms=(
                    None if returned is None or request is None else round(request-returned,3)),
                ROM_grants=c['ROM_grants'],requested_tiles=requests,longest_first_grant_wait_ms=c['longest_first_grant_wait_ms'],
                bank_return_ms=c['returned_after_E9_ms'],last_grant_to_return_ms=(
                    None if not requests else round(c['returned_after_E9_ms']-requests[-1]['last_grant_ms'],3))))
            banks[c['bank']]=c['returned_after_E9_ms']
        slots.append(dict(tick=row['tick'],generation=row['generation'],BG=row['BG'],OBJ=row['OBJ'],
                          map=row['map'],tiles=row['tiles'],last_offset=row['last_offset'],
                          E9_to_last_ready_ms=row['E9_to_last_publish_ms'],
                          input_to_ARM_ACK_ms=row['input_to_final_ACK_ms'],
                          ARM_ACK_interval_ms=row['previous_to_current_ARM_ACK_ms'],chunks=chunks))
    return dict(edition=956,summary_rows=len(trace['rows']),dropped=trace['dropped'],time_bin_ms=MS,
                targets=slots)


if __name__=='__main__':
    print(json.dumps(report(Path(sys.argv[1])),indent=2))
