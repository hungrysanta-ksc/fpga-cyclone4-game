# SPDX-License-Identifier: MIT
"""Receipt endpoint admission, CRC coverage, STOP and underflow guards."""
import guard_nes_range287 as prior
from nes_delta231 import once


def main():
    run=prior.old.main
    def endpoint():
        s=once(prior.old.TB,'first=f;count=n;map=m;', 'first=f;count=f+n;map=m;')
        s=once(s,'  $display("PASS RANGE283', '''  clear();desc=1;reject(128,0,0);
  clear();desc=1;reject(128,-1,0);
  clear();desc=1;reject(4095,2,0);
  $display("PASS RANGE283''')
        prior.old.TB=s;run()
    prior.old.main=endpoint;prior.main()


if __name__=='__main__':main()
