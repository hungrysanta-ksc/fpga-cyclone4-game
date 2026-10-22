# NES274 — 참조 명령을 위한 입력 분할과 실제 처리 비용

**50개 패킷의256B 초과를 명령 분할로 해소했다.** 실제 ARM serializer와 기존 FPGA
queue·parser·receipt, 새65816 실행 trace를 같은 일정에 연결했다.
다만 참조 프로그램은 용량·의미를 독립 대조했을 뿐, 아직 SPI로 보내거나 FPGA에서
실행하지 않는다. 단일 source/receipt/parser 구현이나 회로 절감 완료로 읽으면 안 된다.

## 무엇을 바꿨나

- CGRAM·HDMA literal은 receipt granule과 hash 경계를 보존해 나눈다. 예를 들어
  CGRAM240B는224B+16B가 되고, 같은 원본 descriptor 형식이 각 조각의 SNES
  DMA·WRAM 대상과 기존 FPGA receipt를 결정한다. 별도 ARM receipt 주장을 신뢰하지 않는다.
- dense manifest는235B 이하, RLE manifest는 온전한 token 경계에서 나눈다.
  각 RLE 조각은 기존 mode byte를 가진다. 주소는 압축 길이가 아닌 실제 확장 길이로
  진행한다. 마지막 조각 전 SEAL·표시 승인은 없다.
- 원본 packet 전체를 먼저 검사한 뒤 실제 전송한다. 뒤쪽 malformed RLE를 발견하기
  전에 첫 조각이 전송되는 경우를 막았다. 실패는 기존 sticky error 경로로 종료한다.
- 기존 wire259 버퍼·4credit·sequence/CRC·queue head/ACK 경로를 사용한다.
  새 packet RAM·두 슬롯 공동소유권·FPGA protocol opcode는 추가하지 않았다.

## 실행과 데이터 보존

|항목|기준270|274 분할 후|
|---|---:|---:|
|71프레임 E1 패킷|1181|1231|
|일반65816 명령|522|544|
|일반 명령의 논리 출력(재사용 포함)|128041B|128041B|
|일반 PPU DMA|219회/39648B|223회/39648B|
|bank zero DMA|2회/2200B|2회/2200B|
|map 범위|2069|2069|
|참조 프로그램 포함256B 초과|50|0|

128041B는 각 명령의 출력 대상에서 검증한 논리 결과량이다. bank 재사용으로 생략한
zero fill도 포함하므로 물리적인 WRAM 쓰기 바이트 수와 같지 않다. 실제 PPU DMA와
zero DMA 횟수·바이트 수는 표에서 별도로 센다.

22개의 추가 literal 조각은 cold905/906에만 생긴다. CGRAM4개는PPU DMA를4회
추가하고,HDMA18개는WRAM 복사·ACK 명령을추가한다. 22개를모두DMA로세지않는다. manifest 추가28개는 dense2개,
RLE26개이며 SNES 일반 명령을 추가하지 않는다. 전체 E1 wire는976B 증가한다
(추가 header/CRC50×19B + RLE mode26B). source83240B·map data13406B,
map/tile DMA26350B·metadata8570B/frame·receipt754B/frame·CRC64B/frame 검사는
기존 경로에서 유지한다. ARM 출력과 실제 SPI E1 bytes도71프레임 모두 일치시킨다.

실제65816 ROM은269의653B STOP-aware 코드와 byte-identical하다. 새 입력으로
다시 실행해 WRAM/PPU 쓰기·bank 재사용·ordered ACK를 검사했다. 총 CPU 비용은
77346 master clock 증가했다. cold의추가명령22회와그중CGRAM DMA4회뿐아니라 실제 trace의
refresh/alignment 차이를 포함한다. forced blank 검증이며 active VBlank 상한이 아니다.

## 처리 시간과 회로

|조건|270|274|차이|
|---|---:|---:|---:|
|cold905|61.970302ms|63.615873ms|+1.645571ms|
|cold906|50.001355ms|51.692289ms|+1.690934ms|
|warm 최대/frame954|18.065374ms|18.222145ms|+0.156771ms|
|16.666667ms 초과 warm 수|5|6|—|
|제한 ROM907|20.283029ms|18.246508ms|-2.036521ms|

현재 진단에서 warm 최대는 목표보다 **1.555478ms**,
제한 ROM907은 **1.579842ms** 초과한다.
분할만으로 이전 부족분을 줄이지 못했다. 실제 전체 경로의 남은 시간 상한은 미확정이다.

954의polling은기존과같은E0 4회/E2 110회였다. 추가20 wire B(약0.060952ms),
E1 transaction1회(0.008ms),ARM+IRQ event명령7377개(약0.087821ms)가
합쳐져약0.156774ms를설명한다. 소스·클럭위상 차이를포함한실제차이는비용표에기록했다.
이한프레임의분해를다른프레임의overlap·polling 고정가정으로일반화하지않는다.

제한ROM907의E2 polling은286→237회(-49),wire는441B 감소했다.
하지만앞두cold frame이합계2.026794ms 늦어져907의대기가짧아진것이다.
3프레임전체종료시각은약9.7µs만앞당겨졌다. 907의2.036521ms 감소를
독립적인처리시간절감으로세지않으며,임의ROM위상·실기부하의상한으로도쓰지않는다.

모든 시간은 실제 ARM 명령을CPI1/84MHz로 진행시키고 기존 source RTL,
실제 refill/IRQ 본문·tile ROM arbiter와 실제 일반65816 bus trace를 연결한 **직렬 진단**이다.
full RUN/NVIC·실제 코어의 ROM 요구·전체65816·active VBlank·실기 deadline을
검증한 값은 아니다. map/tile/final display ACK는 모델이며 일반65816 trace와 구분한다.
제한 ROM의3프레임도 WCET 증명이 아니다.

실제 full 실험 ARM link는3164→4206text(+1042B),604→612BSS(+8B),
관측 stack은248B다. standalone 분할 serializer는3574text/320BSS/
관측stack200B다. 별도273 producer의2032text/64BSS/stack136을 이 link에 합친
펌웨어가 아니며, 두 stack 수치를 더하거나 최대값만 취해 full RUN 여유를 주장하지 않는다.

합성 대상 RTL은270과 파일별 hash가 같다. 새 MAP은 실행하지 않았다.
whole Lite MAP 기준17680comb, 한도15408 대비 **2272개 부족**이 그대로다.
교체 영역6486→4214 이하와 배치 여유가 필요하다. 이번 ARM 분할을 logic 절감으로
환산하지 않는다. 기존 source/receipt2448과 output own2206 제어는 남아 있다.

## 참조 프로그램을 실제로 넣기 전의 비용

분할 후 참조 프로그램과2B prefix를 넣는 후보는 모든 slot이256B 이하다.
warm 추가 wire는87–270B이며,954는226B다. 이미 실제 일정에 반영된 분할 wire20B를
포함하면954의 기존270 대비 총 추가는246B다. 이전273 fallback243B보다3B 많다.
따라서 wire 자체의 개선이 아니라 두 슬롯의 공동소유권을 피하는 구조적 선택이다.

954에서 참조 producer는추가19710 ARM 명령이고,
추가 wire와 합친 직렬 민감도는0.923405ms다.
실제 분할 진단에 단순 가산하면19.145550ms,
16.666667ms 대비2.478883ms 초과다.
이 산술값을 실제 참조 명령 실행시간으로 보고하지 않는다.

이는273의954 inline/fallback 추정19.046065ms보다약0.099485ms 크다.
두슬롯 공동소유권을피하는대가도공짜가아니며,이차이를후속RTL 제어절감으로
상쇄할수있는지는아직검증하지않았다.

이 값은 실제 분할 일정에 추가 producer 명령/CPI1과 wire만 더한 민감도다.
새 serializer·CRC 구현, 제거할 FPGA 해석과 overlap은 아직 반영되지 않았다.
inline length/kind와 SNES 원본 view, checked descriptor·참조 bounds의 실제 RTL
연결을 생략하고 완성된 전송 경로라고 주장하지 않는다.

## 검증과 다음 게이트

선택 증거는arm01/armguards01/cpu01/test01/window01/guards01/program01/analysis01이다.
기존24개 ARM 오류와credit counter wrap(65530→54,60packets)을 재검사했고,
새16개 split bounds 오류 및 늦은 RLE 오류의 원자적 사전검사1개가 통과했다.
RTL은새split 경계6개와기존3개 STOP/잘못된 display read/stale ACK guard를검사했다.
첫224B CGRAM·235B manifest 후 STOP,다음조각의미정렬·manifest gap·sequence replay,
CGRAM 조각을OAM으로바꾼missing-receipt 반례에서fault·lease해제·최종ACK차단·RAM
freeze를확인했다. SPI CRC를재계산하므로단순transport오류검사로대신하지않았다.
이 RTL 오류 검사는모델SNES consumer이며새65816/FPGA STOP 동시실행은아니다.

분할은 슬롯 문제를 해결하는 입력 정책으로 남긴다. 자체적인 시간·면적 최적화로
채택하지 않는다. 다음에는 이 입력을 사용해 **source/query·header·typed-map·receipt의
실제 읽기·실행·복귀 제어를 함께 교체**해야 한다. 기존 core는 이미 source/receipt
FSM을 공유하므로 이를 새 절감으로 세지 않는다. 원본 DMA 대상과 참조 명령을
같은 검증된 descriptor에 묶고, 소비 전 receipt·STOP 후 RAM 쓰기·이른 최종 ACK를
차단해야 한다. 별도 decoder만 추가한 상태에서 whole 회로 절감을 주장하지 않는다.

그 교체가 동작하면 실제 참조 wire/CRC/credit·refill/IRQ·ROM 경쟁·SNES polling을
같은 일정으로 다시 측정하고 동일 whole Lite MAP을 비교한다. 시간·회로 부족과
배치 여유를 함께 통과하기 전 FIT/STA·full RUN·실기60fps 게이트로 넘어가지 않는다.
production227·GBC164·saveSRAM은 유지하며 P2는 미선택이다.
