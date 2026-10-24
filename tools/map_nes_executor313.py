# SPDX-License-Identifier: MIT
"""Whole Lite MAP, including two-slot/status and canonical manifest costs."""
import inspect
import map_nes_joint284 as old
from nes_slots312 import apply as slots
from nes_record312 import apply as record
from nes_executor313 import apply as executor
from nes_manifest313 import apply as manifest
from nes_consumer313 import apply as consumer
from nes_admission313 import apply as admission


def apply(d):
    slots(d);record(d);executor(d);manifest(d);consumer(d);admission(d)


def main():
    s=inspect.getsource(old.main).replace('probes/nes-joint280/board01','probes/nes-ingress307/board03')
    s=s.replace("('nes_joint282.py','nes_joint283.py','nes_joint284.py','map_nes_joint284.py')",
                "('nes_slots312.py','nes_record312.py','nes_executor313.py','nes_manifest313.py','nes_consumer313.py','nes_admission313.py','map_nes_executor313.py')")
    ns=dict(old.__dict__);ns['apply']=apply
    exec(compile(s,'map313','exec'),ns);ns['main']()


if __name__=='__main__':main()
