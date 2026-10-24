# SPDX-License-Identifier: MIT
"""Retained325 fault injection with the actual330 ARM binary."""
import inspect
import guard_nes_arm328 as base

def main():
    s=inspect.getsource(base.main).replace('probe_nes_joint328.py','probe_nes_resume330.py')
    ns=dict(base.__dict__);exec(compile(s,'guards330','exec'),ns);ns['main']()

if __name__=='__main__':main()
