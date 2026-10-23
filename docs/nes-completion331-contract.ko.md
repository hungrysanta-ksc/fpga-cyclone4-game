# NES331 — cold 준비와 완료·chunk 응답 통합

330의 ARM tile 재개·첫 map 준비와 325 RTL을 직접 비교한다. 328에서 분리 검증한 325 RTL +327 manifest 선행 발행도 별도 기준으로 남긴다. 목표는 cold 준비 회귀를 줄이면서 완료·identity 전달의 기존 제어를 실제로 교체하는 것이다. 아래 시간은 실제 Cortex-M4 명령을 실행한 CPI1/84MHz 모델이며, SPI/IRQ/2슬롯/ROM/staging과 기존325 65816 bus trace를 연결한 일정이다.

## 구현과 실제 삭제 범위

- 첫 map 준비가 완료됐거나 아직 소유권을 받을 수 없으면 반환값2로 해당 준비 루프를 끝낸다. 이전처럼 준비 함수의 무작업 성공 반환 뒤 최대16회 같은 호출을 반복하지 않는다. 함수 호출 자체는 다음 idle 방문에서 다시 가능하다.
- map bitmap의 정렬된 `0xff` byte는8word 단위로 진행한다. 현재 range32word 상한,208B 임시 packet 상한과 범위 순서를 그대로 검사한다. cold frame 번호나 특정 게임 장면을 조건으로 생략하지 않는다. 비최종 tile 재개16record, metadata 발행 후209B scratch 소유권, DMA·plan credit·IRQ 우선조건을 유지한다.
- E0 완료·identity 응답을 E2의 공통 진행 prefix와 합친다. 별도 E0 accepted/retired/consumed 검사 구현을 삭제하고 `progress331` 한 경로로 CRC·namespace·2슬롯 credit·소비 완료를 검사한다. E0가 plan 상태도 전달하므로 읽은 직후 plan cache를 버리는 동작을 제거한다.
- 응답 buffer는 실제 거래 길이만 초기화한다. 짧은14B poll에서도26B를 지우던 비용을 제거한다. identity가 필요한 tile/map 경로는 사용 직전에 긴 E0를 다시 읽고 검사하므로 짧은 응답 뒤 남아 있는 이전 identity byte를 사용하지 않는다.
- allocation token과 ready chunk token을 둘 다 전송하던 필드를 ready 상태에 맞는 하나의 token으로 대체한다. tile 명령은 ready·owner·bank·kind·slot·length·generation을 검사한 뒤 token을 복사한다. map 시작은 drain과 tiles-closed, chunk-not-ready를 검사한 뒤 allocation token을 사용한다. 기존 FPGA token 검사는 그대로다.
- SPI snapshot의 동적 byte 주소 선택기와 CRC/전송 주소 선택을 제거한다. 캡처한200bit 응답을 한 byte lane으로 순환시켜 CRC를 만들고, 전송도 같은 순차 lane을 쓴다. CRC 사전 순회는25 host clocks이며 전체25byte를 회전해 원래 순서로 복원한다. 유효 응답 byte만 CRC에 포함한다. 원래 transaction 시작 시점의 값이 전송 끝까지 유지된다.
- 순환하는 응답 저장소를 IRQ 비교에도 쓰면 잘못 깨우므로, 기존 autonomous 비교 항목을49bit 기준값으로 캡처한다. queue fault1bit, retired16+phase8bit, plan flags8bit, consumed16bit다. accepted/plan-accepted의 ARM 자체 송신 변화는 IRQ 원인으로 추가하지 않는다. 이 추가 레지스터 비용도 전체 합성에 포함한다.

새 E0는25B, E2/E1/E9의 진행 응답은14B다. 모든 poll을 긴 응답으로 바꾸지 않는다. E1/E9 압축 전송 형식과 SNES 소비 ABI는 변경하지 않는다. queue의 E0 길이 검사는 새25B로 교체하며, 이전26B 요청은 오류다.

|E0 byte|의미|
|---|---|
|0|command 송신 중 dummy|
|1|FB tag|
|2|queue flags|
|3..4 /5..6|accepted /storage-retired, big endian|
|7|tiles-closed /chunk-ready /map-owner|
|8 /9..10|plan flags /plan accepted|
|11..12|actual-consumed, big endian|
|13..16|ready chunk token 또는 allocation token, little endian|
|17..18 /19|chunk length /bank·kind·owner|
|20..21 /22..23|slot /generation|
|24|byte1..23 CRC8|

짧은 응답은 byte1..12를 CRC로 보호하고 byte13에 CRC를 둔다. 긴 응답은 identity까지 포함한 CRC를 사용한다. transaction-start snapshot은 현재 송신 중인 E1의 수락 증명이 아니다. 저장 credit과 실제 소비 완료의 계수는 통합해서 하나로 만들지 않는다.

## 유지한 검사와 포트

독립 expected RAM, 실제 SNES read CRC/receipt, generation/token, STOP 후 RAM freeze와 physical ROM drain, 최종12display read/ACK, VBlank, tile 두chunk 선행 생산을 유지한다. phase RAM의 NES/host 포트, queue의 ingress/reader·expected 접근, staging RAM 소유권은 바꾸지 않는다. 현재 표시 lease와 완료가 없는데 새 프레임을 열 수 있도록 조건을 완화하지 않는다.

host·validator 실행 FSM, manifest 중계, receipt read/modify/write, 최종 검사 cursor, source·plan decode FSM과 queue consumed 계수는 남아 있다. 이번 결과를 이들 블록 전체의 삭제로 계산하지 않는다. 실제 삭제는 별도 ARM E0 완료 검사, 중복 token 전달, SPI 동적 snapshot byte 선택과 기존 snapshot 필드 직접 IRQ 비교다. immutable snapshot 저장 자체를 없앤 것은 아니다.

## 검증 방식

최종 공동 후보는 제한 연속·고정 source-start/ROM cycle·정상 연속 각3프레임을 실행한다. ARM cold 준비만 바꾸고 원래325 RTL/응답 ABI를 유지한 제한·정상 각3프레임도 비교한다. 고정 일정은 과거와 source 시작 시각 및 ROM cycle을 일치시킨다. 연속 일정은 시작·ROM 수락·절대 완료·프레임 duration을 따로 기록한다. ROM 허용창과 코어 경쟁은 변경하지 않는다.

별도71프레임 ARM 생산자는 dispatch를 가로채는 기능 oracle이며 실제 credit/ACK 일정과 구분한다. 강제 재개3프레임은 준비 중/후 STOP, tile batch 중간 재개와 모호한 송신 실패 후 재시도 금지를 검사한다. 최초 생산자 시험 ELF와 이후 RTL 수정 경로의 ELF는 debug path hash가 달라질 수 있으므로, 전체 PT_LOAD가 같은지도 확인한다.

실제 ARM 공통 응답 검사205건은 각 응답 bit CRC 오류, 미래 accepted/retired/consumed,16bit wrap, 저장 credit과 소비 완료 분리를 포함한다. 별도 tile dispatch11건은 ready/owner/bank/kind/slot/length/generation 오류가 E1 송신 전에 거부되는지, 정상 identity의 token을 정확한 위치에서 복사하는지 확인한다. 이 검사는 명시적 응답 fixture이며 RTL 대신 수행한 통합 검사로 주장하지 않는다.

SPI pin 시험58건은 E0/E2/E1/E9/E8/D0/D2/D3의 CRC·byte 순서, 전송 중 live identity 변경에도 이전 응답 유지, consumed/fault/plan/retired 변화의 IRQ와 accepted-only 무깨움, reset을 검사한다. 실제 통합 fault 시험은 partial E1 STOP, 조기 최종 ACK, 독립 expected 변조, physical ROM pending STOP/drain, actual consumed CRC 변조, early expected 저장 중 STOP을 포함한다. phase1024B·queue1024B·staging4096B freeze와 completion 비노출, aperture pingpong/3418B/wrong-token/partial STOP도 유지한다.

## 실패 증거와 범위

window01/board01은 생성된 SPI 코드의 else 위치 문법 오류다. window02는 E0를25B로 바꾸고 queue의26B 길이 검사를 남겨 fault가 발생했다. 두 오류를 실제 생성 코드에서 고쳤다. window03/board03은 정상 일정이 통과했지만 검토에서 IRQ key의 fault bit 누락을 발견했다. fixed01은 이 수정 전에 진행 중이던 시험을 명시적으로 중단했다. fault bit를 복구한 최종 후보는 별도 window04/fixed02/board04에 보존한다. 중간 후보의141개 절감을 최종 수치로 쓰지 않는다.

identity01은 시험 hook이 E1 전송 실패를 반환하지 않아 뒤따른 drain을 예상하지 못한 fixture 오류이며, 실제 E1을 관측한 뒤 실패를 반환하도록 고친 identity02를 사용한다. 모든 실패와 중간 로그는 보존한다. 라이선스 문제로 분류하지 않는다.

전체 Quartus Lite MAP을 사용하고 부모 inclusive 비용과 자식 own 비용을 더하지 않는다. FIT/STA,71프레임 전체 ARMIRQ/fullRUN, 새65816 실행, 실제 MCU cycle 및 실물60fps는 이번 검증 범위가 아니다. production227/GBC164/saveSRAM은 변경하지 않는다.

## 확정 측정과 판정

|warm907 일정|330 ms|331 ms|차이 ms|
|---|---:|---:|---:|
|고정 시작/ROM 위상|25.726373098|25.642783192|-0.083589906|
|제한 연속|17.882967220|17.849467622|-0.033499598|
|정상 연속|14.130784974|14.098785358|-0.031999616|

제한 warm 시작 261.480089ms(330 대비-0.050091), ROM 수락 274.905042ms, 절대 완료 279.329603ms(-0.083589)다. duration 개선-0.033499598ms와 절대 완료 개선을 구분한다. 60Hz 초과는 **1.216300553 → 1.182800955ms**다.

|cold 일정/프레임|330 대비 공동 변경 µs|ARM 준비만 µs|328 기준 대비 공동 변경 µs|
|---|---:|---:|---:|
|고정/905|-37.318|미실행|-30.863|
|고정/906|-50.090|미실행|-44.045|
|제한/905|-37.318|+0.000|-30.863|
|제한/906|-12.773|+0.000|-13.182|
|정상/905|-52.454|+0.000|-13.409|
|정상/906|-96.499|+0.000|-54.590|

ARM-only와 공동 후보는 연속 시작 시각도 달라질 수 있다. 위 차이를 고정 위상의 순수 RTL 지연으로 부르지 않는다. warm의 ARM-only/추가 공동 변경 차이는 다음과 같다.

|warm 일정|ARM-only Δ ms|공동 변경 추가 duration Δ ms|공동 변경 추가 절대 완료 Δ ms|
|---|---:|---:|---:|
|window01|+0.000000000|-0.033499598|-0.083589000|
|normal01|+0.000000000|-0.031999616|-0.180952000|

ARM 준비만 바꾼 두 대조군의6프레임은 모두 완료 시각과duration이330과같았다. 줄어든 명령을그대로시간절감으로환산하지않는다. 정상warm ARM-only는SPI가14B늘었고,공동후보는330보다10B늘었지만전체시간은32µs개선됐다. 이번시간이득은응답길이·공통완료검사·plan cache 유지까지함께바꾼묶음에서확인한것이다.

전체 Lite는 **22,563LE/17,673comb/9,100FF/307,808RAM bits**다. 기준대비 −54LE/−129comb/+79FF/0RAM이다. 조합 논리 부족은 **2,394 → 2,265**로5.39% 줄었다. SPI own comb697→566(−131)이 주된 변화이며 host2411→2407,validator1015→1013 등 합성의 다른 변화까지 전체합계에 포함한다. 변경하지 않은 블록의 매핑 차이를 별도 구현 절감으로 주장하지 않는다.

ARM 공동 ELF text29,958B/BSS47,404B/data0,관측stack1288B다.330 대비text-132B/BSS0B/stack-16B이며,준비만 바꾼 ELF는text30,130/BSS47,404B다. 시험 ELF 비용이고 production SRAM/최악 stack 증명은 아니다. 세 공동 일정 PT_LOAD 및 두 ARM-only 일정 PT_LOAD의 일치를 검증했다.

|일정|3프레임 SPI B|SysTick/EXTI|관측stack B|
|---|---:|---:|---:|
|window04|21787|27/71|1288|
|fixed02|21787|36/68|1288|
|normal01|21423|18/62|1288|
|arm-window01|21819|27/71|1304|
|arm-normal01|21441|18/62|1304|

제한 warm ARM 명령713,467(330 대비-5,983), SPI1,105B(-18)다. E0 4회/E2 23회다. 긴 응답을 모든 poll에 붙이지 않고 E0 자체를1B 줄이며 checked plan cache를 유지한 효과까지 실제 일정에 포함했다.

정상 warm의 SPI는330 대비+10B다. 전체 시간 개선을 모든 일정의 전송량 감소로 설명하지 않는다. 제한 cold905/906의prepare_map330 호출은112→7/400→25, 포함 명령은7504→469/13200→825다. 이 값은 ARM 준비와 응답 제어를 함께 바꾼 관측이며 단독 준비의 성능 효과는 위ARM-only 대조군으로 판정한다.

첫 map E1은85B이고 직전 ARM 실행 묶음은38,020명령이다. 이 묶음은 map 생산·후속 ordinary 준비·serializer를 포함할 수 있으므로 순수map scan 비용이나 그대로 제거 가능한 지연으로 계산하지 않는다. 후속 검토는 실제 첫map 발행 경계와 ordinary 준비 순서를 계측해야 한다.

ROM 수락 후4.424561ms 중 마지막tile→첫map은0.953867ms, 마지막소비→완료는0.351640ms다. 현재 일정을 고정하고 tail 전체를 무료로 가정해도0.831160955ms가 남는다.329의수락후3.180ms 설계상한까지는1.244561ms 더 줄여야 한다. 단순히 마지막 검사만 줄여서는 목표에 도달하지 않는다.

**판정:**331은 실제 응답 제어를 교체한 시간·회로 공동 개선 후보로 보존한다. 남은1.182800955ms와2,265comb 때문에60fps·보드수용 목표는 미달이다. 다음 교체의 범위는 여전히 host/validator의 실제 manifest·receipt RAM 실행/완료와 source/plan decode 소유권이며,이번에 남긴 FSM·계수를 이미 삭제한 것으로 예산에 반영하지 않는다. 분석에380개 hash를 결합했다.
