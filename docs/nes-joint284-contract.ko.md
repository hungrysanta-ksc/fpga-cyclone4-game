# NES284 — checked 진행 응답·plan 공급·PB8 IRQ 전체 비용

NES284: E2/E8·plan 진행 응답을 공통 CRC snapshot으로 통합하고 기존 MCU_RDY/PB8 알림을 실제 ARM EXTI handler·WFI·refill에 연결했다. 정상71·제한ROM3와 독립 검사·STOP·최종 ACK를 검증했다. warm 최대 15.748447ms(954), 제한 ROM907 18.726366ms(+0.004500), 남은 시간 2.059700ms다. 전체 Lite 17,765comb(-37), 부족 2,357개. 확장 제어 경계 자체는 +4comb이므로 전체 감소를 구조적 절감으로 모두 귀속하지 않는다. 제한 ROM warm 회귀로 공동 목표는 미달이며 P2/FITSTA/실물60fps는 미승인이다.

E2(기존9B)와 E8(기존20B)을 12B FA 공통 응답으로 바꾸었다. E1/E9 압축 전송 바이트는 유지한다. output flags·accepted/retired·phase와 plan flags·accepted를 한 CRC8 응답에서 검사한다. 기존 E0 24B identity/token view, 실제 SNES DMA·읽기 coverage·ordered ACK·최종12B display ACK는 유지한다. 구형 E2/E8 길이는 거부하므로 이 protocol과 ARM은 함께 교체해야 한다. production227은 바꾸지 않았다.

plan endpoint의 중복 chunk identity 응답 mux를 없앴다. identity는 기존 output E0 owner가 제공한다. plan RAM 두 bank, reader, admission, terminal retire 및 독립 validator는 그대로 비용에 포함한다. IRQ는 기존 immutable 응답 snapshot을 비교 기준으로 재사용하며 별도 event FIFO나 token namespace를 만들지 않는다. ARM 자신이 쓰는 accepted 증가로는 알림을 만들지 않고, retired·phase·plan lifetime/fault와 output fault 변화만 알린다. snapshot 이후 변화는 다음 snapshot까지 보인다. E0/source view는 대기를 해제하며 source D0/D2/D3/D4/D5는 MCU_RDY를 원래 memory-ready 모드로 돌린다.

PB8/EXTI8/NVIC23 배선과 주소는 기존 target autoconf/CMSIS header에서 확인했다. 실제 ARM이 GPIO·SYSCFG·EXTI·NVIC를 설정하며 ISR은 EXTI8 W1C와 wake count만 처리한다. SPI는 foreground에 남는다. 첫 checked E2 뒤에만 EXTI를 켜고 frame 실패와 plan 종료/실패에서 마스킹한다. 따라서 source 단계 memory-ready 변화는 handler를 실행하지 않는다. PRIMASK로 check/WFI 경계를 닫고, GPIO level도 확인하여 IRQ가 먼저 처리되더라도 대기를 놓치지 않는다. 이 wait 함수의 caller는 interrupt-enabled foreground다. 현재 adapter는 실제 handler·8-word exception frame·PRIMASK·W1C·foreground 경계 delivery를 실행하며 전체 STM32 peripheral/NVIC priority simulator가 아니다. SPI 중간 preemption과 full firmware ownership 복원은 미검증이다. EXTI 진입·복귀는 각24 zero-wait 사이클을 별도 과금했으며 하드웨어 WCET가 아니다. 기존 SysTick 본문은 service boundary에서 실행하고, 다음10ms tick이 불관련/유실 알림의 checked fallback을 제공한다.

기존 full firmware의 nes_return_spi_ready는 아직 PB8 memory-ready를 기다린다. 새 알림 모드의 실제 펌웨어 적용에는 SPI ready 경로·IRQ 소유권/복원 변경이 필요하다. 이번 physical267 경계는 그 전체 STM32 driver 구현을 실행하지 않으며 실행 가능한 firmware image를 만들지 않았다.

| 일반 프레임 | NES283 | NES284 | 변화 | 16.667ms 여유 |
|---|---:|---:|---:|---:|
|952|14.313237|13.629518|-0.683719|3.037148|
|954|16.063171|15.748447|-0.314723|0.918219|
|955|14.285783|13.852288|-0.433495|2.814378|
|962|14.943912|14.849595|-0.094317|1.817072|
|963|14.370691|14.258056|-0.112635|2.408610|
|968|13.115070|13.049116|-0.065954|3.617551|
|970|15.561041|15.484541|-0.076499|1.182125|

단위 ms. source 실제 RTL/SPI 및 ARM decoder 명령 비용 replay + output live ARM·IRQ·ROM·CPU279 bus trace를 합친 진단 일정이다. source live ARM/full RUN/실물60fps 경계는 아니다. cold905/906 초기화와 warm69를 구분한다.

| 제한 ROM | NES283 | NES284 | 변화 | 절대 종료 |
|---|---:|---:|---:|---:|
|905|88.863888|88.642709|-0.221179|102.921719|
|906|114.095949|114.252902|+0.156953|231.081182|
|907|18.721866|18.726366|+0.004500|263.714108|

제한 warm907 부족은 2.055200→2.059700ms. 세 프레임 절대 종료 변화는 -0.059727ms다. 제한 ROM은 기존 고정 주기/허용 window/12cycle slot을 그대로 사용한다. 앞 프레임의 종료 위상이 다음 구간의 ROM 대기를 바꾸므로 절대 종료와 구간 시간을 따로 비교한다.

| 제한907 비용 | NES283 | NES284 |
|---|---:|---:|
|E2|304|23|
|E8|3|0|
|SPI B|3701|1181|
|SPI 경계 ARM/IRQ 명령|179226|82898|
|ROM slot 대기 cycle|229796|230121|
|tile 대기 cycle|229809|230135|

NES284 추가로 WFI/종료 경계까지 합친907 ARM/IRQ 명령 87,580, EXTI 진입·복귀 allocation 312cycle, WFI 10회, 타이머 fallback 1회다. 이전 SPI 경계 명령과 새 전체 경계 명령을 같은 수치로 취급하지 않는다. 전체 경과 시간에는 모두 포함했다. ROM wait는 ARM/SPI와 겹치므로 별도로 다시 더하지 않는다.

제한907의 ROM slot 대기는 229796→230121cycle로 +325cycle 변했다. SPI는 2,520B 줄었지만 기존 polling이 ROM 대기와 겹쳐 있어 전체 시간에서 wire 절감을 다시 빼면 안 된다. 906 절대 종료는 -0.064226ms, 907은 -0.059727ms 이동했다. 이 시작 위상과 대기 기록을 함께 보며 warm 구간 +4.500µs 회귀와 세 프레임 종료 개선을 구분한다.

ARM text 5050B(+368), BSS 628B(+4), 관측 stack 304B(+32); stack에는 실제 예외 frame도 포함한다. source codec만 CPI2로 둔 frozen 일정 민감도는 최대 16.841138ms, 부족 0.174471ms다. 하드웨어 cache/flash wait나 IRQ WCET로 읽지 않는다.

| 전체 Lite MAP | NES283 | NES284 | 변화 |
|---|---:|---:|---:|
|LE|22,751|22,714|-37|
|comb|17,802|17,765|-37|
|FF|9,088|9,086|-2|
|RAM_bits|307,808|307,808|+0|

| own 조합 논리 | NES283 | NES284 |
|---|---:|---:|
|host|2408|2410|
|validator|1040|1038|
|queue|125|129|
|plan|570|574|
|selected|4143|4151|
|outside|13659|13614|
|budget|1749|1794|

기존 selected에 common SPI를 더한 실제 변경 경계는 4805→4809(+4)comb다. 공통 SPI 자체 662→658, 나머지 outside 변화 -41다. 수정하지 않은 NES/PPU/ROM 계층에도 합성 매핑 변화가 있으므로 전체 -37를 제거한 제어의 확정 절감으로 부르지 않는다. 핀 소유권 수정 전 board01을 보존하고 최종 board02로 다시 MAP했다. 기능 수정 재검증이며 FIT/STA나 seed 탐색은 하지 않았다. 새 경고는 제거된 plan 응답의 사용하지 않는 offset 식 1건이며 합성에서 제거된다. undriven 경고는 없다.

확장 변경 경계 4,809comb의 예산은 2,452, 128개 여유 포함 목표 2,324다. queue·plan·common SPI 합계 1,361개를 전부 0으로 두는 불가능한 산술에서도 996개가 남는다. 따라서 작은 polling/status 제어만의 정리로 용량 목표를 해결할 수 없으며 host·validator 또는 다른 큰 경계까지 실제 교체해야 한다. 이 산술은 FIT 결과가 아니다.

선택 증거: test04, window01, guards01, armguards02, spiguards03, board02, irqguards03, crcguards02, test05, analysis02. 정상71·제한ROM3, E1 1,231개/E9 원본 바이트 exact283, source47,900B, map2,069범위, CPU trace544명령, 최대4credit, metadata8,570B/receipt754B/hash64B의 프레임별 독립 검사를 유지했다. ARM 진행 parser25·CRC65,536쌍·SPI68·STOP/ACK17·IRQ8종(33예외) guard PASS. 정상 연결에서 EXTI 1431회, 제한에서 74회다.

test01은 기능PASS지만 이미 확인한 plan 종료를 다시 기다려 프레임당10ms fallback이 생긴 실패 후보로 보존했다. 최종 C는 cached ended/accepted를 먼저 검사해 terminal retire를 즉시 진행한다. test02는 수정3프레임과 SPI65 증거이며 test03은 source 단계에서도 EXTI를 켜 두는 소유권 문제가 발견되어 중간 종료한 기록이다(라이선스 오류 아님). 최종 test04/window01은 첫 checked E2 뒤에만 EXTI를 켜고 frame 실패·plan 종료/실패 시 끄는 ARM으로 다시 실행했다. source 단계 GPIO 변화가 handler를 실행하지 않는 guard도 추가했다. spiguards02는 없어진 dcommand 시험 helper를 호출해 compile 실패했고 spiguards03에서 현재 prefix를 사용해 수정했다. 핀 모드 복원에 실제 source D4/D5를 추가했다. 이 변경은 progress_mode 출력에만 쓰이며 내부 상태/IRQ/status에는 fanout이 없고 71프레임 timing harness도 이 출력을 읽지 않는다. 최종 test05 3프레임 시간은 test04의 해당3개와 정확히 같고, 최종 SPI68과 board02는 변경 RTL을 사용한다. 최종 핀 분기까지 포함한 새71을 실행했다고 주장하지 않는다. validator RTL은283과 byte exact이며 기존307범위 검증의 적용 경계를 보존한다. STOP guard는 RTL 취소/동결이고 full firmware error→STOP 전송 루프를 새로 증명한 것은 아니다.

이번 후보는 일반 일정과 ARM polling 개선으로 남기되, 제한 ROM까지 개선한 공동 목표 달성안으로 채택하지 않는다. 다음 시간 검토는 source 입력 중 더 일찍 plan을 공급할 수 있는지 확인하는 것이다. 실제 ARM decoder의 데이터 의존성과 기존 staging·ROM 포트 소유권이 허용하는지 먼저 입증해야 한다. output/DMA의 input COMMITTED 장벽은 유지하고 공유 SPI·ROM 경쟁을 모두 과금한다. polling 지연값만 조정하는 방식은 사용하지 않는다.

회로는 common SPI까지 포함한 4,809comb 경계에서 descriptor 해석·실제 읽기/ACK coverage·receipt/H2/manifest 종료·plan/tile 수명을 함께 교체해야 한다. 허용 예산 2,452개(128개 여유 포함 2,324개)와 각 독립 검사를 고정하고 비교한다. 전체 펌웨어 SPI-ready/IRQ 소유권 복원·실제 source ARM·새 live65816/active VBlank·전체 program ROM·FIT/STA·실물60fps는 계속 남은 검증이다. production227/GBC164/saveSRAM은 보존하고 자동 merge하지 않는다.
