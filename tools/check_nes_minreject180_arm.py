# SPDX-License-Identifier: MIT
"""Full linked stack review for strict schema3 optional history."""
import check_nes_reject180_arm as prior
from nes_reject180 import replace
source=prior.source.replace('rx[6]!=96||rx[7]!=2||','rx[6]!=96||rx[7]!=3||')
source=source.replace("'tools/check_nes_reject180_arm.py','tools/nes_reject180_mcu.py','tools/nes_reject180.py'", "'tools/check_nes_minreject180_arm.py','tools/nes_minreject180_mcu.py','tools/nes_reject180.py'")
source=source.replace('180 names/history version2 only;', '180 names/history version3 only;')
namespace=dict(prior.namespace)
exec(compile(source,'check_minreject180','exec'),namespace)
if __name__=='__main__':namespace['main']()
