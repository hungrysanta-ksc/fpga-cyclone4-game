# NES321 — host RAM 실행과 NES source·plan phase 실제 교체

기준은319 후보(315 RTL+317 metadata 선행 ARM)다.320의 실행기 교체 예산을 대상으로 실제 RTL을 생성한다. production227/GBC164/saveSRAM은 변경하지 않는다. 최종 수치와 SELECT는 아래 검증 결과에서만 확정한다.

## 삭제·대체한 실행 제어

host의 descriptor DREAD/DCAP, payload PREAD/PCAP, manifest MREAD313/MCAP313 세 read/capture 체인을 RAM_READ321/RAM_CAP321과2bit request-kind로 대체했다. header/active record는 기존 한 번의 admission 검사와 저장을 유지한다. 요청 종류는 RAM 응답이 소비될 때까지 안정적으로 유지한다. canonical queue 주소 선택과 payload 주소 선택은 이 공통 read/capture 실행에 종속된다.

receipt V_RREAD/V_RWRITE/V_PREAD/V_PWRITE, manifest V_CHECKREAD/V_CHECKTEST/V_PCHECKREAD/V_PCHECKTEST, display metadata D_READ/D_CHECK의 진행 상태를 host 상태 레지스터로 옮겼다. validator control_state321에는 이10개 상태를 저장하거나 갱신하는 경로가 없다. host의 XWAIT298와 MWAIT313 완료 대기를 삭제하고 checker predicate가 완료를 승인하면 CONSUME 또는 다음 canonical byte로 진행한다. phase/RAM 데이터 처리와 검사 predicate 자체는 validator 모듈에 남는다. 모듈 이름을 합쳤다는 의미의 통합이 아니다.

validator의 독립 cursor, expected/actual coverage, persistent validity, CRC mask, range 한도·중복 검사와 first fault는 유지한다. 초기화·hash·certificate·최종 display read 서비스는 여전히 별도 control_state321에 남는다. 특히 host 주소를 validator의 기대 정답으로 재사용하지 않는다. source CRC/plan CRC와 stored credit≠실제 consume도 유지한다. 모든 검증 제어를 없앴다고 주장하지 않는다.

NES source encoder의 동일 state register가 source 완료 후 WAIT/READ/CAPTURE/CHECK/READY/RUN/ENDING plan phase를 실행한다. plan의 별도3bit state register와 갱신을 삭제한다. plan 모듈은 순수 next-phase predicate와 decoded-field datapath/검사를 공급한다. source 압축·query·CRC는 그대로며 physical source/plan RAM·mailbox는 별개다. decoded fields는 tile_done까지 유지한다.

## 포트와 수명

queue SPI write와 host read/canonical write, phase source port-A와 validator host port-B, source NES-write/host-read, plan host-write/NES-read의 동시성·CDC를 유지한다. 새로운 공용 crossbar나 RAM을 추가하지 않는다. metadata op15 선행 발행 ARM은 변경하지 않고 PT_LOAD 주소/zero-fill/bytes의 일치로 확인한다.

receipt가 없는 명령은 이전 범위를 재사용하지 않고 CONSUME로 진행한다. 표시 ACK 뒤의 EA retire는 source 실행 phase가 끝나도 처리해야 한다. 따라서 plan 데이터 decode만 source phase로 제한하고 mailbox retire/closed 해제는 기존 수명으로 유지한다. 다음 frame의 bank 재사용은 이 반환을 기다린다.

## 실패 보존과 검증 방식

- static01..03: 생성기 anchor 및 단일 치환 assertion 오류, static04: 변환 완료. 실행 성공으로 세지 않는다.
- fixed01: RTL 변환의 빈 분기/토큰 연결 문법 오류. 원본 생성물과 vlog 로그 보존.
- fixed02: 실제 queue 읽기를 바꾼 뒤 TB C 소비 관측기가 기존 PCAP만 보아 BEGIN bytes를 놓침. 새 RAM_CAP/request-kind에 관측기를 연결. C oracle 내용은 변경하지 않음.
- fixed03: receipt 범위가 없는 명령이 공통 receipt 단계에 진입해 이전 범위를 다시 처리. 독립 중복 receipt 검사가 fault2로 거부. 범위가 있는 요청에만 실행하도록 수정.
- fixed04: frame905 표시·최종 ACK는 통과했지만 phase 종료 뒤 EA retire를 막아 frame906 plan 재사용 fault. retire 제어를 phase 제한에서 분리.

같은 source 시작 시각/ROM cycle의 fixed A/B와 연속 제한·정상 ROM을 각각 비교한다. 고정 간격의 idle을 시간 절감으로 세지 않는다. 새 계측은 RAM phase cycles/read/commit, queue read, OPEN/PUT/receipt 대기다. counter는 누적 snapshot의 인접 frame 차이로 계산한다. 최초 fixed/window 관측기의 frame 비교가 reset 중 미정 frame 값을 받아 누적 형태로 남은 것을 확인했고, 이후 관측기는 명시적인 누적으로 정규화했다. RTL/ARM과 일정에는 변화가 없다. 겹치는 counter를 합산하지 않으며 첫 BG 이전/이후 누적을 구분하지 않은 총 counter를 critical-path 절감으로 해석하지 않는다.

STOP 검증은 기존 source/plan/부분E1/E9/조기최종ACK/expected mismatch/물리ROM drain7건에 receipt read·receipt commit·manifest read·persistent validity read 도중 STOP4건을 추가한다. fault 이후 phase/queue RAM freeze 및 seal/lease/ACK 비노출을 검사한다. 실제 ARM/IRQ 및2슬롯 환경에서 실행한다.

시간은 실제 M4 명령 실행에 CPI1/84MHz 및 IRQ 모델을 적용한 값이다. ordinary65816은 기존 CPU bus trace를 재생하며 tile/map/VBlank 일부는 모델이다. MAP은 전체 Quartus Lite 합성이고 FIT/STA/실물60fps 검증이 아니다. full71/fullRUN 신규 실행은 없다.

guards01의1..7은 통과했으나8은 STOP 후 source fault의 CDC 전파 전에 정상 storage-owner hold assertion이 종료시켜 freeze 검증에 도달하지 못했다. guards02는 의도한 주입 이후에만 해당 hold 검사를 해제하고 RAM freeze/완료 비노출을 유지한다. 또한 guards01에서 누락된 .lens/.desc fixture를 복사하여11건 전체를 재검증한다. guards01의 중간 통과를 최종 SELECT로 세지 않는다.

## 전체 비용과 시간 판정

| 항목 |319 기준|321 후보|변화|
|---|---:|---:|---:|
| 전체 LE |22,618|22,882|+264|
| 전체 comb |17,824|18,090|+266|
| 전체 FF |9,022|9,018|−4|
| RAM bits |307,808|307,808|0|
| 제한 연속907 ms |17.119885468|17.119885468|0|
| 정상 연속907 ms |14.763186476|14.763050114|−0.000136362|
| 제한 시간 부족 ms |0.453218801|0.453218801|0|
| comb 부족 |2,416|2,682|+266|

고정 시작·ROM cycle 일치 A/B에서905/906/907 완료 시각은91/137/91ns 앞당겨졌다. 의도적 고정 idle을 제외해도 목표0.453ms에 비해 미미하다. 연속 제한907은 앞선 frame 종료와 다음 시작도 함께 달라져 동일 total에 머문다. 세 일정 모두 ARM 명령 수와 SPI bytes의 frame별 차이는0이며 PT_LOAD 이미지도 동일하다. 고정 SysTick36/EXTI73, 제한28/75, 정상19/73 및 제한 SPI22,379B/관측 stack1,304B를 포함한다.

같은 교체 경계는6,700→6,932comb(+232)이고 경계 밖 mapping 변화는+34이다. host2,485→2,599(+114), validator1,007→1,073(+66), source encoder1,350→1,373(+23), plan transport inclusive368→401(+33), SPI696→689(−7)이며 source transport inclusive424→426(+2),plan endpoint91→92(+1)이며 queue와 plan wrapper는 같다. 삭제한 phase 상태가 host/source 상태로 이동하고 request-kind/phase decode·복귀 선택이 추가되어, 전체 FF 절감은4개에 그쳤다. 이 구조가 RAM 주소/datapath 비용을 크게 없앴다는 근거는 없다.

host/source/validator control FSM은 추출되며 plan 전용 state register는 삭제됐다. 공통 read_kind도 FSM으로 추출된다. 따라서 비용 증가를 FSM 추출 실패나 seed 문제로 돌리지 않는다. 기존cache_index141 이외 새 latch/undriven이 없어야 한다. board01은 무범위 receipt 버그를 포함한 중간 소스에 묶인 진단 결과로 보존하며 채택 비교에는 board02만 사용한다.

warm907의 새 계측은 세 일정 모두 동일하다. checker RAM phase966cycle(11.499264µs), 그중 read483/commit19, queue read740회와 capture740cycle(17.617920µs), OPEN/PUT 대기0, receipt 대기6cycle이다. 두 RAM 실행 부분의 총 점유는29.117184µs다. 이는 제거 가능한 critical path가 아니라 실제 점유이며 header/PUT/전송/다른 실행 상태는 포함하지 않는다. 이 작은 RAM phase 자체를 직접 단축하는 것만으로0.453ms를 확보한다는 근거는 없다. ROM/IRQ/외부 소비와의 비선형 위상 효과는 실제 일정 A/B로만 판단한다. 제한warm에서 op15 release는 첫BG보다2.219342ms 앞서므로 기존 선행 정책은 유지된다. 정상ROM에서는BG가 먼저 공급될 수 있으며 모든 경우 op15가BG보다 빠르다고 주장하지 않는다.

**시간·회로 동시 개선 실패,321 미채택.** 다음 비교 기준은319+metadata 선행 ARM을 유지하므로 후속 기준 부족분은0.453219ms/2,416comb다.321의2,682 부족을 새로운 채택 기준으로 삼지 않는다. 단순 state 소유권 이동을 더 반복하지 않는다. 후속 RTL 전에 실제로 없앨 field-format/address datapath와 필요한 독립 증거를 구분하고, ARM으로 옮기는 준비/전송 비용까지 포함한 역할 변경 예산을 다시 입증해야 한다. whole FIT/seed/상태번호 반복은 하지 않는다.

최종 정상·오류 검증과 해시 결합은 analysis/execute321-verification.json을 따른다.


SELECT: fixed05/window01/normal01의9개 정상 frame 일정, guards02의11개 오류 주입, whole Lite board02. `tools/analyze_nes_execute321.py` PASS는 모든 후보 RTL·ELF PT_LOAD·기존 실제 CPU trace·MAP 입력·guard 로그를 결합한다. 고정 기준은319 fixed02, 연속 기준은319 window01/normal01이다. board의 기존 tile_closed267 export만 TB의 동등한 계층 관측과 구분해 명시적으로 정규화하며, 그 외 host/source/validator/plan RTL은 일치한다. FSM 추출·plan register 삭제·새 latch/undriven 없음도 확인한다. 새 전체71/실물/FITSTA 결과로 확대하지 않는다.
