# NES273 — ARM 실행 명령 표현과 단일 실행 제어의 남은 비용

PR130의272 실험 다음 단계다. **ARM producer와 독립 decoder를 구현·실행했다.**
단일 source/receipt/parser RTL이나 새 SPI 경로를 구현한 단계는 아니다.
270의 실제71프레임 E1 전송을 입력으로 사용하며 production227·GBC164·saveSRAM은 유지한다.

## 결과와 선택

기존24bit 의미 이벤트를 ARM에서 그대로 보내는 방식은 추가 전송량이 크다.
16바이트 단위로 값을 묶어도 기존 payload의 값을 다시 전송한다.
반면 **기존 queue payload 위치를 참조하는 명령**은 이 재전송을 없애고
producer의 명령 수를 줄인다. 다음 통합 실험에는 이 표현을 남긴다.
그러나 별도 명령 패킷이나 inline 표현 자체가 시간·회로 목표를 통과한 것은 아니다.

|warm69 / frame954|event24 별도|값 run16 별도|payload 참조 별도|payload 참조 inline 우선|
|---|---:|---:|---:|---:|
|warm 추가 SPI bytes 범위|1295–1554|331–582|239–479|87–287|
|954 추가 bytes|1454|434|414|243|
|954 producer ARM 명령|60904|61500|19498|19498|
|954 전송·setup·CPI1 추가 민감도|5.252286ms|2.118810ms|1.573833ms|0.980690ms|

마지막 행은 기존 경로에서 제거되는 해석 시간을 빼거나 overlap을 다시 실행한 값이
아니다. 새 SPI serializer·CRC·credit/refill/IRQ 비용도 실행하지 않았다.
`ARM 명령/84MHz + 추가 bytes×8/2.625MHz + 추가 transaction×8µs`의
**직렬 추가 민감도**다. 실제 frame 시간이나 상한으로 읽으면 안 된다.

270의954 직렬 진단18.065374ms에 마지막 후보를 단순 가산하면19.046065ms,
16.666667ms 대비2.379398ms 초과다. 이는 제거 비용과 새 일정의 효과를 검증해야
한다는 비교 지점이며, 실제로 새 경로가 이 시간에 실행됐다는 주장이 아니다.
제한 ROM·polling·tile 경쟁은 새 producer와 함께 재실행하지 않았다.

## 실행한 ARM 코드와 의미 대조

`nes_primitive273.c`는 한 packet을 사전검사한 뒤 다시 읽어 명령을 생산한다.
첫 검사가 실패하면 출력0바이트이고 문맥을 되돌린다. 두 번 읽는 비용,
16바이트 값 run 버퍼와 문맥 snapshot을 명령 수·BSS·stack에 포함했다.
이 pure producer의 재시도 가능성을 실제 보드의 STOP/restart 허가로 해석하지 않는다.

- 71프레임 ×3표현 =213회, 원본1181packets, 의미 동작35152개를 대조했다.
- Python oracle은 원래 명령을 펼쳐 실제 쓰기 위치와 값에서 granule·hash·manifest
  동작을 계산한다. C의 continuation이나 출력 명령을 기대값 생성에 사용하지 않는다.
- 각 frame의 display24B·manifest422B를 확인한다. map descriptor와 원래 SNES
  명령은 유지하며, map receipt를 ARM producer가 선행 생성하지 않는다.
- 실제 ARM에서20종 오류×3=60회 검사, decoder17종 오류, 별도 codec7종×3=21회
  검사가 통과했다. 반복2/4바이트·255바이트 조각 경계·홀수 tail phase·RLE
  최대256제로·잘린 literal·257바이트 확장을 포함한다.
- 최종 standalone ELF는2032text/64BSS/관측stack136B다. 기존270의604BSS/stack200과
  합쳐 full firmware 여유를 증명한 값이 아니다. 새 emitter는 측정 callback이며
  실제 SPI writer·CRC를 대신 실행하지 않는다.

선택 실행은 `arm05`, 분석은 `analysis03`이다. `arm01`은2표현,
`arm02`는3표현의 앞선PASS, `arm04`는binding 반례 추가 전PASS로 보존한다.
`arm03`은71프레임 처리 후 합성 vector의bytearray를 Unicorn에 넘기는 자료형 오류,
`analysis01`은MAP entity 이름 오기로 중단됐다. C/RTL 오류나 license 문제로
기록하지 않는다. 최종 실행은bytes 변환과 정확한 entity 이름으로 통과했다.
새 Quartus·Questa 실행은 없으며 기존 Lite MAP을 비용 기준으로만 사용한다.

## 참조 명령과 패킷 용량

문법은 측정용 후보이며 생산 프로토콜 opcode를 예약하지 않는다.

|명령 byte|뒤따르는 필드|의미|
|---|---|---|
|1|first LE16, count8|1–16개 receipt granule 제안|
|3/5/7|count8, 값1–16개|값 run의 manifest/hash/display|
|4|kind/index8|hash 시작|
|6|1|finish 요청|
|9|count8, offset8, pattern8|보유 packet에서 hash byte 읽기|
|10/11|count8, offset8|보유 packet의 manifest/display byte 읽기|
|12|count8|manifest zero run|

참조형은1/4/6/9/10/11/12를 쓴다. pattern의 하위 nibble은0(연속)/2/4,
상위 nibble은반복 phase다. 255바이트 경계에서 phase를 보존한다.
offset은원래16B header 뒤를 가리킨다. decoder는원래packet 범위를넘는 참조를
거부한다. program 최대212B이고 보드 phase RAM을 새 buffer로 사용하지 않았다.

별도 프로그램의 비용은16B identity envelope +2B target sequence +프로그램,
E1 command/CRC16 3B를 세며 payload는최대238B다.
값 표현은기존internal15/10/11/3을 대체하고 SNES-visible 명령은보존한다.
참조형은원본internal packet까지보존해, 검사값도이미수신된payload에서읽는다.

inline 계산은 `legacy length LE16 + legacy packet + program`이256B 이하면
같은slot에 넣고 추가 transaction을0으로 센다. transport 종류 구분과CRC admission,
SNES가보는원본packet offset/length view를새경로에서구현해야한다.
**71프레임 중50개 packet은이형식으로256B를넘는다.** 이들은별도program
전송으로계산했으며, 누락하거나슬롯을몰래늘리지않았다. 954와970도각각1개가넘는다.

이fallback에는원본head와program slot의공동소유권,read-address 선택,
원본SNES ACK후참조완료까지retire를늦추는제어가필요하다.
명령split로해결한다면SNES setup/DMA 수와token/receipt 의미가바뀔수있다.
이번계산은이제어를구현한것이아니다. 170B의phaseRAM 빈공간에256B packet을
복사하거나새port가공짜라고가정하지않는다.

## 삭제할 수 없는 검증과 단일 실행 제어

실제tile packet에대해 **문법상유효하지만다른granule을주장하는RANGE**를만들었다.
generic decoder는이를해석하지만원래DMA대상에서계산한oracle과불일치한다.
따라서identity·CRC·참조bounds만검사하고ARM의receipt 명령을곧바로승인할수없다.
새구조는한검사된descriptor가DMA대상과receipt 양쪽을결정하게하거나,
원래명령과program의의미대조를유지해야한다. 실제소비와최종표시ACK도별도다.

단일실행제어후보의경계는다음과같다. 이표는구현계획이며합성절감량이아니다.

|구간|공유할 실행 상태|유지할 조건|
|---|---|---|
|source/query→input commit|source cursor·byte fetch·CRC 진행|query 선행읽기,accepted source ACK와display lease 전환|
|header/descriptor admission|queue byte cursor·length·identity 비교|원본packet과program의경계,sequence/bank/generation/token|
|SNES ordinary/tile/map 소비|같은검사된descriptor에서DMA와receipt 파생|head/aperture 소유권,실제소비전receipt 금지|
|hash/manifest 참조|하나의read/execute/return 경로|H_BYTES/H_SCROLL가byte를기다릴때V_ACTIVE-ready를기다리지않음|
|receipt RAM·최종 표시|CRC/receipt의현재RAM상태를이어서실행|RAM port충돌,STOP후쓰기금지,12B display read후최종ACK|

기존core는이미source와receipt를42상태의한FSM으로실행한다. 이것을새절감으로
다시세지않는다. 272의별도parser 상태를단순히이어붙이는것도host header/map
cursor·continuation·CDC·RAM접근을제거하지못한다. 특히parser가다음byte를
요청하는동안core의hash 상태가유지되므로,단일FSM에는실제중단·재개규칙이필요하다.

270 whole Lite MAP은17680comb,15408대비2272초과다. 중복없는교체영역6486을
4214이하로줄여야하고,다른1832를유지하면core+host4654→2382이하가필요하다.
**기존core2448을그대로두는ARM offload는출력제어를0으로가정해도66개초과한다.**
이번producer의코드크기나상태수를FPGA comb 절감량으로환산하지않는다.

전체4398B source와RAW를매frame literal로옮겨core를단순화하는후보도비교했다.
가장작은inline우선참조형을포함해warm69모두source literal payload+E1 bytes
전송만으로16.666667ms를넘는다. 이하한은source framing·poll·CPU를제외한것이다.
따라서같은SPI와같은출력명령에서full literal 전환은제외한다.
mask-only source와참조형의wire floor는이한도로배제되지않지만,
그사실만으로전체시간이나회로PASS를주장하지않는다.

## 다음 게이트

1. payload참조와**DMA/receipt 공통descriptor**를단일queue 소유권경로로연결한다.
   50개overflow packet의보유/continuation 또는명령split을실제비용으로선택한다.
2. source/query·header·typed-map·receipt의read/execute/return 제어를같이대체한다.
   270의분리된실행문맥이남은채새decoder만더하는후보는채택하지않는다.
3. 새ARM serializer/refill/IRQ·ROM 경쟁·SNES polling을같은일정으로실행하고,
   동일한전체보드범위의Lite MAP에서2272comb와배치여유를확인한다.
4. 범위·소유권·STOP·재사용·CRC/receipt·최종ACK 후에만FIT/STA와전체RUN으로간다.

P2는미선택이다. full RUN/NVIC·active VBlank·whole CDC/IO/STA·실기60fps는미완료다.
