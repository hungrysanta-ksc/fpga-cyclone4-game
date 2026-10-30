# SPDX-License-Identifier: MIT
"""Regression: RUN success must not hide V3 capture rejects or invent loss rate."""
from audit_nes499 import capture_evidence


def sample(rows):
    return ('ppu_history_kind=LAST16_EPISODE180_V3\nppu_history_valid=1\n'
            f'ppu_history_count={len(rows)}\nppu_history_flags=1\n'+
            ''.join(f'ppu_history_{i:02d}={v}\n' for i,v in enumerate(rows)))


def main():
    # Actual metadata signatures: no ROM, pixels or game state included.
    text=sample(['55c000003ffff8c703a10001','960000001ffff8c703a10001',
                 '564000009ffff8c703a10001','58000000dffff8c703a10001'])
    r=capture_evidence(text)
    assert r['retained_reject_episodes']==3 and r['retained_recovery_episodes']==1
    assert r['fetch_error_signatures']=={'1':1,'4':1,'6':1}
    assert not r['capture_health_proven'] and r['whole_run_reject_count'] is None
    assert r['reject_time_ms'] is None
    assert r['history']['events'][0]['fetch_reasons']==['low_while_pair_pending']
    assert r['history']['events'][3]['fetch_reasons']==['invalid_low_address_or_lane','high_pair_check_failed']
    bads=[text.replace('EPISODE180_V3','REJECT180_V2'),text.replace('valid=1','valid=0'),
          text.replace('count=4','count=3'),text.replace('_00=','_09='),
          text.replace('55c000003ffff8c703a10001','55c000003fff78c703a10001')]
    for bad in bads:
        try: capture_evidence(bad)
        except AssertionError: pass
        else: raise AssertionError('accepted corrupt/schema-mismatched history')
    empty=capture_evidence(sample([]))
    assert not empty['capture_health_proven'], 'No retained episodes is not proof of no losses'
    print('PASS499: capture rejection attribution, no fabricated loss rate,5 malformed/schema guards,empty-history limit')


if __name__=='__main__': main()
