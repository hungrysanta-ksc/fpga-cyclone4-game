-- Lossless one-word lookahead cache. Physical word address includes the MBC bank.
-- One outstanding request; a stale return cannot be reported as a live hit.
-- No CPU clock gating, WAIT insertion, or guessed opcode bytes.
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
entity rom_prefetch is
 generic(FORWARD_RESPONSE:boolean:=true);
 port(clk,reset:in std_logic;
      cart_active:in std_logic;
      word_addr:in unsigned(21 downto 0);
      byte_select:in std_logic;
      req_valid:out std_logic;req_ready:in std_logic;
      req_addr:out unsigned(21 downto 0);
      rsp_valid:in std_logic;rsp_data:in std_logic_vector(15 downto 0);
      hit:out std_logic;data:out std_logic_vector(7 downto 0));
end;
architecture rtl of rom_prefetch is
 signal forwarding:std_logic;
 signal selected_data:std_logic_vector(15 downto 0);
 signal valid,pending,request:std_logic:='0';
 signal cached_tag,pending_tag:unsigned(21 downto 0):=(others=>'0');
 signal cached_data:std_logic_vector(15 downto 0):=(others=>'0');
begin
 forwarding<='1' when FORWARD_RESPONSE and reset='0' and pending='1' and rsp_valid='1' and pending_tag=word_addr else '0';
 selected_data<=rsp_data when forwarding='1' else cached_data;
 hit<='1' when reset='0' and cart_active='1' and (forwarding='1' or (valid='1' and cached_tag=word_addr)) else '0';
 request<='1' when reset='0' and cart_active='1' and pending='0' and
          (valid='0' or cached_tag/=word_addr) else '0';
 req_valid<=request;
 req_addr<=word_addr;
 data<=selected_data(7 downto 0) when byte_select='0' else selected_data(15 downto 8);
 process(clk) begin if rising_edge(clk) then
  if reset='1' then valid<='0';pending<='0';
  else
   if request='1' and req_ready='1' then
    pending<='1';pending_tag<=word_addr;
   end if;
   if rsp_valid='1' and pending='1' then
    cached_data<=rsp_data;cached_tag<=pending_tag;valid<='1';pending<='0';
   end if;
  end if;
 end if;end process;
end;
