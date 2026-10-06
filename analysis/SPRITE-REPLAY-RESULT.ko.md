# 실제 NES sprite → native SNES OBJ 재생023

2026-10-05. 후보 **NES-R2-SPRITE-REPLAY-023**, NES 구현014 유지.
**021에서누락되던8×8sprite한개를배경과함께실제SNES OBJ로재생했다.**
배경앞/palette0/flip없음/잘림없음/고정OAM조건이다. 일반NES sprite처리완료는아니다.

## 원본 관측과 변환
021 sprite표본의CPU OAM writes를재생해256B OAM전체와entry0=[79,1,0,40]을확인했다.
나머지entry는숨김상태이며capture중OAM변경을허용하지않는다.
palette초기writes32B가고정4색반복임을확인했다.
원본sprite실제영역은x40..47/y80..87이다.

각frame에서line79..86의sprite slot0 CHR reads16건이physicaltile257/offset4112..4127와일치했다.
Mesen콜백은각행두plane을같은dot261에기록한다.이를실제전기적버스위상검증으로부르지않는다.
NES16B를SNES4bpp32B로변환했다.하위2planes는row별interleave,상위2planes는0이며color0은투명하다.
SNES OBJtile0,OBSEL2,앞쪽priority3,palette0으로배경과합성했다.
sourceOAMy79를SNES표시y80으로변환하고별도하단viewport에서는y79로보정했다.

## 패킷과 실제 전송
NSP1은022의20Bheader+BGmap/edge/palette에OBJ CHR32B+OBJpalette8B+OAM4B를붙인다.
총 **2,052B**이며기존2KiB보다4B크므로진단ROMstride를4KiB로늘렸다.
정상frame PPU DMA는 **2,032B**다.4KiB전체를전송하지않는다.
4KiB ROMslot이실제FPGA FIFO/M9K크기를확정하는것도아니다.
BG CHR전체16KiBstartup에숨김OAM544B초기화를더해startup DMA16,928B.
map/CHR/OAM/OBJpalette를업데이트한뒤scroll/map을commit한다.

| 실제SNES실행 | 결과 |
| --- | --- |
|sprite,source rows0..238|4연속frame화소차이0|
|sprite,source rows1..239|4연속frame화소차이0|
|fine-X1/sprite없음회귀|4연속frame화소차이0|
|OAMy를240으로변조|sprite영역의화소불일치검출|
|OBJ CHR를0으로변조|sprite영역의화소불일치검출|
|packet2의sprite count를2로변조|E2거부,해당packet DMA/scroll/page변경0|

정상12개표시frame의734,208화소비교통과.
sprite두viewport의union은원본4frames/240줄의245,760화소전체일치.
동시출력은239줄이며제품crop/240줄정책승인은아니다.
가로scroll+보이는sprite의동시NES참조표본은이번에실행하지않았다.

## 시간·검증
정상header검사·6DMA·commit 최대 **21,470SNESmasterclocks**,
관측최소VBlank여유 **8,444clocks**.
022보다payload44B/최대시간1,852clocks추가.단순바이트수외설정비용도포함한다.
원본CPU/OAM/CHR와생성packet을재대조하고actualRGB/VRAM주소/VMAIN/CGRAM/OAM주소/TM/OBSEL/연속frame을감사했다.
packet/count/CHR상위plane/palette/tile/priority/잘림/절단/OBJ화소검출13종통과.
초기오류주입은투명palette0에0을쓰는no-op을mutation guard가잡았다.
또단일CHR bit변조가우연히같은배경색을드러내화면차이가없어,
실제실행에서도검출한OBJ전체소거로검사를고쳤다.초기두verifier와설명은보존했다.
decoder/실제capture를약화하거나바꾼것은아니다.

공급원은완성packetROM/불변BG CHR전체사전적재다.실시간producer/메모리/CDC기한은미검증.
RGB555변환과4색기호보존은이전과같으며최종색보정이아니다.
이번은새SNES Mesen6실행이며NES RTL/Questa/Quartus재실행없음.
원본·020~022도구·core014·GBC·upstream보존.

## 다음
021의line63 CHR bank변경으로8×8cell안에서pattern이바뀌는경우를patch표현으로구현하고전송예산을확인한다.
그후큰CHR residency와실시간queue/CDC/pacing,018자원비용을연결한다.
sprite전체종류검사만계속늘리며이관문을미루지않는다.
우선순위혼합·sprite간겹침/overflow·8×16/flip·동적OAM·SMB3·전체board/실기·DMC·HDLhold는미완료다.

[검증 수치](sprite-replay-verification.json), [재현 계약](../docs/nes-sprite-replay-contract.md).
