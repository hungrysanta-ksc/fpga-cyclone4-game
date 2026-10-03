"""C1 X-only, bounded line-185 capture and final CGRAM comparison.
Extra WRAM code 8000..9fff; data 1900..1c3f, below IRQ stub/stack.
1b00 marker A1=complete,00=skip,E1=bad table,E2=beam timeout,E3=late entry.
1b01 color count,02 first slot,04 got word,06 expected word,08 HDMA mask.
1b0a/0c stop H/V; 1a00..1a41 capture DMAP..NLTR for six channels.
"""

def emit_capture(a):
    a.label('c1_capture')
    for adr in range(0x1b00, 0x1b10): a.stz(adr)
    a.read(0x24);a.emit(0xc9,5);a.branch(0xd0,'c3_manual')
    # Already forced blank, before another install or monitor invocation.
    a.write(0x4201,0xff);a.jsr('c1_beam');a.jump('c1_stop')
    a.label('c3_manual')
    # Only the existing manual diagnostic on an installed, valid, HDMA frame.
    for adr, val in ((0x24,3),(0x3f,1),(0x2d,0x7f)):
        tag=f'c1_guard_{adr:x}'
        a.read(adr);a.emit(0xc9,val);a.branch(0xf0,tag);a.emit(0x60);a.label(tag)
    a.read(0x2a);a.emit(0x29,0x0b,0xc9,0x0a);a.branch(0xf0,'c1_valid');a.emit(0x60)
    a.label('c1_valid');a.write(0x4201,0xff);a.jsr('c1_beam')
    a.read(0x1b0d);a.branch(0xd0,'c1_late')
    a.read(0x1b0c);a.emit(0xc9,185);a.branch(0x90,'c1_wait_begin')
    a.label('c1_late');a.write(0x1b00,0xe3);a.emit(0x60)
    a.label('c1_wait_begin');a.ldx16(0xffff)
    a.label('c1_wait');a.jsr('c1_beam')
    a.read(0x1b0d);a.branch(0xd0,'c1_wait_next')
    a.read(0x1b0c);a.emit(0xc9,185);a.branch(0xf0,'c1_stop')
    a.label('c1_wait_next');a.emit(0xca);a.branch(0xd0,'c1_wait')
    a.write(0x1b00,0xe2);a.emit(0x60)
    a.label('c1_stop')
    a.stz(0x420c);a.write(0x2100,0x80)
    # Beam timestamp was latched just before disabling HDMA/forcing blank.
    for ch in range(7):
        for off in range(11):
            a.read(0x4300+ch*16+off);a.sta(0x1a00+ch*11+off)
    a.stz(0x2121);a.ldx16(0)
    a.label('c1_read_color')
    a.read(0x213b);a.emit(0x9d,0x80,0x19,0xe8)
    a.read(0x213b);a.emit(0x29,0x7f,0x9d,0x80,0x19,0xe8,0xe0,128,0)
    a.branch(0xd0,'c1_read_color');a.write(0x1b00,0x51);a.emit(0x60)
    a.label('c1_beam')
    a.read(0x213f);a.read(0x2137)
    for port,dest,high in ((0x213c,0x1b0a,False),(0x213c,0x1b0b,True),(0x213d,0x1b0c,False),(0x213d,0x1b0d,True)):
        a.read(port)
        if high:a.emit(0x29,1)
        a.sta(dest)
    a.emit(0x60)

def emit_compare(a):
    a.label('c1_compare')
    a.read(0x1b00);a.emit(0xc9,0x51);a.branch(0xf0,'c1_compare_valid');a.emit(0x60)
    a.label('c1_compare_valid')
    a.read(0x24);a.emit(0xc9,5);a.branch(0xf0,'c1_r1_good')
    a.read(0x185e);a.emit(0xc9,0xa1);a.branch(0xf0,'c1_r1_good');a.jump('c1_bad')
    a.label('c1_r1_good')
    a.read(0x12);a.emit(0x49,1,0x0a,0x0a,0x0a,0x0a,0x0a,0x09,0x40);a.sta(0x99)
    a.sta(0x91);a.write(0x90,0x80);a.write(0x92,0x7e);a.emit(0xa0,0,0)
    # Always derive lengths from the active buffer, not next-frame globals.
    a.label('c3_lengths');a.emit(0xb7,0x90,0x99,0x20,0x18,0xc8,0xc0,14,0);a.branch(0xd0,'c3_lengths')
    a.stz(0x90);a.emit(0xa0,0,0)
    a.label('c1_initial');a.emit(0xb7,0x90,0x99,0,0x19,0xc8,0xc0,128,0);a.branch(0xd0,'c1_initial')
    a.ldx16(63);a.label('c1_clear_stamps');a.lda8(0);a.emit(0x9d,0,0x1c,0xca);a.branch(0x10,'c1_clear_stamps')
    for ch in range(7):
        a.stz(0x90);a.read(0x99);a.emit(0x18,0x69,1+ch*3);a.sta(0x91)
        a.emit(0xae,0x20+2*ch,0x18);a.write(0x95,1);a.emit(0xa0,0,0);a.jsr('c1_table')
        a.read(0x1b00);a.emit(0xc9,0xe1);a.branch(0xd0,f'c1_ch_{ch}_ok');a.emit(0x60);a.label(f'c1_ch_{ch}_ok')
        # Final A2A must point just after terminator; DMAP/BBAD/bank/source
        # must identify this active table. Store one mismatch bit per channel.
        base=0x1a00+ch*11
        checks=[(base,3),(base+1,0x21),(base+2,0),(base+4,0x7e)]
        for adr,value in checks:
            a.read(adr);a.emit(0xc9,value);a.branch(0xd0,f'c1_hdma_bad_{ch}')
        a.read(base+3);a.emit(0xc5,0x91);a.branch(0xd0,f'c1_hdma_bad_{ch}')
        a.emit(0xc2,0x20,0x98,0x18,0x65,0x90,0xcd,base+8,(base+8)>>8,0xe2,0x20)
        a.branch(0xf0,f'c1_hdma_ok_{ch}')
        a.label(f'c1_hdma_bad_{ch}');a.read(0x1b08);a.emit(0x09,1<<ch);a.sta(0x1b08)
        a.label(f'c1_hdma_ok_{ch}')
    a.ldx16(0);a.emit(0xc2,0x20)
    a.label('c1_compare_word');a.emit(0xbd,0x80,0x19,0xdd,0,0x19);a.branch(0xf0,'c1_equal')
    a.emit(0xe2,0x20);a.read(0x1b01);a.branch(0xd0,'c1_seen')
    a.emit(0x8a,0x4a);a.sta(0x1b02);a.emit(0xc2,0x20,0xbd,0x80,0x19);a.sta(0x1b04)
    a.emit(0xbd,0,0x19);a.sta(0x1b06);a.emit(0xe2,0x20)
    a.label('c1_seen');a.emit(0xee,1,0x1b,0xc2,0x20)
    a.label('c1_equal');a.emit(0xe8,0xe8,0xe0,128,0);a.branch(0xd0,'c1_compare_word')
    a.emit(0xe2,0x20);a.write(0x1b00,0xa1);a.emit(0x60)

    a.label('c1_table')
    a.emit(0xe0,1,0);a.branch(0xd0,'c1_record')
    a.emit(0xb7,0x90);a.branch(0xd0,'c1_bad');a.emit(0xc8,0x60)
    a.label('c1_record');a.emit(0xe0,6,0);a.branch(0x90,'c1_bad')
    a.emit(0xb7,0x90);a.branch(0xf0,'c1_bad');a.branch(0x30,'c1_bad');a.sta(0x94)
    a.read(0x95);a.emit(0xc9,186);a.branch(0xb0,'c1_bad')
    a.emit(0xc8,0xb7,0x90,0xc9,64);a.branch(0xb0,'c1_bad');a.sta(0x96)
    a.emit(0xc8,0xb7,0x90,0xc5,0x96);a.branch(0xd0,'c1_bad')
    a.emit(0xc8,0xb7,0x90);a.sta(0x97)
    a.emit(0xc8,0xb7,0x90);a.branch(0x30,'c1_bad');a.sta(0x98)
    a.emit(0xc8,0xda) # preserve remaining bytes
    a.read(0x96);a.emit(0xc2,0x20,0x29,255,0,0xaa,0xe2,0x20)
    a.read(0x95);a.emit(0xdd,0,0x1c);a.branch(0x90,'c1_older')
    a.emit(0x9d,0,0x1c,0xc2,0x20,0x8a,0x0a,0xaa)
    a.read(0x97);a.emit(0x9d,0,0x19,0xe2,0x20)
    a.label('c1_older');a.emit(0xfa)
    a.read(0x95);a.emit(0x18,0x65,0x94);a.branch(0xb0,'c1_bad');a.sta(0x95)
    for _ in range(5):a.emit(0xca)
    a.jump('c1_table')
    a.label('c1_bad');a.write(0x1b00,0xe1);a.emit(0x60)
