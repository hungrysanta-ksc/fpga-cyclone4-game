"""SNES-side adapter for the frozen A7 endpoint and bounded SPC bootstrap.

The endpoint predates the real SNES JOY1 layout. Preserve that FPGA ABI here:
$6005 = reversed JOY1H, $6006 bit0 = JOY1L bit7 (A). Y/X/L/R are ignored
by the endpoint. Raw pad and audio status bytes remain in WRAM for tests.
"""
AUDIO_STATUS = 0x1c
AUDIO_FLG = 0x1d
PAD_LOW, PAD_HIGH, PAD_PACKED = 0x20, 0x21, 0x22


def spc_program():
    # Original SPC700 program. Internal voices/echo stay silent; the cartridge
    # DAC supplies the sound. IPL remains enabled for a renderer warm restart.
    code = bytearray((0xcd, 0xef, 0xbd, 0x20, 0x8f, 0x80, 0xf1))
    for reg, value in ((0x6c, 0x60), (0x4c, 0), (0x5c, 255),
                       (0x0c, 0), (0x1c, 0), (0x2c, 0), (0x3c, 0),
                       (0x4d, 0), (0x2d, 0), (0x3d, 0), (0x6c, 0x20)):
        code.extend((0x8f, reg, 0xf2, 0x8f, value, 0xf3))
    # Report DSP FLG readback, then ready token. A9 alone is not success.
    code.extend((0xe4, 0xf3, 0xc4, 0xf5, 0x8f, 0xa9, 0xf4))
    # Re-enter IPL when a newly reset S-CPU sends F0; otherwise idle.
    code.extend((0xe4, 0xf4, 0x68, 0xf0, 0xd0, 0xfa, 0x5f, 0xc0, 0xff))
    assert len(code) < 0xcc
    return bytes(code)


def emit_pad(a):
    a.read(0x4219); a.sta(PAD_HIGH)
    a.stz(PAD_PACKED)
    for _ in range(8):
        a.emit(0x4a)                       # LSR A: high-byte bit -> carry
        a.emit(0x2e, PAD_PACKED, 0)        # ROL packed
    a.read(PAD_PACKED); a.sta(0x6005)
    a.read(0x4218); a.sta(PAD_LOW)
    for _ in range(7): a.emit(0x4a)
    a.sta(0x6006)                          # commit once, after both bytes


def emit_audio(a):
    def wait_byte(name, port, value):
        a.ldx16(0xffff)
        a.label(name)
        a.read(port); a.emit(0xc9, value)
        a.branch(0xf0, name+'_ok')
        a.emit(0xca); a.branch(0xd0, name)
        a.jump('audio_done')               # bounded failure, keep stage
        a.label(name+'_ok')

    a.label('audio_init')
    a.write(AUDIO_STATUS, 1); a.stz(AUDIO_FLG)
    a.write(0x2140, 0xf0)                  # our previous driver -> IPL
    a.ldx16(0xffff)
    a.label('audio_ipl')
    a.read(0x2140); a.emit(0xc9, 0xaa)
    a.branch(0xd0, 'audio_ipl_retry')
    a.read(0x2141); a.emit(0xc9, 0xbb)
    a.branch(0xf0, 'audio_ipl_ok')
    a.label('audio_ipl_retry')
    a.emit(0xca); a.branch(0xd0, 'audio_ipl')
    a.jump('audio_done')
    a.label('audio_ipl_ok')
    a.write(AUDIO_STATUS, 2)
    a.stz(0x2142); a.write(0x2143, 1)       # upload at SPC $0100
    a.write(0x2141, 1); a.write(0x2140, 0xcc)
    wait_byte('audio_transfer', 0x2140, 0xcc)
    payload = spc_program()
    for seq, value in enumerate(payload):
        a.write(0x2141, value); a.write(0x2140, seq)
        wait_byte('audio_byte_'+str(seq), 0x2140, seq)
    a.write(AUDIO_STATUS, 3)
    a.stz(0x2142); a.write(0x2143, 1)
    a.stz(0x2141); a.write(0x2140, len(payload)+1)
    # The program may overwrite the final IPL echo before we see it. Its own
    # token/readback is the completion handshake, not that transient echo.
    wait_byte('audio_ready', 0x2140, 0xa9)
    a.read(0x2141); a.sta(AUDIO_FLG); a.emit(0xc9, 0x20)
    a.branch(0xd0, 'audio_done')
    a.write(AUDIO_STATUS, 0xa9)
    a.label('audio_done'); a.emit(0x60)

    a.label('audio_indicator')
    a.stz(0x212c); a.stz(0x2121)
    a.read(AUDIO_STATUS); a.emit(0xc9, 0xa9)
    a.branch(0xd0, 'audio_indicator_fail')
    a.write(0x2122, 0xe0); a.write(0x2122, 3)  # green
    a.jump('audio_indicator_show')
    a.label('audio_indicator_fail')
    a.write(0x2122, 0x1f); a.write(0x2122, 1)  # orange
    a.label('audio_indicator_show')
    a.write(0x2100, 15)
    a.ldx16(60)
    a.label('audio_indicator_frame')
    a.read(0x4212); a.emit(0x29, 0x80)
    a.branch(0xd0, 'audio_indicator_frame')
    a.label('audio_indicator_vblank')
    a.read(0x4212); a.emit(0x29, 0x80)
    a.branch(0xf0, 'audio_indicator_vblank')
    a.emit(0xca); a.branch(0xd0, 'audio_indicator_frame')
    a.write(0x2100, 0x80); a.write(0x212c, 1)
    a.emit(0x60)
