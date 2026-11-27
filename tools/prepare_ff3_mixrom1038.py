"""Map the original FF3 profile's exact 512-word APU transfer table to one M9K."""
import re


def map_mix_rom(board):
    path = board / 'rtl/apu.sv'
    s = path.read_text()
    before, start, tail = s.partition('logic [15:0] mix_lut[512];')
    assert start and tail.startswith("\nassign mix_lut = '{")
    body, end, after = tail.partition('};')
    words = re.findall(r"16'h([0-9a-fA-F]{4})", body)
    assert end and len(words) == 512
    init = '\n'.join(f" mix_lut[{i}]=16'h{w};" for i, w in enumerate(words))
    s = before + '(* romstyle="M9K" *) reg [15:0] mix_lut[0:511];\ninitial begin\n' + init + '\nend\n' + after
    for old, new in (('APUMixer mixer (', 'APUMixer mixer (.clk(clk),'),
                     ('module APUMixer (', 'module APUMixer (input logic clk,'),
                     ('wire [15:0] ch2;', 'reg [15:0] ch2;'),
                     ('assign ch2 = mix_lut[mix];', 'always @(negedge clk) ch2 <= mix_lut[mix];')):
        assert s.count(old) == 1, old
        s = s.replace(old, new)
    path.write_text(s)
