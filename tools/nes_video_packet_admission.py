# Conservative offline admission for the bounded020 packet. SPDX-License-Identifier: MIT.
from build_nes_trace_replay import packet,convert,decode
from collections import Counter
from verify_nes_rtl_fetch import pixel_coordinate
REQUIRED={'ppu_mask','ppu_ctrl','scroll_x','scroll_y','active_ppu_writes','immutable_chr_rom'}
def admit(frame,seq,chrdata,features,reference):
    reasons=[]
    if not REQUIRED<=features.keys():
        return dict(accepted=False,reasons=['missing_control_evidence']),None
    if not features['immutable_chr_rom']:reasons.append('mutable_chr_unsupported')
    if len(chrdata)>16384:reasons.append('full_chr_atlas_exceeds_16kib')
    if features['ppu_mask']!=0x0a:reasons.append('ppu_mask_or_sprite_unsupported')
    if features['ppu_ctrl']&0x13:reasons.append('bg_table_or_nametable_unsupported')
    if features['scroll_x'] or features['scroll_y']:reasons.append('scroll_unsupported')
    if features['active_ppu_writes']:reasons.append('active_ppu_write_unsupported')
    if len(reference)!=256*240:reasons.append('incomplete_reference_frame')
    if any(e['frame']!=frame for e in seq):reasons.append('mixed_source_frames')
    slots=Counter((line,dot) for line in range(-1,240) for k in range(34)
                  for dot in ((8*k+5,8*k+7) if k<32 else (325+8*(k-32),327+8*(k-32))))
    if Counter((e['line'],e['dot']) for e in seq)!=slots:reasons.append('incomplete_bg_cadence')
    if any(b['tick']<=a['tick'] for a,b in zip(seq,seq[1:])):reasons.append('nonmonotonic_fetch')
    if any(not 0<=e['offset']<len(chrdata) or e['tile']!=e['offset']//16 or
           chrdata[e['offset']]!=e['value'] for e in seq):reasons.append('chr_event_mismatch')
    if any(e['pixel']!=(None if pixel_coordinate(e['line'],e['dot']) is None else
                       list(pixel_coordinate(e['line'],e['dot']))) for e in seq):reasons.append('coordinate_evidence_mismatch')
    if reasons:return dict(accepted=False,reasons=reasons),None
    try:
        p,release=packet(frame,seq)
        restored=decode(p,convert(chrdata))
    except (AssertionError,ValueError) as exc:
        return dict(accepted=False,reasons=['packet_representation:'+str(exc)]),None
    if restored!=reference:
        return dict(accepted=False,reasons=['full_frame_pixel_mismatch']),None
    return dict(accepted=True,reasons=[],packet_bytes=len(p),release_tick=release),p