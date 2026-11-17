"""Restore the bulk receipt guard on the completed-BG scroll callback."""
import shutil

from prepare_nes_mask820 import edit
from prepare_nes_trial802 import PROBES, rename_edition


def prepare():
    src = PROBES / "nes-output823/link-824/src"
    dest = PROBES / "nes-trial825/patch"
    rename_edition(src, dest, 824, 825)
    sink = dest / "nes_native_sink165.c"
    shutil.copyfile(src / sink.name, sink)
    edit(sink, "if(!s->plan->bulk_pending && (((uint32_t)(map>>32))",
         """/* The two unchecked-for-plan-service scroll submissions can move a
  * live bulk target outside the four-head receipt window. Leave both to
  * the normal output path until the outstanding tile has retired. */
 if(s->plan->bulk_pending)return true;
 if((((uint32_t)(map>>32))""")


if __name__ == "__main__":
    prepare()
