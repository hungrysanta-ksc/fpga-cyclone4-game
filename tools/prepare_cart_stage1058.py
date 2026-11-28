"""Generate the 1058 mapper boards from the 1057 hardware-tested images."""
from shutil import copytree
from prepare_cart_stage1057 import OUT as BASE
from prepare_nes_kirby1023 import edit

OUT = BASE.parent / "nes-carts1058"


def prepare():
    for mapper in (7, 21):
        copytree(BASE / f"board-{mapper}", OUT / f"board-{mapper}", dirs_exist_ok=True)
    # The pre-render scanline is encoded as 511. Rendering can restart there
    # just as on a visible line, including the even dot without a preceding ALE.
    edit(OUT / "board-21/rtl", "ppu.sv",
         ("earlynormal707=re_sr[1] && !re_sr[2] && scanline<240",
          "earlynormal707=re_sr[1] && !re_sr[2] && in_rendering_frame"),
         ("restart160 = !re_sr[2] && scanline<240",
          "restart160 = !re_sr[2] && in_rendering_frame"),
         ("assign game160_restart_hint=restart160 || (earlynormal707 && normal155);",
          """assign game160_restart_hint=restart160 || (earlynormal707 && normal155) ||
    (is_pre_render_line && normal155 && cycle[2:0]==3);"""))
    # modified is the accumulated write set since the previous retirement.
    # On a prefix write fall back to its conservative page mask, including
    # this very write; a single-group receipt cannot describe the union.
    edit(OUT / "board-7", "nes_chr_snapshot.sv",
         ("clean_pages<=0;fine_receipt<=0;\n   end",
          "clean_pages<=~(modified|write_mask);fine_receipt<=0;\n   end"))


def debug_link():
    link = OUT / "debug/link"
    copytree(BASE / "debug/link", link, dirs_exist_ok=True)
    for name in ("nes_checkpoint112.c", "nes_menu_diagnostic.c"):
        edit(link / "src", name, ("debug1057", "debug1058"))
    edit(link / "src", "nes_budget210.c", ("edition=1057","edition=1058"))


if __name__ == "__main__":
    prepare()
    debug_link()
