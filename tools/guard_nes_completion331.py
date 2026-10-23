# SPDX-License-Identifier: MIT
import inspect
import guard_nes_arm328 as base


def main():
    s=inspect.getsource(base.main).replace('probe_nes_joint328.py','probe_nes_completion331.py')
    ns=dict(base.__dict__);exec(compile(s,'guards331','exec'),ns);ns['main']()


if __name__=='__main__':main()
