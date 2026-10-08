# SPDX-License-Identifier: MIT
"""Correct the diagnostic menu address without modifying frozen076/094 inputs."""
def once(text, old, new):
    assert text.count(old) == 1, old
    return text.replace(old, new, 1)

def adapt(src):
    p = src / 'memory.c'
    s = once(p.read_text(), '||flags||base_addr)',
             '||flags||base_addr!=SRAM_MENU_ADDR)')
    p.write_text(s, encoding='utf-8', newline='\n')
    p = src / 'nes_menu_return.c'
    s = once(p.read_text(), 'size==NES_MENU076_SIZE&&!offset&&!address;',
             'size==NES_MENU076_SIZE&&!offset&&address==SRAM_MENU_ADDR;')
    p.write_text(s, encoding='utf-8', newline='\n')
