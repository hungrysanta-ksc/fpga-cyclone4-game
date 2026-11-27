"""Generate the FF3 T65 with shared execution and checkpoint write paths."""
import re
from pathlib import Path


def replace(source, original, revised):
    if source.count(original) != 1:
        raise ValueError(original)
    return source.replace(original, revised)


def share_address_adders(cpu: Path):
    source = cpu.read_text()
    source = replace(source, "  signal state_write :", """  signal stack_down : std_logic;
  signal stack_step : unsigned(15 downto 0);
  signal ad_step : unsigned(7 downto 0);
  signal bal_base, bal_step : unsigned(8 downto 0);
  signal state_write :""")
    source = replace(source, "  execute_native <=", """  stack_down <= Dec_S and (not RstCycle or not (Mode(1) or Mode(0)));
  stack_step <= (0=>'1', others=>stack_down);
  ad_step <= to_unsigned(1,8) when ADAdd='0' else
             unsigned(Y(7 downto 0)) when AddY='1' else unsigned(X(7 downto 0));
  bal_base <= unsigned((BAL(8) and BAAdd(0)) & BAL(7 downto 0));
  bal_step <= to_unsigned(1,9) when BAAdd="01" else resize(unsigned(BusA),9);
  execute_native <=""")
    start = source.index("          if Inc_S = '1' then")
    end = source.index("          if IR = ", start)
    assert source[start:end].count("S <=") == 2
    source = source[:start]+"""          if Inc_S='1' or stack_down='1' then
            S <= S + stack_step;
          end if;

"""+source[end:]
    start = source.index('          case BAAdd is')
    end = source.index('            -- BA Adj', start)
    assert source[start:end].count("BAL <=") == 2
    source = source[:start]+"""          if BAAdd="01" or ADAdd='1' then
            AD <= std_logic_vector(unsigned(AD) + ad_step);
          end if;
          case BAAdd is
            when "01" | "10" =>
              BAL <= std_logic_vector(bal_base + bal_step);
            when "11" =>
"""+source[end:]
    start = source.index("          -- modified to use Y register as well", start)
    end = source.index('          if IR = ', start)
    assert source[start:end].count("AD <=") == 2
    cpu.write_text(source[:start]+source[end:])


def share_program_counter(cpu: Path):
    """One write enable per PC byte, including branch/carry overlap."""
    source = cpu.read_text()
    start = source.index("          if IR = \"00000000\" and MCycle = \"001\"")
    end = source.index("          end case;", start)+len("          end case;")
    assert source[start:end].count("PC") >= 10
    source = source[:start]+source[end:]
    source = replace(source, """            if IRQCycle = '0' and NMICycle = '0' then
              PC <= PC + 1;
            end if;
""", "")
    # Both warm reset and direct load are now handled by the owner below.
    for value in ("SS_1", "state_data_0"):
        source, count = re.subn(r"(?m)^\s*PC\s*<= unsigned\("+value+r"\(15 downto  0\)\);[^\n]*", "", source)
        assert count == 1
    source = replace(source, "  signal stack_down :", """  signal pc_run, pc_inc, pc_jump, pc_branch, pc_adjust, pc_carry : boolean;
  signal pc_file, pc_clear : boolean;
  signal high_delta, next_high, next_low : unsigned(7 downto 0);
  signal stack_down :""")
    source = replace(source, "  stack_down <=", """  pc_run <= execute_native='1' and Res_n_i='1' and SaveStateBus_load='0'
            and Enable='1' and really_rdy='1';
  pc_inc <= (MCycle="000" and IRQCycle='0' and NMICycle='0') or
            (IR=x"00" and MCycle="001" and IRQCycle='0' and NMICycle='0') or Jump="01";
  pc_jump <= Jump="10";
  pc_branch <= Jump="11";
  pc_adjust <= pc_branch and PCAdder(8)='1';
  pc_carry <= pc_inc and PC(7 downto 0)=x"ff";
  pc_file <= state_write(0)='1' and Pwr_n='1';
  pc_clear <= Pwr_n='0' or (execute_native='1' and Res_n_i='0');
  high_delta <= x"ff" when pc_adjust and DL(7)='1' else x"01";
  next_high <= unsigned(DI) when pc_jump else PC(15 downto 8)+high_delta;
  next_low <= unsigned(DL) when pc_jump else PCAdder(7 downto 0) when pc_branch
              else PC(7 downto 0)+1;
  process(Clk)
  begin
    if rising_edge(Clk) then
      if pc_file or pc_clear or (pc_run and (pc_inc or pc_jump or pc_branch)) then
        if pc_file then PC(7 downto 0) <= unsigned(SaveStateBus_Din(7 downto 0));
        elsif pc_clear then PC(7 downto 0) <= x"00";
        else PC(7 downto 0) <= next_low; end if;
      end if;
      if pc_file or pc_clear or (pc_run and (pc_jump or pc_adjust or pc_carry)) then
        if pc_file then PC(15 downto 8) <= unsigned(SaveStateBus_Din(15 downto 8));
        elsif pc_clear then PC(15 downto 8) <= x"00";
        else PC(15 downto 8) <= next_high; end if;
      end if;
    end if;
  end process;
  stack_down <=""")
    cpu.write_text(source)


def share_byte_writes(cpu: Path):
    """Route the normal ALU byte once to A/X/Y and keep a single writer per register."""
    source = cpu.read_text()
    for reg in ("ABC", "X", "Y", "BusA_r", "BusB", "BusB_r"):
        # High halves never receive an execution write. Keep their cold defaults.
        source, count = re.subn(
            rf"(?m)^([ \t]*){reg}(?:\(7 downto 0\))?[ \t]*<=[^;]*;[^\n]*",
            r"\1null;", source)
        assert count == (4 if reg in ("ABC","X","Y") else 3), reg
    source = replace(source, "  signal stack_down :", """  signal gpr_clock, bus_clock, clear_gpr, clear_bus : boolean;
  signal gpr_value, port_a, port_b, port_inc : std_logic_vector(7 downto 0);
  signal gpr_file, bus_file : std_logic_vector(7 downto 0);
  signal stack_down :""")
    process = """  gpr_clock <= execute_native='1' and SaveStateBus_load='0' and Enable='1'
               and really_rdy='1' and MCycle="000";
  bus_clock <= pc_run;
  clear_gpr <= Pwr_n='0' or (execute_native='1' and SaveStateBus_load='1');
  clear_bus <= pc_clear;
  gpr_value <= ALU_Q when gpr_clock else x"00";
  port_a <= BusA when bus_clock else x"00";
  port_b <= DI when bus_clock else x"00";
  port_inc <= std_logic_vector(unsigned(DI)+1) when bus_clock else x"00";
  gpr_file <= (others=>'1') when Pwr_n='1' and state_write(1)='1' else (others=>'0');
  bus_file <= (others=>'1') when Pwr_n='1' and state_write(2)='1' else (others=>'0');
  process(Clk)
  begin
    if rising_edge(Clk) then
"""
    fields = [("ABC(7 downto 0)","gpr_clock and LDA='1'", "gpr_value", 1,10),
              ("X(7 downto 0)","gpr_clock and LDX='1'", "gpr_value", 1,18),
              ("Y(7 downto 0)","gpr_clock and LDY='1'", "gpr_value", 1,26),
              ("BusA_r","bus_clock","port_a",2,0),
              ("BusB","bus_clock","port_b",2,8),
              ("BusB_r","bus_clock and (Set_Addr_To_r=Set_Addr_To_PBR or Set_Addr_To_r=Set_Addr_To_ZPG)","port_inc",2,16)]
    for target, active, run_data, bank, lo in fields:
        owner = "gpr" if bank==1 else "bus"
        process += f"""      if ({active}) or clear_{owner} or state_write({bank})='1' then
        {target} <= {run_data} or (SaveStateBus_Din({lo+7} downto {lo}) and {owner}_file);
      end if;
"""
    process += "    end if;\n  end process;\n"
    cpu.write_text(replace(source, "  stack_down <=", process+"  stack_down <="))

def bind_nes_mode(cpu: Path):
    """Use the immutable NES mode pin during execution and in checkpoint readback."""
    binding = (cpu.parents[1] / "nes.v").read_text()
    cpu_instance = re.search(r"\bT65\s+cpu\s*\((.*?)\);", binding, re.S)
    if not cpu_instance or not re.search(r"\.mode\s*\(\s*2'b00\s*\)", cpu_instance[1]):
        raise ValueError("FF3 checkpoint mode requires a fixed 2A03 CPU mode")
    source = cpu.read_text()
    source, count = re.subn(r"(?im)^[ \t]*Mode_r[ \t]*<=.*?;[^\n]*$", "", source)
    assert count in (3, 4)
    source = replace(source, "  stack_down <=", "  Mode_r <= Mode;\n  stack_down <=")
    cpu.write_text(source)


def shared_cpu_writes(path):
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
    s = replace(s, '  SS_1 <=', '\n'.join(gating)+'\n  SS_1 <=')

    declarations = ["  signal state_write : std_logic_vector(2 downto 0);",
                    "  signal execute_native : std_logic;"]
    controls = ["  execute_native <= Pwr_n and (not SaveStateBus_load or SaveStateBus_rst);"]
    for index in range(3):
        word = f"state_data_{index}"
        declarations.append(f"  signal {word} : std_logic_vector(63 downto 0);")
        controls.extend([
            f"  {word} <= SS_{index+1} when Pwr_n='0' else SaveStateBus_Din;",
            f"  state_write({index}) <= '1' when Pwr_n='0' or "
            f"(SaveStateBus_load='1' and SaveStateBus_rst='0' and SaveStateBus_wren='1' "
            f"and SaveStateBus_Adr=\"{index:010b}\") else '0';",
        ])
    s = replace(s, "  reg_wired_or_0 <=", "\n".join(controls)+"\n  reg_wired_or_0 <=")
    s = replace(s, "signal reg_wired_or_0 :", "\n".join(declarations)+"\n  signal reg_wired_or_0 :")

    def process(match):
        body = match[0]
        fields = re.findall(r'^\s*(\w+(?:\(\s*\d+ downto \d+\))?)\s*<=\s*([^;\n]*\bSS_([123])\([^;\n]+);', body, re.M)
        if not fields:
            return body
        groups = {}
        for dest, rhs, bank in fields:
            index = int(bank)-1
            restored = rhs.replace(f'SS_{bank}', f'state_data_{index}')
            groups.setdefault(index, []).append(f'          {dest} <= {restored};')
        if 'S( 7 downto 0)' in body:
            groups[0].append("          S(15 downto 8) <= (others=>'0');")
        extra = []
        for reg in ('ABC', 'X', 'Y'):
            if any(dest.startswith(reg+'(') for dest,_,_ in fields):
                extra.append(f"          {reg}(15 downto 8) <= (others=>'0');")
        dispatch = ["      else"]
        for index, writes in sorted(groups.items()):
            dispatch.extend([f"        if state_write({index})='1' then", *writes, "        end if;"])
        if extra:
            dispatch.extend(["        if Pwr_n='0' then", *extra, "        end if;"])
        dispatch.append("      end if;")
        edge = "if Clk'event and Clk = '1' then"
        body = replace(body, edge, edge+"\n      if execute_native='1' then")
        return replace(body, '\n    end if;\n  end process;',
                            '\n'+'\n'.join(dispatch)+'\n    end if;\n  end process;')

    s = re.sub(r'(?ms)^  process \(Clk\)\n.*?^  end process;', process, s)
    assert s.count("if execute_native='1' then") == 4
    path.write_text(s)

def bind_cpu(cpu: Path):
    shared_cpu_writes(cpu)
    share_address_adders(cpu)
    share_program_counter(cpu)
    share_byte_writes(cpu)
    bind_nes_mode(cpu)
