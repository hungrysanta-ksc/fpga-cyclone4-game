"""Keep the hardware-tested MMC825 runtime and split display completions at 30 s."""
import shutil

from prepare_nes_mask820 import edit
from prepare_nes_trial802 import PROBES, rename_edition


if __name__ == "__main__":
    source = PROBES / "nes-output823/link-825/src"
    patch = PROBES / "nes-trial826/patch"
    rename_edition(source, patch, 825, 826)
    counter = patch / "nes_budget210.c"
    shutil.copyfile(source / counter.name, counter)
    edit(counter, "elapsed>=500 && elapsed<5500)s->displayed_window[elapsed>=4000]",
         "elapsed>=100 && elapsed<6000)s->displayed_window[elapsed>=3000]")
    edit(counter, "display_5_40_55=", "display_1_30_60=")
