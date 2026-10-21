# NES296 DMA 대기 중 OBJ 공급·host/validator 진행 제어 검증

DMA 대기 전에 남은 OBJ planner 작업을 실행하여 후속 plan을 공급했고, host packet 위치와 validator 단계별 RAM cursor를 공유하는 후보를 같은 경로에 연결했다. 제한 ROM의 큰 시간 회귀는 줄었지만 전체 Lite 회로 비용이 늘어 공동 후보는 미채택이다. 기능 기준289·성능 기준287·production227/GBC164/saveSRAM을 유지한다.

## 병목과 ARM 변경

기존 `io259`는 원래 E2/전송 호출마다 최대 두 plan bank를 채울 수 있었다. 문제는295에서 `tiles290`의 blocking DMA/receipt 대기가 끝나기 전까지 foreground의 마지막 OBJ planner 단계가 실행되지 않아 공급할 immutable plan이 없다는 점이었다. E9 credit을 늘리거나 IRQ를 더 자주 발생시키는 것만으로 해결되지 않는다.

296은 비-prefill E2 경로에서 `service296`을 호출한다. 입력 COMMITTED 상태와 BG 완료를 확인한 뒤 남은 planner 단계를 한 번 진행한다. `next_step286`은 완료를 기억해 foreground가 돌아와도 마지막 단계를 다시 실행하지 않는다. 새로 확정된 output 크기만 plan 공급 한도에 반영하고, 이미 추가된 최종 END 크기는 줄이지 않는다. source/plan의 원래 정렬·generation·H2 검증은 유지한다.

이 서비스는 planner만 호출하며 `tiles290`나 `io259`를 재귀 호출하지 않는다. SPI 전송이 진행 중인 buffer를 덮어쓰지 않고, 같은 foreground에서 전송 전 한 번 수행한다. 기존 두 plan bank의 credit, E9 수락 수, queue4credit, token 검사를 유지한다. STOP 뒤 입력 상태를 검사하여 계획의 추가 생산·완료 재사용을 거절한다. BG 완료는295의 비최종0x87 표식을 그대로 사용하며 별도 E9를 없앤 실험은 아니다.

## 공동 진행 제어의 실제 범위

host의 encoded packet 위치 `opos`와 끝 주소 `oend`를 제거했다. 기존 parser address를9bit로 확장해256B 끝 위치를 나타내고, 끝 주소는 queue head의 `qlen`을 사용한다. queue RAM 주소는 하위8bit만 사용하며, 끝 위치256에서 새 payload read를 하지 않는 기존 종료 조건을 유지한다. compressed input 위치와 validator의 expanded manifest 위치는 다른 의미이므로 둘을 같다고 가정하지 않는다.

validator에서는 receipt bit 위치 `v_bit_at`와 phase cursor를12bit cursor 하나로 합쳤다. receipt walk가 끝나면0으로 되돌리고 기존 V_ACTIVE admission으로 복귀한다. receipt 도중의 cursor가 manifest 진행으로 보이지 않도록 기존 receipt 상태에서 `manifest_started`/`manifest_at`을 차단한다. mask·receipt 범위 끝·실소비 CRC·중복 bit·persistent validity·map coverage·H2 certificate·12B 표시 읽기와 최종 ACK 검사는 그대로 남겼다.

이 구현은 host와 validator의 중복 진행 저장·주소 제어를 줄이는 공동 후보다. packet/manifest/receipt 전체 FSM을 단일 실행기로 대체한 구현은 아니며, concurrent CRC tap이나 독립 검사를 제거하지 않았다.

## 실행과 시간

선택 정상 test02, 제한 window02, ARM native01/armguard01/h2guard01/irqguard01, RTL guards01, 전체 Lite board01, analysis01. 71프레임 native 검사에서 원래 plan record 순서와1,039명령/73,260B가 유지되고 fixture read는0이다. native dispatch는 intercepted sink이며 서비스 호출 위치도 live E2와 구별한다. 따라서 native71을 실제71개 DMA 일정으로 세지 않는다.

새 service 함수의 진입/복귀 instruction trace를 기록했다. foreground 마지막 step 비용 감소는 일을 대기 서비스로 옮긴 결과이며, 해당 명령들은 총 ARM instruction 수에 포함한다. sent/retired는 보수적으로 캐시된 ARM 값이며 실제 DMA 동시 진행 자체의 증거로 단독 사용하지 않는다. RTL의 OBJ plan 수락과 앞선 tile receipt 시각을 별도로 기록한다. 정상905/906/907에서 service가 planner 완료로 바뀌는 것은 각각 한 번이고, 이미 발행한 BG prefix가 유지된다. 정상907의 완료 전환 시 캐시 기준 pending packet은1개지만, 제한907은 sent=retired 상태에서 tile-ready를 기다리며 실행했다. 모든 실행을 이미 시작한 DMA와의 동시 실행으로 일반화하지 않는다.

| 조건 | 295 ms | 296 ms | 변화 ms |
|---|---:|---:|---:|
|정상905|80.260491|79.689998|-0.570493|
|정상906|56.588321|56.212189|-0.376132|
|정상907|15.527359|15.473814|-0.053545|
|제한905|104.875014|104.876060|+0.001045|
|제한906|117.184094|116.900688|-0.283406|
|제한907|32.216341|17.468381|-14.747959|

정상907의60Hz 산술 여유는1.192852ms, 제한907 초과는0.801715ms다. parser+map receipt 구간 합은0.019582ms이며, 이 합을 제거 가능한 시간으로 차감하지 않는다. 기능 기준289 대비 정상907 변화는+0.158816ms, 제한907 변화는-0.531266ms다.

일정은 source replay와 같은 프레임의 실제 ARM/IRQ/shared SPI/ROM arbiter/출력 RTL 시간을 합친 것이다. CPI1/84MHz와 IRQ exception 할당, 기존 ordinary65816 bus trace, map/tile/display bus 모델은 남는다. 실제 SNES CPU 전체 실행이나 fullRUN/WCET/실물60fps 증명이 아니다.

제한907의 첫 OBJ plan 수락은276.271889→275.212038ms, 첫 OBJ 출력은291.149302→275.212402ms다. 새 OBJ plan은 앞선 tile receipt 275.351207ms보다 먼저 공급됐다. 서로 다른 전체 일정의 누적 ROM 위상을 포함하므로 전부를 SPI 전송 자체 비용으로 귀속하지 않는다. ARM 단독/RTL 단독 A/B 결과는 아니다.

907의 실제 OBJ 완료 service는49,175 instructions로,84MHz/CPI1 가정에서 약0.585417ms다. 정상907 총 ARM 명령은295보다248개 늘었고 제한907은134개 줄었다. 14ms대 전체 시간 개선은 계산량의 대폭 감소가 아니라 대기·ROM 허용 구간에 대한 실행 순서 변화다.

ARM text/data/BSS는[27458, 0, 47100]B,295 대비[128, 0, 8]B이며 관측 stack은1288B다. stack 관측치는 최대 stack/WCET 보장이 아니다.

## Quartus Lite 전체 비용과 판단

295 whole board 입력에서 host mux와 validator만 변경했다. 나머지 합성 입력 hash는 같으며 board와 live mux는 기존 board-only 관측 포트만 정규화해 비교했다. 새 whole Lite MAP 한 번을 실행했고 FIT/STA나 seed 반복은 하지 않았다.

| 항목 | 295 | 296 | 변화 |
|---|---:|---:|---:|
| LE |22603|22644|+41|
| comb |17703|17744|+41|
| FF |9029|9002|-27|
| RAM bits |307808|307808|0|
|15408 대비 comb 부족|2295|2336|+41|

host own comb2352→2339(-13), validator1088→1138(+50)다. 공유 cursor는 레지스터를 줄였지만 폭과 phase 선택 조건을 넓혀 조합 논리가 증가했다. 실제 own 집계 기준 고정 경계4847→4879(+32), 밖12856→12865(+9), 전체+41이다. 코드의 저장 bit 감소를 곧바로 LE 절감으로 계산하지 않는다.

현재 밖의 비용을 고정하면 공동 경계 예산은2543으로,4879에서2336개(약47.9%)를 더 줄여야 한다. host+validator만으로 해결하려면3477→1141이 필요하다. 시간 개선만으로 P2를 선택할 수 없으며 이번 RTL 공유 후보는 반려한다.

## 독립 검사와 보존

새 ARM 대기 서비스 검사8개는 기존 BG 전후 STOP/생산 실패/IRQ 검사에 실제 ISR 중 OBJ 완료·완료 재사용 방지·published prefix 보존·STOP 후 서비스 차단을 추가한다. native commit/실패/STOP6개, H2 9개, IRQ8cases/33exceptions도 같은 loaded ELF로 실행했다. native/ARM guard가 사용한 window01 ELF와 선택 test02/window02의 PT_LOAD segment를 대조한다. raw ELF hash는 각각 보존한다.

새 출력 RTL38개 오류 주입은 독립 CRC/receipt/manifest·ordered ACK·STOP/clock freeze·최종 ACK 검사를 수행한다. legacy guard의 미연결 progress IRQ 출력 경고3개는 유지되며 실제 IRQ는 별도 ARM/live 시험에서 검증한다. 295의 plan decoder는 hash가 같으므로 close02의9개 검사 결과를 재사용하며 새 실행으로 세지 않는다. legacy guard는 partial 입력0이며, BG 완료를 포함한 연결은 live 정상/제한각3프레임으로 별도 확인한다. 원래 E1 명령·최대4credit·metadata8570·receipt/CRC·최종 표시 ACK와 finish267→commit285 순서를 유지한다.

test01은 STOP 진입 검사를 강화하기 전 첫 정상 PASS, window01은 강화 후 관측 hook 추가 전 제한 PASS로 보존한다. test02/window02는 동일 최종 ELF와 동일 관측 전용 hook을 사용하는 선택 쌍이다. 관측 hook은 target instruction 수나 RTL 구동을 추가하지 않는다. 원본·실패 기록을 덮어쓰지 않으며 라이선스/서버 기록은 Git에 넣지 않는다.

원본은 `../probes/nes-joint296/`, 재현 entry는 `probe_nes_live296.py`, `probe_nes_native296.py`, `guard_nes_wait296.py`, `guard_nes_joint296.py`, `map_nes_joint296.py`, `analyze_nes_joint296.py`다. Questa는 기존 Starter FLOAT wrapper, 합성은 Quartus Lite를 사용한다. 분석기는 source/ELF/RTL/명령/전체 MAP hash와 합계를 검산한다.

## 더 넓은 공동 제어 후보의 예산 검토

현재 host+validator3477comb를 그대로 두고 나머지 제어만 조금 줄이는 방식은2336개 부족을 설명하지 못한다. queue129/plan576/SPI657/glue40의 합은1402다. 이들을 전부 없애는 불가능한 가정조차 필요한 절감량보다 작다. 특히 plan group576을 모두 회수한다고 계산해도1760개가 더 필요하고, 실제로는 SPI/clock/credit/lease/독립검사 비용을 다시 부담해야 한다.

검토할 더 넓은 경계는 packet read·descriptor admission·manifest byte decode·receipt 완료의 공통 실행 front-end다. 이번처럼 각 모듈 안의 cursor만 공유하는 경우와 구분한다. 단일 encoded-input cursor와 packet continuation은 공유 후보지만, RLE expanded coverage·실소비 CRC tap·persistent validity·최종 표시 읽기 coverage는 수명과 동시 실행 조건이 달라 독립 검사를 유지해야 한다. 그런 경계의 구현 비용과 실제 제거 목록은 아직 측정되지 않았으므로 현재 표에서 절감0 또는 미확정으로 취급한다. state 수나 삭제 예정 FF 수를 LUT 절감으로 환산하지 않는다.

## 다음 판단 경계

먼저 시간 개선이 확인된 대기 서비스와 반려한 cursor 공유 RTL을 분리해295의 원래 제어에 붙였을 때의 실제 일정을 확인해야 한다. 현재 결과만으로 ARM 단독 후보의 시간이 같다고 확정하지 않는다. 이후 receipt·manifest·descriptor 처리의 공통 실행 front-end가 실제로 없앨 decode/주소/control mux와 retained CRC tap·RAM port·CDC 비용을 고정 예산으로 제시해야 한다. scalar cursor/FSM/marker 바이트만 바꾸는 MAP 반복은 멈춘다.

회로가 더 큰 현재 공동 후보에서 full71/heavy7/FIT를 확대하지 않는다. 실질적인 제거 근거가 있는 후보에만 normal71/heavy7/restricted와 matching whole Lite/FIT/STA를 적용한다. 미확인 fullRUN·전체65816·실물60fps와 기존 production/GBC/saveSRAM 경계는 유지하며 자동 merge하지 않는다.
