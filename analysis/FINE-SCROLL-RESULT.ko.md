# Fine-X 가로 스크롤 packet/SNES 재생022

2026-10-05. 후보 **NES-R2-FINE-SCROLL-022**, NES 구현014 유지.
**021에서 불일치하던 가로1픽셀 스크롤을 packet과 실제 SNES 재생으로 구현·검증했다.**
관측 범위는fine-X0/1,고정BG/세로scroll0/불변CHR16KiB다. 일반scroll전체지원은아니다.

## 구현
기존32열만으로는가로이동후오른쪽끝에필요한33번째타일열이없었다.
021 실제 NES fetch에서각scanline의dot245/247까지포함해33열×240줄×2planes=15,840reads를사용했다.
8×8cell990개의물리tile번호를얻었으며원본240줄소프트웨어복원이참조와일치했다.
원본ROM·trace·NES코어와020/021도구는바꾸지않았다.

새NFX1 packet은20B header+32열map1,920B+오른쪽column60B+palette8B=**2,008B**다.
2,048B ROMslot안에유지된다. SNES의64×32map에앞32열은일반DMA,
다음map page의첫column은VMAIN81의32word간격DMA로쓴다.
완성후packet의fine-X값을BG1HOFS에쓰고map page를전환한다.
두map세트합계8KiB의VRAM할당과16KiB CHR atlas는FPGA M9K예산이아니다.
실제queue깊이는이2KiB ROMslot크기로확정하지않는다.

## 실제 SNES 결과
격리 Mesen SNES를6회새로실행했다. Lua는화면·DMA·VMAIN·HOFS·page/phase를읽기만한다.

| 실행 | 결과 |
| --- | --- |
|fine-X1,source rows0..238|4연속frame화소차이0|
|fine-X1,source rows1..239|4연속frame화소차이0|
|fine-X0 회귀|4연속frame화소차이0|
|오른쪽column tile변조|네frame모두x255에만화소불일치|
|HOFS commit을0으로변조|네frame모두화소불일치|
|packet2 map길이변조|E2거부,해당packet DMA/page/scroll변경0|

정상3실행은총734,208회표시화소비교를통과했다.
fine-X1의두viewport를합치면원본4frames의**245,760개화소/240줄전체**가일치한다.
동시에출력한높이는239줄이며240줄동시출력/crop정책승인은아니다.

## 소비자 전송 예산
정상frame PPU DMA는1,920+60+8=**1,988B**,020보다60B증가했다.
header검사·DMA·scroll/page commit의최대는 **19,618SNESmasterclocks**,
관측최소VBlank여유는 **10,282clocks**였다.
020최대18,046대비1,572clocks추가이며,증가분은60B DMA뿐아니라설정/검사/commit비용을포함한다.
잘못된HOFS를의도적으로쓰는fault code는16clocks추가되어최대19,634였다.정상측정과섞지않았다.
초기loading/overscan안정화외정상frame의forced blank/반복/생략은없었다.

불변CHR전체16KiB를startup때사전적재하고완성packet을ROM에서공급했다.
header의NES release tick은기록만한다.실시간producer/메모리/CDC도착기한은포함하지않는다.
RGB555색변환은020과같고4색기호를보존한다.최종색정책/아날로그색상검증은아니다.

## 검증과 다음 단계
raw RGB와DMA/주소/증분/scroll/page/프레임연속성을재검증했다.
packet header·tile·palette·절단·오른쪽열손상/plane누락·sprite/세로/coarse/가변CHR거부16종검사통과.
새코드는fine-X필드0..7을표현하지만실제NES/SNES참조는0/1에서만확인했다.
전체BG cadence/원본바이트검증은021입력감사에의존하며새encoder만독립적인범용입력검사라고부르지않는다.

다음구현은021의실제sprite1개를BG와함께보존하는표현과SNES재생이다.
그후cell내CHR bank변경patch·큰CHR residency비용을판단하고실시간queue/CDC와018자원에연결한다.
이번에는새SNES실행6건만수행했고NES RTL/Questa/Quartus를실행하지않았다.
원본/기존코어/GBC/upstream보존. DMC/SMB3/전체board fit·STA/실기·HDL반입hold는미완료다.

[검증 수치](fine-scroll-verification.json), [재현 계약](../docs/nes-fine-scroll-contract.md).
