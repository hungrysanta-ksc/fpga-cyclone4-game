"""Compile current production C against synthetic filesystem/SPI models."""
from pathlib import Path
import argparse,re,subprocess,json
ROOT=Path(__file__).resolve().parents[1]
a=argparse.ArgumentParser();a.add_argument('--source',type=Path,required=True,help='Prepared firmware/src');a.add_argument('--out',type=Path,required=True);a.add_argument('--gcc',default='gcc');args=a.parse_args()
M=args.source.resolve();R=args.out.resolve();R.mkdir(parents=True,exist_ok=False)
f=json.loads((ROOT/'tests/log-policy-fixtures.json').read_text());header=(M/'gbc_log_policy.h').read_text()
def clean(t):return re.sub(r'^#include[^\n]*\n','',t,flags=re.M)
report=f['report'].replace('__PRODUCTION__',clean((M/'gbc_state_report.c').read_text()))
off_report=report[:report.index('int main(void)')]+f['off_report']
pre=f['dump_pre'].replace('memory_reads;','memory_reads,folder_calls;').replace('check_or_create_folder(const char *p){','check_or_create_folder(const char *p){folder_calls++;')
tests=f['dump_tests'].replace('memory_reads=0;gbc_dump_disarm();','memory_reads=folder_calls=0;gbc_dump_disarm();')
crc=(M/'crc32.c').read_text();crc=crc[crc.index('static const uint32_t crc32_table'):]
dump=pre+crc+'\n'+clean((M/'gbc_dump.c').read_text())+'\n'+tests
off_dump=dump[:dump.index('int main(void)')]+f['off_dump']
source=(M/'memory.c').read_text()
profile=source[source.index('static struct {\n  tick_t start'):source.index('/* C26 loading UI:')]
results=[]
for name,enabled,code in [('state-off',0,off_report),('state-on',1,report),('dump-off',0,off_dump),('dump-on',1,dump),('load-off',0,f['profile_pre']+profile+f['profile_main']),('load-on',1,f['profile_pre']+profile+f['profile_main'])]:
 src=R/(name+'.c');exe=R/(name+'.exe');src.write_text('#define GBC_FILE_LOGS '+str(enabled)+'\n'+header+'\n'+code,encoding='utf-8')
 for command,log in [([args.gcc,'-std=c99','-Wall','-Wextra','-Werror',str(src),'-o',str(exe)],name+'-compile.log'),([str(exe)],name+'-run.log')]:
  with(R/log).open('w')as out:subprocess.run(command,stdout=out,stderr=subprocess.STDOUT,check=True,timeout=60)
 results.append(dict(test=name,passed=True,output=(R/(name+'-run.log')).read_text().strip()))
(R/'verification.json').write_text(json.dumps(dict(passed=True,scope='Actual C with modeled filesystem/SPI; no hardware execution',tests=results),indent=2))
print('PASS: all six C44 log ON/OFF suites')

