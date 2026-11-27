"""Bind the paused FF3 register bus to live registers in the generated NES core."""
import re
from pathlib import Path


def replace_once(source, old, new):
    if source.count(old) != 1:
        raise ValueError(f"Expected one {old!r}")
    return source.replace(old, new)


def live_cpu(path):
    s = path.read_text()
    # Preserve the original VHDL field conversions and enum encodings.
    for bank in range(1, 4):
        rule = rf'(?m)^  iREG_SAVESTATE_T80_{bank} : .*?generic map \({bank-1}, (x"[0-9A-F]+")\).*?;$'
        s, count = re.subn(rule, rf'  SS_{bank} <= \1;', s)
        assert count == 1
    # Gate at the leaf. Reserved addresses contribute zero to the shared return.
    gating = []
    for bank in range(1, 4):
        gating.append(f'  reg_wired_or_{bank-1} <= SS_{bank}_BACK when SaveStateBus_Adr="{bank-1:010b}" else (others=>\'0\');')
    s = replace_once(s, '  SS_1 <=', '\n'.join(gating)+'\n  SS_1 <=')

    def process(m):
        body = m[0]
        fields = re.findall(r'^\s*(\w+(?:\(\s*\d+ downto \d+\))?)\s*<=\s*([^;\n]*\bSS_([123])\([^;\n]+);',body,re.M)
        if not fields:
            return body
        groups = {}
        for dest, rhs, bank in fields:
            groups.setdefault(int(bank)-1, []).append(
                f'              {dest} <= {rhs.replace("SS_"+bank,"SaveStateBus_Din")};')
        if 'S( 7 downto 0)' in body:
            groups[0].append("              S(15 downto 8) <= (others=>'0');")
        cold = [f'        {dest} <= {rhs};' for dest,rhs,_ in fields]
        if 'S( 7 downto 0)' in body:
            cold.append("        S(15 downto 8) <= (others=>'0');")
        for reg in ('ABC','X','Y'):
            if any(dest.startswith(reg+'(') for dest,_,_ in fields):
                cold.append(f"        {reg}(15 downto 8) <= (others=>'0');")
        apply = ["      if Pwr_n='0' then", *cold,
                 "      elsif SaveStateBus_load='1' and SaveStateBus_rst='0' then",
                 "        if SaveStateBus_wren='1' then",
                 "          case to_integer(unsigned(SaveStateBus_Adr)) is"]
        for word, writes in sorted(groups.items()):
            apply.extend([f"            when {word} =>", *writes])
        apply += ["            when others => null;", "          end case;", "        end if;", "      else"]
        edge = "if Clk'event and Clk = '1' then"
        body = replace_once(body, edge, edge+'\n'+'\n'.join(apply))
        return replace_once(body, '\n    end if;\n  end process;', '\n      end if;\n    end if;\n  end process;')
    s = re.sub(r'(?ms)^  process \(Clk\)\n.*?^  end process;',process,s)
    assert s.count("case to_integer(unsigned(SaveStateBus_Adr)) is")==4
    path.write_text(s)


def live_sv(path, names):
    s = path.read_text()
    # Each upstream process remains the sole writer of its registers. Keep
    # unrelated processes (including timing, OAM and sample generation) intact.
    for module, words in names.items():
        m = re.search(r'(?ms)^module '+module+r'\b.*?^endmodule\b',s)
        block = m[0]
        fields_seen = set()
        applied_fields = set()
        for state, (index, default) in words.items():
            rule = rf'(?m)^(\s*)eReg_SavestateV #\({index}, {default}\) \w+\s*\(clk, SaveStateBus_Din, SaveStateBus_Adr, SaveStateBus_wren, SaveStateBus_rst, ([\w\[\]]+),\s*{state}_BACK,\s*{state}\);'
            block,count = re.subn(rule,rf"\1assign \2 = (SaveStateBus_Adr=={index}) ? {state}_BACK : 64'h0;\n assign {state} = {default};",block)
            assert count == 1, state
        clocks = list(re.finditer(r'(?m)^(?P<indent>[ \t]*)always(?:_ff)? @\(posedge clk\) begin(?: :\w+| : \w+)?[ \t]*$',block))
        for proc in reversed(clocks):
            end = re.search(r'(?m)^'+proc['indent']+r'end\b',block[proc.end():])
            if not end:
                continue
            body = block[proc.end():proc.end()+end.start()]
            writes = []
            cold = []
            for state,(index,_) in words.items():
                fields = re.findall(r'(?m)^[ \t]*([\w\[\]:]+)\s*<=\s*'+state+r'(\[[^\]]+\]);',body)
                if fields:
                    fields_seen.add(state)
                    for dest,bits in fields:
                        assert dest not in applied_fields, (module, dest)
                        applied_fields.add(dest)
                        value = 'rst_behavior' if dest=='clear' else state+bits
                        cold.append(f'        {dest} <= {value};')
                    writes.append(f'      if (SaveStateBus_wren && SaveStateBus_Adr=={index}) begin')
                    writes += [f'        {dest} <= SaveStateBus_Din{bits};' for dest,bits in fields]
                    writes.append('      end')
            if writes:
                branch = "\n    if (SaveStateBus_load && !cold_reset && !SaveStateBus_rst) begin\n"
                middle = branch+'\n'.join(writes)+'\n    end else begin'+body+'      if (cold_reset) begin\n'+'\n'.join(cold)+'\n      end\n    end\n'
                block = block[:proc.end()]+middle+block[proc.end()+end.start():]
        assert fields_seen == set(words), (module, fields_seen)
        expected = {"PPU": 23, "APU": 3, "FrameCtr": 9, "DmcChan": 21}
        assert len(applied_fields) == expected[module], (module, applied_fields)
        s = s[:m.start()]+block+s[m.end():]
    path.write_text(s)


def bind(board: Path, cpu_writer=live_cpu):
    rtl = board/'rtl'
    cpu_writer(rtl/'t65/T65.vhd')
    pp = rtl/'ppu.sv'
    live_sv(pp, {'PPU':{'SS_PPU':('SSREG_INDEX_PPU_1','SSREG_DEFAULT_PPU_1'),
                         'SS_PPU_DECAY':('SSREG_INDEX_PPU_2','SSREG_DEFAULT_PPU_2')}})
    ap = rtl/'apu.sv'
    live_sv(ap, {'APU':{'SS_APU':('SSREG_INDEX_TOP','SSREG_DEFAULT_APU_TOP')},
                 'FrameCtr':{'SS_FCT':('SSREG_INDEX_FCT','SSREG_DEFAULT_APU_FCT')},
                 'DmcChan':{'SS_DMC1':('SSREG_INDEX_DMC1','SSREG_DEFAULT_APU_DMC1'),
                            'SS_DMC2':('SSREG_INDEX_DMC2','SSREG_DEFAULT_APU_DMC2')}})
