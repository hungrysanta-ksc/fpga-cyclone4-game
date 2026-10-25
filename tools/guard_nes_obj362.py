# SPDX-License-Identifier: MIT
import guard_nes_hint361 as old
if __name__=='__main__':
 for a,b in [('gold[0:23]','gold[0:27]'),('j<24','j<28'),('cut<24','cut<28'),('k<24','k<28'),('send(24)','send(28)'),('send(25)','send(29)'),('packet[24]','packet[28]'),('j<22','j<26'),('packet[22]','packet[26]'),('packet[23]','packet[27]'),('reads!=80','reads!=112')]:
  assert a in old.TB,a;old.TB=old.TB.replace(a,b)
 old.TB=old.TB.replace('j<5;j++)if(source.cache_path.cache.valid[j]','j<7;j++)if(source.cache_path.cache.valid[j]')
 old.TB=old.TB.replace('nes_spi270 front(', 'nes_spi270 front(.progress_mode284(),.progress_irq284(),')
 old.TB=old.TB.replace('nes_plan_spi200 ep(', 'nes_plan_spi200 ep(.admit319(),')
 old.TB=old.TB.replace('source(.clk(n)', 'source(.done(),.busy(),.out_generation(),.out_slot(),.out_kind(),.out_length(),.out_index(),.out_data(),.out_valid(),.core_data(),.core_response_address(),.core_error(),.core_response(),.core_ready(),.plan_ready(),.clk(n)')
 old.TB=old.TB.replace('reader(.clk(n)', 'reader(.check_data(),.check_response_address(),.check_response(),.check_ready(),.clk(n)')
 old.main()
