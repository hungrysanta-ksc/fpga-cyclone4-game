"""Architecture budget and exhaustive phase-RAM layout audit, not RTL validation."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT.parent
pins = {}
def read(path):
    raw = path.read_bytes()
    pins[str(path.relative_to(BASE))] = hashlib.sha256(raw).hexdigest()
    return raw.decode('utf-8-sig')

d = json.loads(read(ROOT/'analysis/joint298-verification.json'))
assert d['whole_MAP']['comb'] == 17683
row = next(r for r in d['restricted'] if r['frame'] == 907)
live = BASE/'probes/nes-joint298/test04'
for name in ('nes_mux260.sv','nes_validator278.sv','nes_joint257.sv','nes_core257.sv','nes_plan_rom267.sv'):
    read(live/name)
read(BASE/'probes/nes-joint298/window04/joint266_tb.sv')
read(ROOT/'tools/nes_wait296.py')
read(ROOT/'tools/nes_bg293.py')

# Preserve logical bytes, not numerical old addresses. Source scratch is phase-exclusive.
old = dict(valid0=(0,166), valid1=(166,166), crc=(332,64), receipt=(396,166), map=(562,256), context=(832,36))
new = dict(valid0=(0,166), valid1=(256,166), crc=(448,64), receipt=(512,166), map=(768,256), context=(680,36))
used = set(); mapping = {}; new_used = set()
for name,(start,size) in old.items():
    ns,nsize = new[name]; assert nsize == size
    for offset in range(size):
        a,b=start+offset,ns+offset
        assert a not in used and b not in new_used and 0<=b<1024
        used.add(a);new_used.add(b);mapping[a]=b
assert len(mapping)==854
persistent = set(range(166)) | set(range(256,422)) | set(range(448,512))
scratch = set(range(512,1024))
clear_frame = set(range(512,678)) | set(range(768,1024))
context = set(range(680,716))
assert not persistent & scratch and not clear_frame & context
assert len(clear_frame)==422
# Exhaust all logical manifest addresses for both banks; the second persistent read
# (logical bytes144..165) remains distinct from the fresh receipt read.
checked = 0
for bank in (0,1):
    for cursor in range(422):
        a = bank*166+cursor if cursor<144 else 396+cursor if cursor<166 else 562+cursor-166
        b = bank*256+cursor if cursor<144 else 512+cursor if cursor<166 else 768+cursor-166
        assert mapping[a]==b
        checked += 1
        if 144<=cursor<166:
            assert mapping[bank*166+cursor] == bank*256+cursor
            checked += 1
assert not (set(range(148,166))|set(range(404,422))) & context
# This deliberate wrong clear range demonstrates why a base-only replacement fails.
bad_clear = set(range(512,1024))
assert bad_clear & context == context

regions=d['area']['regions']; fixed=sum(regions.values()); assert fixed==4837
gap=row['total_ms']-1000/60
windows=row['parser_windows_ms']+row['map_receipt_windows_ms']
service=row['service_instructions']/84000
result=dict(stage=299,scope='Static source audit + exhaustive address model + budget arithmetic; no new RTL/CPU/MAP',
    merge130='d7a96c5652d7c511d061ae5035277027c14ec597',
    whole_comb=17683,capacity=15408,deficit=2275,
    regions=regions,fixed_boundary=fixed,outside=12846,
    budgets=[dict(scope='host+validator',current=3427,ceiling=1152,ceiling_with_128_reserve=1024),
             dict(scope='fixed output boundary',current=fixed,ceiling=2562,ceiling_with_128_reserve=2434)],
    retained_queue_SPI_plan_glue=regions['queue']+regions['SPI']+regions['plan']+regions['glue'],
    time=dict(restricted907_ms=row['total_ms'],required_net_ms=gap,
              parser_receipt_sum_ms=windows,ideal_zero_windows_residual_ms=gap-windows,
              service_instructions=row['service_instructions'],service_CPI1_ms=service,
              ideal_remove_service_and_windows_residual_ms=gap-windows-service,
              warning='Impossible removals for diagnostic scale only; not additive recoverable time or a new schedule',
              minimum_ARM_instructions_at_CPI1=gap*84000,
              extra_wire_cost_ms_per_byte=8/2625000*1000,
              ROM_window_cycles=dict(period=357368,start=330088,end=354640,slot_modulo=12,core_modulo=120)),
    RAM_model=dict(old=old,proposed=new,logical_bytes=854,unused_addresses=1024-854,
                   translated_manifest_reads=checked,frame_clear_bytes=422,
                   persistent_source_disjoint=True,clear_preserves_context=True,
                   contiguous_clear_negative_detected=True,ports='A source clock; B host clock unchanged',
                   new_RAM_bits=0,RTL_equivalence_proven=False),
    projected_comb=None,projected_frame_ms=None,candidate_selected_for_production=False,
    input_hashes=pins)
(ROOT/'analysis/arch299-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps({k:result[k] for k in ('budgets','time','RAM_model')},ensure_ascii=False,indent=2))
