# NES367 실제 ARM source foreground·causal hint와 연속 캡처 경계

PR132 / `codex/nes-capture-admission-365`. PR131 merge `914138969246387162bf2c909159824e72a3666d` 위의365–366 증거를 보존한다. 이번 비교의 기준 HEAD는 `067e9d4e45e65cffab570cdaa74f668f8ced17b4`이다.

## 결과와 판정

908의 후반 ROM 대기는 줄었다. 동일 RTL·시작 시각·ROM 위상에서 hint만 바꾼 결과 **20.650139 → 13.117365ms**, **7.532774ms 개선**이다. 다만 더 긴 일정에서는 **910 캡처가 거절**된다. 연속 캡처 통과·실기60fps 후보로 채택하지 않는다.

`long01`은 hint 축소 뒤 기존 core, `long03`은 마지막 로컬 저장 해제로 바꾼 core에서 모두910 시작을 즉시 실패 처리했다. `long02 --observe-miss --last909`는910 거절을 그대로 기록하고909만 끝까지 배출한다. 마지막에 `capture coverage367`로 반드시 실패한다. 이 진단의5개 완료 프레임을5개 연속 캡처 성공으로 세지 않는다. 계획했던905..911 정상 완료는 달성하지 못했다.

## 실행 경로와 소유권

- `source_receive367()`·N5 decoder·planner·refill·output serializer는 같은 Cortex-M4 ELF에서 실행한다. 기존 source 비용 replay와 별도 hint ARM snapshot helper는 runtime 경로에서 제거했다.
- D4의13B prefix를 먼저 받고, header CRC8·token·length를 검사한 다음 같은 CS에서N+2B를 받는다. source payload CRC16와 N5 의미/연속성 검사를 유지하고 마지막 D5만 입력 commit을 보낸다. 같은259B `wire259`를 사용하며 추가 SPI buffer는 없다.
- IRQ는 SPI를 사용하지 않는다. D4/D5가 기존 MCU_RDY pin을 source 현재 head-ready/fault로 선택하고, EA는 그 소유권을 유지한다. E2/E8 이후에는 output 진행 IRQ를 사용한다. mask/check/WFI/unmask와 실제 compiled EXTI/SysTick body를 실행하고 entry/exit24cycle을 각기 명시적으로 계상한다.
- 매 CRC-통과 block에서 아직 hint를 보내지 않았다면 생산을 시도한다. cold·stale epoch/serial/generation·미표시/open/prepared/fault·STOP cancel에서는 차단한다. 현재 변경된 geometry 그룹의 우선 tag를 먼저 선택하고, 그런 후보가 없을 때 이전에 표시한 bank의 BG5/OBJ2 부족분을 사용한다. future plan oracle은 생산에 쓰지 않는다.
- fixed28B EA·7entry/112B 유효cache를 유지한다.908은0213/0218/0216 세 tag 뒤의 빈 lane을 같은 causal tag로 반복한다. 불필요한 이전 BG/OBJ tag를 채우지 않아 ROM 창 안에서 끝난다.908 helper는6,018명령이며 ARM의 정확한 tag-membership RAM1KiB를 사용한다.
- collector read 해제는 마지막 local base RAM 저장이 끝난 `BLOCKEND && cursor==4398+raw_limit && !q_pending`으로 정한다. 이전RAWSTART/압축 record 전송 대기는 제거했다. raw0/1/2 모두 해제 뒤256clock 소비를 막고 collector 응답을 바꿔도 추가 query가 없음을 확인했다. 추가 FPGA RAM/copy는 없다.

## 처리 일정

| frame | source 시작→최종 완료 ms | 마지막 local 저장 ms | 입력 ACK ms | source SPI B | hint SPI B |
|---|---:|---:|---:|---:|---:|
| 905 | 99.274558 | 21.383516 | 23.583603 | 6076 | 0 |
| 906 | 116.690213 | 0.579220 | 2.544401 | 507 | 0 |
| 907 | 12.157104 | 1.709843 | 2.843761 | 582 | 28 |
| 908 | 13.117365 | 0.576948 | 2.663355 | 468 | 28 |
| 909 | 21.458584 | 2.398471 | 4.058520 | 917 | 28 |

905/906은 직렬 초기화이다. 연속 구간은907 이후 실제PPU908/909와 다음910 시작을 독립적으로 공급한다. fixture 주기는357,368NES clocks(45.454ns/clock,약16.244ms)이며, 처리 시간에는 캡처 자체가 포함되지 않는다. 실제 콘솔 주기나 전체 VBlank 완료의 실측치로 해석하지 않는다.

910 시작에서 collector는 여전히 owned였다.909 마지막 local 저장 대비 캡처 여유는 **-0.058248ms**이다. 입력 수신·CRC/해석·hint 뒤 다음 D4의8번째 byte에서만 이전 packet pop이 적용되는 경로가 source 생산을 막는다. 마지막 저장 신호만 앞당겨도 아직 도착하지 않은 query 데이터를 대신할 수 없다. 또한909의 실제BG plan은0213/0218/0216을 요구하지만 송신 hint는0213/0218 두종류뿐이었다. 마지막BG tile은 plan302.433984ms→tile307.393879ms까지 기다렸다. 따라서 collector58.248us만 줄여도909 표시 초과4.791917ms가 자동으로 해소되지는 않는다. 기한을 늦추거나 캡처 성공 신호를 강제하지 않았다.

동일 old-core control/hint-only 비교는 ARM loadable code/data와 전체 RTL,905..908 시작 시각 및 ROM cycle가 같다. 마지막 저장 해제 변경은 별도 joint run으로 분리한다. 후속 frame의 연속 위상 차이를 독립 최적화 시간으로 합산하지 않는다. 실제 read→unit→private write→publish,2slot credit,12 exact display reads 및 token ACK는 완료한 각 프레임에서 독립적으로 다시 대조했다.

## Quartus Lite 전체 비용

| 전체 MAP |365–366|367|변화|
|---|---:|---:|---:|
|LE|22817|22803|-14|
|comb|17776|17762|-14|
|FF|9217|9218|+1|
|RAM bits|308832|308832|0|

source-ready IRQ만 연결한map01은17,830comb으로54 증가했다. 마지막 저장 조건까지 바꾼map02는17,762comb이다. 전체14 감소를 core 본체68개 삭제로 주장하지 않는다. core self는1,350→1,356, SPI self는557→565이며, 전체 합성 최적화 결과와 각 hierarchy 비용을 따로 보존한다. parent/child inclusive 값은 합산하지 않는다.

기능 tests와 whole QSF는11개 canonical file 및30개 공통 compiled module의 bytes가 일치한다. source/transport/SPI3파일은 `src/fpga/nes_hint367/manifest.json`으로 고정한다. 나머지365–366 canonical bytes는 보존한다. **조합 논리2354개 부족**,155개 여유를 포함하면 **2509개 순삭제**가 추가로 필요하다. FIT/STA는 실행하지 않았다.

ARM 전체 ELF는 text33618B/data4B/BSS48476B이며, 같은 build의 pre367 image 대비 text+1604B/BSS+1056B이다. 관측 stack은1288B이다. data도0→4B이다. production 전체 firmware RAM/stack 승인이나 hardware WCET는 아니다.

## 검증 범위와 다음 예산

28개 hint 차단 검사,9개 실제M4 source IO 시나리오,11개 SPI/pin ownership 검사,68개 실제 cache/arbiter/STOP/legacy-retire 검사,raw0/1/2 지연 소비를 통과했다. 변경 없는 controller의22개 session guard 증거도 hash로 유지한다. 진단 종료 때 ARM 결과 파일 생성을 기다리는 poll에서32개의FOFIR 임시파일 경고가 발생했고, 모두동일한arm-result.json 미생성 경고임을 확인했다. 정상control과strict 첫 실패에는 해당 경고가 없다. 실패한 declaration/worker namespace/old5tag guard fixture 및910 strict failure 로그를 보존한다.

Compiled SysTick/EXTI bodies plus allocated 24 entry/exit cycles; bounded peripheral adapter, not hardware WCET.

Declared ready-gated period120 NES-clock stress at001234 during both input/output; real physical-reader arbitration, not live NES CPU.

Existing ordinary65816 bus traces; DMA/final display remain bus models. Unchanged VBlank firmware is not a new full65816 proof.

909의0216 BG tag가 실제 plan에는 필요하지만 hint에서 빠진 원인과 후반 cache miss를 먼저 분리한다. 58.248us collector 해제 부족과4.791917ms 표시 초과를 각각 줄이는 공급·준비 예산을 잡는다.909 입력의 실제 저장 완료·credit 반환과 ARM decode/hint를 분리할 범위 및 RAM 포트·바이트 예산을 먼저 확정한다. 기존 D4의 다음 요청에서만 pop하는 경로, ARM SPI DMA/수신 보관의 중첩 후보를 전체 비용으로 비교한다. 캡처 기한을 늦추거나 실패를 승인하지 않는다. 독립 검사·STOP·최종 ACK·VBlank를 유지하고, 연속/heavy7/71 및 실제65816 표시 서비스 통과 뒤에만 전체 Lite FIT/STA/실물 단계로 간다. 새 opcode/부분 FSM/seed/FIT 반복을 먼저 시작하지 않는다.

production227·GBC164·saveSRAM·기존 VBlank firmware는 변경하지 않았다. 자동 merge는 하지 않는다. 재현 입력/실패 원본은 private `probes/nes-hint367`, 검증 hash와 비용은 `analysis/hint367-verification.json`을 따른다.
