"""Generate the two computed entry points for the 23-row WRAM comparison."""
from nes_native_local165 import call


def emit(c,straight=False,indexed=False,bank_once=False):
    c.label('column_write')
    c.emit(0xc2,0x20,0xa9,22,0,0x85,0x60)
    # Each prefix entry is eight instruction bytes per 16-bit map word.
    # Each zero-tail entry is three bytes. Both entry addresses are computed
    # once from the independently checked even byte offset 0..34.
    c.long(0xaf,0x400014)
    c.emit(0x85,0x68,0x0a,0x0a,0x85,0x62)
    prefix=len(c.data)+1
    c.emit(0xa9,0,0,0x38,0xe5,0x62,0x85,0x64)
    if straight:c.emit(0xa5,0x68,0x4a,0x18,0x65,0x68,0x18)
    else:c.emit(0xa5,0x68,0x29,15,0,0x85,0x6a,0x4a,0x18,0x65,0x6a,0x18)
    tail=len(c.data)+1
    c.emit(0x69,0,0,0x85,0x66,0xa2,0,0,0xa4,0x7a)
    if not bank_once:c.label('column_row')
    c.emit(0x8b,0xe2,0x20,0xa9,0x7f,0x48,0xab,0xc2,0x20)
    if bank_once:c.label('column_row')
    # X remains the relative row. Y is the first partial 16-byte tilemap group.
    if not straight:c.emit(0x98,0x18,0x69,64,0,0x85,0x6c,0xa5,0x68,0x29,0xf0,0,0x18,0x65,0x7a,0x85,0x6a,0x8a,0x18,0x65,0x6a,0xa8)
    c.absolute(0x6c,0x64)
    c.label('prefix_bad');c.emit(0xab);c.jump('bad_packet')
    for word in reversed(range(17)):
        c.absolute(0xbd,0x5800+word*2);c.absolute(0xdd,0xd800+word*2)
        c.branch(0xd0,'prefix_bad' if word>=9 else 'low_bad')
    c.label('prefix_end')
    c.emit(0xa9,0,0);c.absolute(0x6c,0x66)
    c.label('low_bad');c.emit(0xab);c.jump('bad_packet')
    if not straight:c.label('full_suffix');c.absolute(0xb9,0)
    c.label('suffix')
    for word in range(1,32 if straight else 8):c.absolute(0x19,2*word)
    c.branch(0xd0,'low_bad')
    if not straight:c.emit(0x98,0x18,0x69,16,0,0xa8,0xc5,0x6c);c.branch(0xd0,'full_suffix')
    # The original index is restored before service. The new word itself is
    # always written to the inactive target and independently read back there.
    if indexed:
        # Y already holds the physical target row. ($68),Y adds the checked
        # column, and a short-lived X advances the packet pointer in one pass.
        c.emit(0xda,0xa6,0x60);c.long(0xbf,0x400000)
        c.emit(0xe8,0xe8,0x86,0x60,0xfa,0x91,0x68)
        c.label('column_written');c.emit(0xd1,0x68);c.branch(0xd0,'write_bad')
    else:
        c.emit(0x8a,0x18,0x65,0x68,0xa8,0xda,0xa6,0x60)
        c.long(0xbf,0x400000);c.emit(0xfa,0x91,0x7a)
        c.label('column_written');c.emit(0xd1,0x7a);c.branch(0xd0,'write_bad')
        c.emit(0xe6,0x60,0xe6,0x60)
    c.label('column_service')
    if not bank_once:c.emit(0xab)
    if straight:
        # Poll the actual STOP latch after every row. Run the joypad service
        # every fourth row and before accepting the last one. On STOP, use
        # its existing latch/invalidation block even if the line drops again.
        c.emit(0xe2,0x20)
        if bank_once:c.long(0xaf,0x006001)
        else:c.absolute(0xad,0x6001)
        c.branch(0x30,'latched_stop')
        c.emit(0xc2,0x20,0xa5,0x60,0x89,7,0);c.branch(0xf0,'full_service')
        c.emit(0xc9,68,0);c.branch(0xd0,'advance_row' if indexed else 'column_next')
        c.label('full_service')
    if bank_once:
        # The caller's DBR is still on the stack. Service uses bank 0 for
        # hardware IO. Keep its return value across the PLB flag update.
        c.emit(0xf4,0,0x7f,0xab)
        call(c,'service');c.emit(0xab,0xc9,0,0);c.branch(0xf0,'column_next')
        c.emit(0xab);c.jump('stop_packet')
    else:
        call(c,'service');c.branch(0xf0,'column_next');c.jump('stop_packet')
    if straight:
        c.label('latched_stop')
        if bank_once:c.emit(0xab)
        c.emit(0xa9,1);c.absolute(0x8d,0x1236)
        c.emit(0xc2,0x20);c.absolute(0x20,0x3609);c.jump('stop_packet')
    c.label('column_next');c.emit(0xa5,0x60,0xc9,68,0);c.branch(0xf0,'column_done')
    if indexed:c.label('advance_row')
    c.emit(0x8a,0x18,0x69,64,0,0xaa,0x18,0x65,0x7a,0xa8);c.jump('column_row')
    c.label('column_done')
    if bank_once:c.emit(0xab)
    c.jump('accepted')
    c.label('write_bad');c.emit(0xab);c.jump('bad_packet')
    for where,label in ((prefix,'prefix_end'),(tail,'suffix')):
        c.data[where:where+2]=(c.labels[label]&65535).to_bytes(2,'little')

    # Independently check each address reachable through the validated wire
    # column, including zero and the last word in the 36-byte prefix.
    for col in range(0,36,2):
        at=c.labels['prefix_end']-4*col-c.base
        if col:
            word=col-2
            assert bytes(c.data[at:at+6])==bytes([0xbd,word,0x58,0xdd,word,0xd8])
        else:
            assert bytes(c.data[at:at+3])==bytes([0xa9,0,0])
        skip=col if straight else col%16
        at=c.labels['suffix']+3*(skip//2)-c.base
        if straight or skip<14:
            assert bytes(c.data[at:at+3])==bytes([0x19,skip+2,0])
        else:
            assert c.data[at]==0xd0  # empty first group, zero from prefix_end
