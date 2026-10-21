# NES297 ARM 대기 서비스 분리와 공동 실행 제어 예산

ARM296의 대기 중 OBJ 생산을 기존 RTL295에 연결했다. 반려한296 cursor 공유는 적용하지 않는다. 새 정상·제한 ROM 일정으로 ARM 변경의 효과를 분리하고, RTL/전체 합성 입력의 동일성을 확인하여 기존 Quartus Lite295 비용과 비교한다. 기능 기준289·성능 기준287과 production227/GBC164/saveSRAM은 유지한다.

## 분리 조건과 전체 시간

`probe_nes_live297.py`는296 entry에서 `nes_joint296.apply`만 제외한다. service296, native producer, BG partial0x87, 두 plan bank, four-credit queue, source replay, CPU trace, ROM 제한, 관측 hook은 유지한다. 새로 빌드한 ELF의 PT_LOAD 주소·크기·권한·바이트가296과 같고, live RTL hash는295와 모두 같다. 디버그 정보 등으로 raw ELF가 달라도 이를 실행 코드 차이로 세지 않는다.

| 조건 | ARM295+RTL295 ms | ARM296+RTL296 ms | ARM296+RTL295 ms | 295 대비 ms |
|---|---:|---:|---:|---:|
|정상905|80.260491|79.689998|79.689998|-0.570493|
|정상906|56.588321|56.212189|56.212189|-0.376132|
|정상907|15.527359|15.473814|15.473814|-0.053545|
|제한905|104.875014|104.876060|104.876060|+0.001045|
|제한906|117.184094|116.900688|116.900688|-0.283406|
|제한907|32.216341|17.468381|17.468381|-14.747959|

정상907 여유1.192852ms, 제한907 초과0.801715ms다.296 대비 제한907 변화는+0.000000000ms다. parser+map receipt 관측 구간 합0.019582ms는 제거 가능한 시간이나 상한으로 사용하지 않는다.

ARM의 OBJ 계산은 삭제되지 않았으며 service 진입/복귀 instruction 수와 총 ARM 비용에 포함한다. E9·E2·timer fallback·SPI bytes·ROM wait는 normal/restricted CSV에 기록했다. 이전296과 비교하면 같은 ARM의 RTL 차이,295와 비교하면 같은 RTL의 ARM 차이를 확인할 수 있다. 세 조합은 동일 초기 시험 조건을 사용하지만 프레임별 누적 ROM 위상은 각 실행 순서의 결과다. 단일 명령이나 SPI wire 비용만의 절감으로 해석하지 않는다.

제한907 첫 OBJ plan 수락275.212038ms, 첫 OBJ 출력275.212402ms, 앞선 tile receipt275.351207ms다. 서비스 계산49,175instructions를 총 비용에 포함했고, plan 공급이 앞선 receipt보다 빠른지 이 실제 RTL 시각으로 확인한다.

전체 시간은 source replay와 같은 프레임의 실제 compiled M4/IRQ/shared SPI/ROM arbiter/출력 RTL 일정을 합산한다. CPI1/84MHz, IRQ overhead 할당, 기존 ordinary65816 trace와 map/tile/display bus 모델이 남는다. 새로운 fullRUN, 전체 live65816 CPU, WCET 또는 실물60fps 측정이 아니다.905/906은 초기 상태를 포함하며 warm907과 구별한다.

## 독립 검사·credit·STOP·최종 ACK

새 live 정상/제한905–907의 원래 E1 순서·최대4credit·metadata/CRC/receipt·최종 표시 ACK·finish267→commit285를 확인한다. service 완료 전환은 프레임당 한 번이다. sent/retired는 ARM 캐시이므로 이 값만으로 DMA 동시 실행을 주장하지 않고, 실제 plan/receipt RTL 이벤트를 별도로 비교한다.

ARM native71/원래 plan1039명령73260B·fixture read0, native6guards, wait-service8guards, H2 9guards, IRQ8cases/33exceptions는296의 동일 loaded ELF 증거를 재사용한다. RTL38guards와 BG-close9guards는295의 동일 RTL 증거를 재사용한다. 재사용은 새로운 오류 주입 실행이 아니며, 새 live6프레임과 구별한다. 코드/RTL/결과 hash를 분석기에 고정한다. 합성 입력이 같으므로 같은 MAP를 다시 실행하지 않는다. 실패/기존 기록은 보존하고 라이선스 자료는 공개하지 않는다.

실행 기록상 두 simulation은 errors0/PASS로 완료됐으나 외부 wrapper 세션의 반환 코드는-15였고 별도 로그는 비어 있다. 원인은 미확정으로 원본 `execution-status.json`에 남긴다. simulation 실패나 새 라이선스 문제로 해석하지 않으며 wrapper 정상 종료를 주장하지 않는다.

## Quartus Lite 비용

| 항목 | 296 공동 cursor | 297 ARM 분리 | 변화 |
|---|---:|---:|---:|
|LE|22644|22603|-41|
|comb|17744|17703|-41|
|FF|9002|9029|+27|
|RAM bits|307808|307808|0|
|comb 부족|2336|2295|-41|

이번41comb 회복은296의 불리한 cursor 공유를 제외한 결과다.295 대비 새로운 RTL 절감은0이며 넓은 공동 실행기를 구현·합성한 결과가 아니다. 동일 RTL의 기존 whole Lite MAP를 재사용한다. board-only tile_closed 관측 포트만 정규화하고 live/board mux와 validator/plan/tile RTL을 대조하며, 전체 board 입력 hash와 own 합계를 검산한다. FIT/STA는 실행하지 않는다.

## 공동 실행기에서 실제 바꿀 경계

292의17개 전이 설계에 대해295의 실제 소스 위치를 다시 결합했다. `analysis/joint297-control.csv`는 교체할 중계 제어와 유지할 검사·RAM port·추가 비용을 각 anchor에 연결한다. 과거 설계를 새 구현으로 세지 않는다.

1. **receipt 완료 continuation**: host의 SEND→WAIT_RECEIPT→CONSUME 및 OTILE/OSELECT→ORET와 validator의 V_ACTIVE 복귀/재-dispatch를 공통 실행기의 완료 전이로 바꾼다. ordinary exact-read/ordered ACK/tap drain 또는 map exact-read/full-token consume을 확인한 후 같은 RAM walker로 진입한다. 마지막 range에만 batch credit을 돌려주며 기존 단일 op12의 조기 packet-retire와 aperture 수명을 혼동하지 않는다. 명령별 retire 정책을 명시적으로 유지해야 한다.
2. **manifest 실행**: host의 OCHECKNEXT/ORLE ready 확인과 validator의 바이트별 V_ACTIVE 재진입을 직접 decode→RAM read→compare→decode 복귀로 교체한다. encoded cursor/RLE remaining, expanded422B cursor와 두 번째 RAM 비교용 checked_byte는 동시에 필요하여 유지한다. 단순히 cursor bit를 공유하는296 후보와 다르다.
3. **descriptor admission**: original header를 소비 완료까지 보유하고 독립 domain/alignment/widened end 검사를 유지한다. receipt first/count 전달과 중복 실행 선택을 공통 admission으로 옮기는 것이 대상이다. ARM 계산값을 믿어 검사 산술까지 삭제하는 안은 제외한다.
4. **동시 SNES/CRC observer**: ordinary bus 읽기 중 pattern 확장·실소비 CRC가 진행하므로 strobe latch, pattern, CRC 상태는 계속 살아 있어야 한다. 공통 FSM의 BUS_WAIT가 observer 실행을 막아서는 안 된다. 완료 event를 받는 continuation과 RAM address/data 선택 비용도 새 회로에 포함한다.
5. **display/STOP**: seal·certificate·12 exact reads·full token·empty queue/owner 이후 final mailbox를 보내는 규칙은 유지한다. STOP/fault는 RAM write보다 우선해야 하며 token/serial 소각·bank invalidation·stale ACK 거절을 보존한다. 내부 fault relay 제거도 같은 edge의 write inhibit를 입증한 뒤에만 가능하다.

port A는 NES source/lease, port B는 host validator가 소유한다. 공동 실행기는 host-clock 안에서 B의 소유권을 바꾸는 안이다. source clock을 합치거나 queue RAM·phase RAM·aperture RAM을 같은 port로 간주하지 않는다. 두 sealed plan bank와 E9/EA credit은 refill과 tile ROM 소비가 겹치기 위해 유지한다. 새 descriptor latch·continuation selector·bus mode·RAM mux를 무료로 계산하지 않는다.

| 공동 경계 | 현재 comb | 대체 예산 |128 여유 예산|필요 절감|
|---|---:|---:|---:|---:|
|host+validator|3440|1145|1017|2295|
|queue/plan/SPI/glue 포함|4847|2552|2424|2295|

host2352/validator1088/queue128/plan573/SPI657/glue49, 밖12856comb다. 계층 own 합계만 사용하여 parent/child를 중복 합산하지 않는다.

host+validator만으로 해결하려면 약66.7%를 줄여야 한다. 이 영역에는 독립 검사와 CRC/datapath가 포함되며 state 수를 줄인다고 이 비율이 회수되지 않는다. queue+plan+SPI+glue1407개를 모두 없앤다는 불가능한 가정조차2295보다 작다. 따라서 작은 control 묶음만의 후보는 목표 해결안으로 채택할 수 없다. 넓은 공통 실행기의 새 comb는 미측정(null), 입증한 추가 절감은0이다.

## 다음 검증의 합격 조건

ARM296+RTL295를 시간 분리 참조로 보존한다. 다음 구현은 위 receipt·manifest·descriptor의 완료 전이와 dispatch를 한 번에 교체하고 동시 observer를 남기는 후보여야 한다. 새 mux·continuation과 유지 검사를 포함한 실제 whole Lite MAP를 한 번 측정해2295개 부족에 의미 있는 변화가 있는지 판단한다. host+validator만을 대상으로 할 경우1145comb 이하, 고정 경계 전체는2552comb 이하가 무여유 산술 목표이며128개 여유를 원하면 각각1017/2424다. 이는 예측이나 물리 배치 보장이 아니다.

시간은 정상/제한 동일 프레임에서 모두 비교하고, 제한907의 남은 초과를 숨기기 위해 parser/receipt 구간을 단순 차감하지 않는다. ROM 창에 걸친 plan 수락·첫 OBJ·receipt·최종 ACK 일정을 함께 비교한다. 오류 주입은 ordinary/typed/batch·raw0/cold-bank·중간STOP·RLE 경계·중복 receipt·full token·final ACK에서 새 실행기를 검증해야 한다. 이 근거 없이 scalar FSM/opcode/seed/FIT 반복이나 full71/heavy7 확대를 하지 않는다. 자동 merge하지 않는다.
