# SPDX-License-Identifier: MIT
"""Compare a returned HW083nnn.TXT with all3072 expected storage-test bytes."""
from pathlib import Path
import argparse,hashlib,json
def expected():
 b=bytearray(10 if i%64==63 else 65+i%26 for i in range(3072))
 h=b'SDREPORT083-NATIVE077\nSTORAGE PAYLOAD; FILE ALONE DOES NOT PROVE SUCCESS\n'
 b[:len(h)]=h;return bytes(b)
def main():
 p=argparse.ArgumentParser();p.add_argument('report',type=Path);a=p.parse_args()
 actual=a.report.read_bytes();want=expected()
 mismatch=next((i for i,(x,y) in enumerate(zip(actual,want)) if x!=y),None)
 ok=actual==want
 print(json.dumps(dict(bytes=len(actual),expected_bytes=len(want),exact_payload=ok,
                      first_mismatch=mismatch,sha256=hashlib.sha256(actual).hexdigest(),
                      proves_terminal_or_physical_recovery=False)))
 raise SystemExit(0 if ok else 1)
if __name__=='__main__':main()
