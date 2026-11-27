-- FF3 cartridge profile. The 1036 SD format has 64 register words,
-- then OAM, mapper RAM, CHR, nametable, CPU RAM and battery RAM.
-- Only the architecture is substituted; the upstream entity is retained.
architecture ff3 of savestates is
   type phase is (idle, settle, header_issue, header_wait,
                  reg_issue, reg_wait, reg_next, apply_regs, palette_byte, palette_send,
                  ram_issue, ram_wait, byte_begin, byte_wait, byte_done,
                  word_next, finish);
   signal state : phase := idle;
   signal writing_core : std_logic := '0';
   signal word_index : unsigned(11 downto 0) := (others => '0');
   signal region : integer range 0 to 5 := 0;
   -- File words 65,97,98,1122,1378,1634 start the six RAM regions.
   signal ram_word, aligned_word : unsigned(9 downto 0);
   signal subaddr : unsigned(4 downto 0) := (others=>'0');
   signal offset : unsigned(12 downto 0);
   signal delay_count : integer range 0 to 100 := 0;
   signal word_data : std_logic_vector(63 downto 0);
   type bases is array(0 to 5) of integer;
   constant region_base : bases := (0,0,16#200000#,16#3a0000#,16#380000#,16#3c0000#);
   constant last_word : bases := (96,97,1121,1377,1633,2657);
   signal last_region_byte : boolean;
   signal palette_word, mapper_word, serial_read : boolean;
   constant size_header : std_logic_vector(63 downto 0) := x"000014C400000000";
begin
   -- All region bases are 8 KiB aligned. No carry crosses the region boundary.
   aligned_word <= word_index(9 downto 0)-to_unsigned(98,10);
   with region select ram_word <=
      resize(word_index(4 downto 0)-1,10) when 0,
      (others=>'0') when 1,
      aligned_word when 2,
      aligned_word xor to_unsigned(512,10) when 5,
      resize(aligned_word(7 downto 0),10) when others;
   offset <= resize(subaddr,13) when state=palette_byte else ram_word & subaddr(2 downto 0);
   Save_RAMAddr <= std_logic_vector(to_unsigned(region_base(region)/8192,12)) & std_logic_vector(offset);
   -- Disk words 8..11 hold interleaved columns of the 32-entry palette.
   palette_word <= word_index(11 downto 2)=to_unsigned(2,10);
   mapper_word <= word_index>=33 and word_index<=35;
   serial_read <= palette_word or (mapper_word and writing_core='0');
   Save_RAMType <= "110" when state=palette_byte and palette_word and reset_in='0' else to_unsigned(region,3);
   Save_RAMWriteData <= word_data(7 downto 0);
   last_region_byte <= word_index = to_unsigned(last_word(region),12);
   savestate_busy <= '0' when state=idle else '1';
   sleep_savestate <= '0' when state=idle else '1';
   bus_out_Adr <= std_logic_vector(to_unsigned(savestate_address/8192,13)) & std_logic_vector(word_index) & '0';
   bus_out_rnw <= writing_core;
   bus_out_be <= x"F0" when state=header_issue or state=header_wait else x"FF";
   bus_out_Din <= size_header when state=header_issue or state=header_wait else
                  word_data;
   BUS_Din <= bus_out_Dout;
   process(clk)
   begin
      if rising_edge(clk) then
         reset_ss <= '0'; reset_delay <= '0'; load_done <= '0';
         bus_out_ena <= '0'; BUS_wren <= '0'; BUS_rst <= '0';
         Save_RAMWrEn <= '0'; Save_RAMRdEn <= '0';
         if reset_in='1' then
            state <= idle; BUS_rst <= '1'; reset_ss <= '1'; reset_delay <= '1';
            saving_savestate <= '0'; loading_savestate <= '0';
         else
            case state is
               when idle =>
                  if save='1' or load='1' then
                     writing_core <= load; delay_count <= 100; state <= settle;
                     word_index <= (others=>'0'); BUS_Adr <= (others=>'0');
                     region <= 0; subaddr <= (others=>'0');
                  end if;
               when settle =>
                  if paused='0' then delay_count <= 100;
                  elsif delay_count/=0 then delay_count <= delay_count-1;
                  elsif writing_core='1' then state <= header_issue;
                  else word_index <= to_unsigned(1,12); saving_savestate <= '1'; state <= reg_issue;
                  end if;
               when header_issue =>
                  bus_out_ena <= '1'; state <= header_wait;
               when header_wait =>
                  if bus_out_done='1' then
                     if writing_core='0' then state <= finish;
                     elsif bus_out_Dout(63 downto 32)/=size_header(63 downto 32) then state <= idle;
                     else word_index <= to_unsigned(1,12); loading_savestate <= '1'; state <= reg_issue;
                     end if;
                  end if;
               when reg_issue =>
                  if serial_read and writing_core='0' then
                     if palette_word then subaddr <= resize(word_index(1 downto 0),subaddr'length);
                     else subaddr <= (others=>'0');
                     end if;
                     state <= palette_byte;
                  else
                     -- The serializer uses this owner until its exact-word ACK.
                     if writing_core='0' then word_data <= BUS_Dout; end if;
                     bus_out_ena <= '1'; state <= reg_wait;
                  end if;
               when reg_wait =>
                  if bus_out_done='1' then
                     if palette_word and writing_core='1' then
                        word_data <= bus_out_Dout;
                        subaddr <= resize(word_index(1 downto 0),subaddr'length);
                        state <= palette_byte;
                     else BUS_wren <= writing_core; state <= reg_next;
                     end if;
                  end if;
               when palette_byte =>
                  if palette_word then word_data <= Save_RAMReadData & word_data(63 downto 8);
                  else word_data <= BUS_Dout(7 downto 0) & word_data(63 downto 8);
                  end if;
                  if (palette_word and offset(4 downto 2)="111") or
                     (not palette_word and offset(2 downto 0)="111") then
                     subaddr <= (others=>'0');
                     if writing_core='1' then state <= reg_next; else state <= palette_send; end if;
                  elsif palette_word then subaddr <= subaddr+4;
                  else subaddr <= subaddr+1;
                  end if;
               when palette_send =>
                  bus_out_ena <= '1'; state <= reg_wait;
               when reg_next =>
                  word_index <= word_index+1;
                  if word_index=64 then state <= apply_regs;
                  else BUS_Adr <= std_logic_vector(unsigned(BUS_Adr)+1); state <= reg_issue;
                  end if;
               when apply_regs =>
                  reset_ss <= writing_core;
                  if writing_core='1' then state <= ram_issue; else state <= byte_begin; end if;
               when ram_issue =>
                  bus_out_ena <= '1'; state <= ram_wait;
               when ram_wait =>
                  if bus_out_done='1' then
                     if writing_core='1' then word_data <= bus_out_Dout; state <= byte_begin;
                     else state <= word_next;
                     end if;
                  end if;
               when byte_begin =>
                  Save_RAMWrEn <= writing_core; Save_RAMRdEn <= not writing_core;
                  delay_count <= 6; state <= byte_wait;
               when byte_wait =>
                  Save_RAMRdEn <= not writing_core;
                  if delay_count/=0 then delay_count <= delay_count-1;
                  else state <= byte_done;
                  end if;
               when byte_done =>
                  word_data <= Save_RAMReadData & word_data(63 downto 8);
                  if offset(2 downto 0)/="111" then subaddr <= subaddr+1; state <= byte_begin;
                  elsif writing_core='1' then state <= word_next;
                  else state <= ram_issue;
                  end if;
               when word_next =>
                  word_index <= word_index+1;
                  subaddr <= (others=>'0');
                  if last_region_byte and region=5 then
                     word_index <= (others=>'0');
                     if writing_core='1' then state <= finish; else state <= header_issue; end if;
                  else
                     if last_region_byte then region <= region+1; end if;
                     if writing_core='1' then state <= ram_issue; else state <= byte_begin; end if;
                  end if;
               when finish =>
                  saving_savestate <= '0'; loading_savestate <= '0';
                  load_done <= writing_core; state <= idle;
            end case;
         end if;
      end if;
   end process;
end architecture;
