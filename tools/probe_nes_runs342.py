import inspect
import probe_nes_decode280 as old
from nes_runs342 import decoder,encode342
s=inspect.getsource(old.build).replace("shutil.copyfile(ROOT/'tools/nes_decode280.c',d/'nes_decode280.c')", "(d/'nes_decode280.c').write_text(decoder(),newline='\\n')")
n=dict(old.__dict__);n['decoder']=decoder;exec(compile(s,'build342','exec'),n)
old.build=n['build'];old.encode280=encode342
if __name__=='__main__':old.main()
