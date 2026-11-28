"""Build the next diagnostic profile from the selected 1059 links."""
from shutil import copytree
from prepare_cart_state1059 import OUT as PRIOR
from prepare_nes_kirby1023 import edit

OUT = PRIOR.parent / "nes-carts1060"


def prepare():
    for edition in ("debug", "release"):
        link = OUT / edition / "link"
        copytree(PRIOR / "vrc" / edition / "link", link, dirs_exist_ok=True)
        src = link / "src"
        if edition == "debug":
            # Continue validating the complete ROM on LOAD. Once full, reuse
            # the oldest sector, retaining the monotonic sequence on disk.
            edit(src, "nes_checkpoint112.c",
                 ("Each append uses a new data sector.", "A rotating sector holds one complete record."),
                 ("sequence>=256", "sequence==UINT32_MAX"),
                 ("if(f_size(&file)!=sequence*512u)", "if(f_size(&file)!=(sequence<256u?sequence:256u)*512u)"),
                 ("f_lseek(&file,sequence*512u)", "f_lseek(&file,(sequence&255u)*512u)"),
                 ("DEBUG1054 seq=", "DEBUG1060 seq="), ("debug1059", "debug1060"))
            edit(src, "nes_menu_diagnostic.c", ("debug1059", "debug1060"))
            edit(src, "nes_budget210.c", ("edition=1059", "edition=1060"))


if __name__ == "__main__":
    prepare()
