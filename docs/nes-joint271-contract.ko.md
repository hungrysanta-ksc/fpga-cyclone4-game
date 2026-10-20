# NES271 — tile 대기와 E1 credit 응답의 비용 및 parser 교체 경계

PR130의 실험 후속이다. production227, GBC164, saveSRAM은 유지한다.
이번에는 polling 두 후보를 실제 ARM·SPI·ROM 일정에서 비교했다.
source·receipt·출력 parser의 통합 RTL을 구현한 단계는 아니다.

## 측정 결과

|warm907 직렬 진단|269|270|A: tile 대기|B: A+E1 snapshot|
|---|---:|---:|---:|---:|
|일반 ROM|11.843858ms|11.543680ms|11.543816ms|11.583997ms|
|제한 ROM|19.291450ms|20.283029ms|19.913352ms|20.116850ms|
|제한 ROM 예산 초과|2.624784ms|3.616363ms|3.246685ms|3.450183ms|
|whole comb|17692|17680|17680 (동일 RTL 재사용)|17694|

A는 제한 ROM의 조회290→136회를 줄였지만 CPU pause를 포함해269보다0.621902ms 느리다. B는 같은136회/2173SPI B로 별도 조회를 더 줄이지 못했다. A 대비 ARM 명령17,095개가 늘었고, 여기에는 pause1회 증가(10,245명령)도 포함된다. 모든 CPU·SPI·ROM 비용은 이미 실행 일정에 들어 있다.

A는3244text/604bss/관측stack208B, B는3300text/604bss/stack200B다. 270 대비text+80/+136B, static0이며 full firmware SRAM·link 여유는 검증하지 않았다. B whole MAP은22501LE/17694comb/8892FF/303712RAM bits,270 대비+14comb/0FF/0RAM이다. 조합 논리 한도15408보다2286개 초과한다.

A: 기존24 ARM 오류+4대기 검사와wrap, B: 이에6 E1 오류를 더한34검사와wrap, 실제SPI31검사가 통과했다. 기능 PASS를 성능·회로 게이트 PASS로 바꾸지 않는다.

## 후보 A: tile 준비 대기에만 간격 추가

queue가 비어 있고 tile-ready bit를 기다릴 때, 같은 phase 응답이 반복되면
128→256→512→1024→2048회로 증가하는 ARM 루프를 실행한다.
phase가 바뀌면 간격을 초기화한다. credit 대기, queue drain, map-ready 대기는
기존 짧은 조회를 유지한다. phase 재시도 상한 1024회도 유지한다.

`pause271`은 `5×iterations+5`개의 실제 ARM 명령을 실행한다.
최대 10,245명령은 84MHz·CPI1 가정에서 약121.964µs다.
이 시간을 RTL 일정에 반영했으며 무료 idle, WFI, 타이머 IRQ로 처리하지 않았다.
실제 Cortex-M4 cycle, IRQ 진입·복귀·선점 또는 full RUN의 상한은 아니다.
1024회 제한 역시 하드웨어 deadline을 뜻하지 않는다.

준비 응답이 오면 진행하고, phase 변화 때 backoff가 초기화되며,
fault 이후 추가 SPI가 멈추는 것을 실제 ELF로 검사했다.
계속 준비되지 않는 경우 1023회의 pause 뒤 오류17로 종료한다.
이 실패 뒤에도 추가 전송·재시도는 없다.

## 후보 B: E1 전송 중 pre-admission 상태 반환

후보 A에 E1 응답을 추가했다. 기존 공통 SPI snapshot과 CRC8을 재사용해
E1의 MISO 앞9B에 E2와 같은 F9 상태를 보낸다. MOSI packet 형식과 길이는 같다.
snapshot은 E1 명령 byte 수신 시 고정되므로 **현재 packet의 admission 이전 상태**다.

ARM은 전송 전 `sent`와 snapshot의 accepted를 비교하고, retired 증가와4credit,
marker·CRC·fault를 확인한 뒤 현재 packet의 sent/sequence를 증가시킨다.
이 응답은 현재 packet CRC가 맞았다는 증명도, 현재 packet의 ACK도 아니다.
실제로 잘못된 packet CRC에도 유효한 이전 snapshot이 반환되는 경우를 검사했다.

응답 오류가 나면 현재 packet은 이미 수신됐을 수도 있다. 따라서 ARM은 오류를
고정하고 재전송하지 않는다. 재시작은 기존 STOP·bank 무효화와 양쪽 namespace를
일치시키는 절차가 필요하다. `reset259()`만 호출해 재전송해도 된다는 뜻이 아니다.

E1 snapshot의 accepted/retired, 전송 중 불변성, counter wrap과 packet CRC 실패를
실제 SPI RTL에서 검사했다. ARM은 잘못된 E1 marker·CRC·counter·full·fault 응답에서
sent를 증가시키지 않고 추가 SPI 없이 중단한다.

## 검증 범위와 판정

두 후보 각각 normal/restricted ROM의905..907을 실행했다. 총12프레임 실행이며
새71프레임이나 heavy954 검증으로 확대하지 않는다. source 입력, packet bytes,
map·receipt·metadata, 실제269 일반65816 명령 trace와4credit은 비교 대상과 일치한다.
map/tile/final display의 전체65816 실행은 여전히 모델이다.

후보 A의 RTL은270과 동일하므로270의 전체 MAP을 재사용한다.
후보 B는 공통 SPI의 E1 snapshot 선택만 바꾸고 동일 전체 보드를 Lite MAP으로 한 번 합성했다.
FF 또는 RAM 변화가 없더라도 조합 논리가 추가됐으며 새 FIT/STA는 실행하지 않았다.
기존38개 semantic/STOP 검사는270의 증거로 유지하고 이번 새 실행으로 세지 않는다.
새 검사는 대기와 E1 계약에 집중한 ARM·SPI 검사다.

두 후보 모두 제한 ROM warm907에서269보다 느리고 전체 회로 여유를 확보하지 못했다.
따라서 단독 채택하지 않는다. 71프레임 확대나 추가 seed/FIT·대기 상수 탐색으로
이 부적합 판정을 덮지 않는다. CPU 반복 대기를 이벤트 대기로 바꾸는 경우에는
실제 MCU timer/IRQ/full RUN을 연결한 별도 비용 증명이 필요하다.

## 다음 교체의 RAM·clock 경계

다음 실험의 회로 기준은 E1 추가 비용을 제외한270 common SPI다.
core2448 + output parser 자체2206 =4654comb이고, 나머지1832개가 유지된다면
새 core/parser 합계2382 이하가 필요하다. 전체 교체 영역6486→4214 이하와
배치·mapper 여유가 필요한 장부이며, 새 회로 절감이 증명된 것은 아니다.

현재1024B phase RAM의 출력 단계 배치는 다음과 같다.

|영역|주소|bytes|
|---|---|---:|
|persistent validity|0..331|332|
|retained CRC|332..395|64|
|receipt|396..561|166|
|map coverage|562..817|256|
|H2 문맥|832..863|32|
|display offset|864..867|4|
|미사용 간격|818..831, 868..1023|170|

전체256B packet 복사는86B가 부족하다. 입력 단계의 source scratch는512..1023을
사용하므로 이170B도 입력·출력 동시에 쓸 수 있는 별도 RAM이 아니다.
예를 들어868..895의28B 문맥과896..1023의128B 조각 버퍼는 출력 단계의 산술상 후보다.
이는 새 RAM 배치·중재·FSM 합성 결과가 아니며, H2·CRC·receipt를 덮어쓰면 안 된다.
RAM의 두 port도 기존 CRC/receipt 갱신에 사용되므로 버퍼 접근 시간을 따로 지불해야 한다.

queue RAM은 host-clock 쓰기 port와 읽기 port를 사용한다.
읽기 주소는 NORMAL에서 SNES 주소, 그 외에는 parser 주소다.
읽기 port를 NES clock으로 단순 이동하면 SNES 응답 경로도 바뀐다.
clock mux, read-during-write, 새 왕복 CDC 또는 RAM 복제를 무료로 계산하지 않는다.

다음에 먼저 구현할 후보는 **host RAM 읽기와 SNES bus 제어를 유지하고,
기존24비트 mailbox를 통해 제한된 단위로 바이트를 넘겨 NES core에서 해석하는 경계**다.
검증 조건은 다음과 같다.

- NES header 검사 전에는 일반 SNES packet 창이나 typed staging 완료를 공개하지 않는다.
- 일반 명령은 실제 SNES read/ordered ACK 이후 payload 검증·receipt를 확정한다.
- map descriptor 승인, staging, DMA consume, receipt와 마지막 head 반환을 구분한다.
  staging 수락만으로 queue credit를 돌려주지 않는다.
- host의 읽기·staging cursor와 NES 해석 cursor가 모두 필요하면 둘 다 회로에 포함한다.
  기존24비트 전송과8비트 응답을 그대로 삭제했다고 계산하지 않는다.
- source/output phase의 주소·CRC·문맥 제어를 실제로 공유하고, 이전 host parser와
  불필요해진 semantic event 제어를 삭제한 동일 전체 보드로 비용을 비교한다.
- plan의 조기 copy credit와 tile 완료까지 유지하는 문맥, STOP·stale token,
  최종 display ACK를 유지한다. 새 mailbox service 비용은 실제 일정에 반영한다.

이 경계의 추가 RAM0은 설계 제약일 뿐 합성 결과가 아니다.
새 core/parser 비용과 처리 시간은 아직 null이다. 이 넓은 교체에서도 예산에 못 들어오면
전송 표현과 ARM/FPGA/SNES 역할 분담을 다시 비교한다.

## 재현과 증거

후보 A는 `nes_output271_phase.c`와 `probe_nes_phase271.py`,
후보 B는 `nes_output271.c`, `nes_spi271.sv`, `probe_nes_refill271.py`로 재현한다.
실제 A 실행 때 사용한 동일 C·RTL·worker와 당시 실행기 원본도 별도로 보존했다.
`guard_nes_arm271.py`는 B의 기존 오류·wrap 및 새 대기/E1 검사를 실행한다.
`guard_nes_spi271.py`는 실제 세 endpoint와 E1 snapshot 계약을 검사한다.
`analyze_nes_joint271.py`는 actual source 시간과 SPI event를 대조하고 비용표를 만든다.

Questa는 승인된 임시 Starter FLOAT, 합성은 Quartus Lite를 사용했다.
ARM guard 어댑터의 상속 오류로 실패한 armguards02와 수정 전 코드도 보존한다.
ROM/CHR/ELF·원시 로그는 비공개 증거에 보존하고 Git에는 넣지 않는다.
full RUN/NVIC·active VBlank·전체 보드 기능/CDC/IO/STA·실기60fps는 미완료다.
