"""Build FF3's retained verified-ROM restart, and the matching interactive ARM."""
import argparse
from pathlib import Path
from prepare_ff3_play1045 import prepare
from ff3_backdrop1046 import patch_board, patch_arm
from prepare_ff3_display1045 import board1045
from prepare_nes_kirby1023 import edit


def arm(out):
    prepare(out)
    src=out/'src'
    patch_arm(src)
    # Reload the selected SD file's identity; the stopped FPGA still owns the
    # write-protected, physically compared PRG. Check the slot again at restore.
    edit(src,'nes_h1_stm32.c',
         (''' if(ff3_next_slot){
  expected_crc=nes_content_crc;
  memcpy(buffer,header,16);
  goto verify_payload;
 }
''',''),
         (' expected_crc=nes_content_crc=crc^0xffffffffu;', ''' expected_crc=crc^0xffffffffu;
 if(ff3_next_slot){
  if(expected_crc!=nes_content_crc || f_size(&file)!=total+16u){r->result=NES_MCU_LOAD_CHANGED;goto cleanup;}
  r->file_result=f_close(&file);opened=false;
  if(r->file_result!=FR_OK){r->result=NES_MCU_LOAD_CLOSE;goto cleanup;}
  report->verified=true;
  return true;
 }
 nes_content_crc=expected_crc;'''),
         ('verify_payload: ;',''),
         ('// STOP keeps PSRAM but revokes CHECK_FINISH. Recompare the full selected\n   // file and require a fresh FINISH before START may reset display ownership.',
          '// The slot STOP retains FINISH for this immutable PRG. Recheck SD identity.'))
    edit(src,'nes_run136.inc',
         ('nes_rom_spi_frame(stop_tx,NES_ROM_STOP,total,0);','nes_rom_spi_frame(stop_tx,NES_ROM_STOP,total,ff3_next_slot!=0);'),
         ('||s.flags!=2||s.count!=total','||s.flags!=(ff3_next_slot?0x82:2)||s.count!=total'))
    for filename in ('nes_menu_diagnostic.c','nes_checkpoint112.c'):
        file=src/filename
        text=file.read_text()
        assert 'ff31045' in text
        file.write_text(text.replace('ff31045','ff31046'))


def board(out,client):
    board1045(out,client)
    patch_board(out)
    from ff3_forced_blank1046 import patch as patch_closed
    patch_closed(out)
    edit(out,'nes_rom_spi.sv',
         ("((command==8'h60)?arg!=2:arg!=0)", "((command==8'h60)?arg!=2:(command==8'h64)?arg>1:arg!=0)"),
         (" wire state_verified=(verified && !(pending && pending_command==0) && !command_stop && !command_begin) || command_finish;",
          """ // A checkpoint STOP resets the game/renderer using the normal STOP pulse.
 // Reuse only a FINISH earned on this running, fault-free loaded image.
 wire slot_stop=pending_arg[0] && raw_run && raw_loaded && !boot_fault;
 wire image_write=pending && (pending_command==0 || pending_command==1);
 wire state_verified=(verified && !image_write && (!command_stop || slot_stop) && !command_begin) || command_finish;"""))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('out',type=Path)
    parser.add_argument('--client',type=Path)
    args=parser.parse_args()
    if args.client:board(args.out,args.client)
    else:arm(args.out)
