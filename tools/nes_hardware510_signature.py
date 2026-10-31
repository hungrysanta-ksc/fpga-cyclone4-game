# SPDX-License-Identifier: MIT
"""Strict observed509 terminal ordinary-credit signature, not a general error waiver."""
def ordinary_deadline(g,b):
    request=bytes.fromhex(g.get('sink_trace_request_hex',''))
    expected={'candidate':'NES-MMC509','native_result':'1','native_video_error':'0','native_receiver_error':'0',
              'native_sink_error':'2','sink_window_error':'2','plan_error':'0','plan_sent':'1','plan_end':'1',
              'trace_aborts':'0','fault_context_valid':'0','sink_trace_valid':'1','sink_trace_ack_valid':'0',
              'sink_trace_mismatch_hex':'00','sink_trace_ack_hex':'0'*24,'sink_window_flags':'7','sink_window_ack':'0'}
    return (all(g.get(k)==v for k,v in expected.items()) and
            all(b.get(k)==v for k,v in {'boot_reason':'1','cost_transfer_stops':'0','failed_transfers':'0','cost_crc_errors':'0'}.items()) and
            ((int(g['sink_window_sent'])-int(g['sink_window_retired']))&65535)==4 and
            (int(b['cost_op_05'].split(',')[0])&65535)==int(g['sink_window_sent']) and
            int(g['trace_begins'])==int(g['trace_ends'])==int(g['trace_commits'])==int(g['native_frames'])+1 and
            5900<=int(g['profile_last_display_tick'])<=6020 and
            len(request)==16 and request[:4]==b'\x02\x05\x11\x00' and
            int.from_bytes(request[4:8],'little')==int(g['native_frames'])+1 and
            int.from_bytes(request[8:10],'little')==int(g['trace_generation']) and
            request[10:]==b'\xe1\x05\x51\x00\x00\x00')
