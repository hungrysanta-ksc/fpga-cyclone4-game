# 실제 NES trace → packet → SNES 재생020

2026-10-05. 후보 **NES-R2-TRACE-REPLAY-020**, NES 구현014 유지.
**보존된 실제 Mapper4 fetch로 만든 패킷이 SNES에서 정상 재생되고, 관측한 소비자 VBlank 기한 안에 전송됐다.**
공급원은 오프라인 진단 ROM이다. 실시간 NES producer/CDC까지 연결된 결과는 아니다.

## 입력과 표현
자체009 Mapper4 진단을014 코어에서 실행한4프레임을 재사용했다.
원본 ROM·fetch·화소를 기존 Mesen/oracle 검증기로 재확인한 후, 물리CHR 타일 주소를 실제fetch에서 모았다.
각8×8cell의 타일이 한 프레임 동안 같고 row/plane이 완전한 경우만 변환한다.
scroll·sprite·중간타일변경을 지원한다고 간주하지 않는다.

입력의 불변 CHR ROM **전체16KiB**를 시작 시 사전 적재했다.
미래trace에 나오는타일만 골라 적재한 것이 아니며, 모든ROM bytes는 로딩 때 알 수 있다.
NES의 plane0 8B+plane1 8B를 SNES의row별2B로 실제변환했다.
이 구조를 큰게임ROM/CHR RAM에 그대로 적용할 수 있다는 근거는 없다.

패킷은16B header+1,920B tilemap+8B CGRAM=**1,944B**다. ROMslot은2,048B.
header에는NTR0/version/frame/256×240/map길이/마지막사용fetch의NES tick을 기록한다.
지도는960개의물리타일번호를 담는다. 소프트웨어 decode가원본240줄과일치한다.
SNES는현재패킷header를확인하고비활성map page에DMA한뒤palette와map을전환한다.
release tick은기록만하며실시간NES/SNES위상동기화를수행하지않는다.

## 실제 SNES 실행
기존격리Mesen에서새로실행했다. 관측Lua는메모리/PPU를바꾸지않는다.

| 실행 | 프레임 | 판정 |
| --- | ---: | --- |
|source rows0..238 관측|4연속|화소차이0,정상commit4|
|source rows1..239 관측|4연속|화소차이0,정상commit4|
|CHR byte변조|4|예상대로source frame1·3에서화소불일치|
|두번째packet 길이변조|4관측|E2거부,두번째packet DMA0,기존화면유지|

정상실행마다source frames1→2→3→4가연속된SNES frames에표시됐다.
초기로딩forced blank와overscan안정화이후정상프레임의추가forced blank/생략은없었다.
오류주입의화면유지는개발오류동작이며정상게임정책이아니다.

프레임당PPU DMA는 **1,928B**(map1,920+palette8).
header검사·DMA·page전환을포함한관측최대는 **18,046SNESmasterclocks**,
다음frame경계까지최소여유는 **11,852clocks**였다.
이수치는ROM에완성된packet이이미있다는소비자조건의결과다.
NES생산완료→packet작성→물리메모리→CDC도착시간은포함하지않으며FIFO깊이를확정하지않는다.
2KiB ROMslot을곧바로FPGA M9K할당또는실제queue크기로채택하지않는다.

## 240줄과색의판정
한번의SNES출력은여전히239줄이다. 서로1줄어긋난두독립실행을합쳐
**245,760개source화소전체**를검증했고,겹치는238줄도같았다.
실제비교횟수489,472는중복을포함하며서로다른source화소수는245,760이다.
240줄동시출력또는crop정책승인이아니다.

원래4개색은명시적인nearest RGB555변환을썼다.
source RGB 000000/64b0ff/fffeff/b53120 →
SNES RGB 000000/42adff/ffffff/b53121.
네색기호는모두구별되며source indexed image로역변환했을때정확히일치한다.
원래RGB의bit-exact출력이나최종NES색상/아날로그보정검증은아니다.

## 검증과실패기록
실제실행4건을raw RGB/phase/DMA/header/프레임연속성으로재검증했다.
packet decoder의magic/version/width/height/길이/타일범위/palette/절단8종거부,
plane교환의화소불일치검출까지9종통과.
초기생성기제목22B가21Bheader영역을늘려ROM을65,537B로만든실패를보존했다.
제목길이를고정하고64KiB ROM크기/첫packet주소검사를추가했다.최종ROM은65,536B.
첫실행의225줄startup경계를관측해최초overscan안정화대기를추가했고,
최종전송은240..261scanline에서만관측됐다.
width음성검사가이미0인low byte를0으로쓴초기검사도보존한뒤실제high byte변조로고쳤다.
코어·upstream·GBC·원래ROM은바꾸지않았다.이번에는Questa/Quartus를실행하지않았다.

## 남은실행
R2는소비자재생의부분검증이다.
다음은더넓은자체Mapper4의bank/scroll/sprite/중간변경부하에서표현가능범위와거부조건을확인한다.
그다음실제producer완료시각·packet전달·queue/CDC·source/consumer속도차를연결해기한을재검증하고018자원예산에대입한다.
큰CHR ROM/동적CHR·display240·DMCtiming·SMB3·fullboard fit/STA·실기는열린과제다.

[검증수치](trace-replay-verification.json), [재현계약](../docs/nes-trace-replay-contract.md).
