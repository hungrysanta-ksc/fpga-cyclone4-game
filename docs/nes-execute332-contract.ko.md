# NES332 첫 map 발행과 최종 RAM 실행기

기준은 NES331이다. 제한 ROM warm907은17.849467622ms, 60Hz 초과1.182800955ms이며 전체 Lite는22563LE/17673comb/9100FF/307808bits, 조합 논리 부족2265개다. 이번 작업은 같은 PR131에서 진행한다.

## 구현 범위와 유지하는 증거

ARM `map247()`이 끝난 직후 `publish_map332()`을 호출한다. 확인된 저장 queue가 비어 있으면 기존 batch를 발행하고, 진행 중인 일이 있으면 ordinary 준비를 계속해 기존 dispatch 시점에 발행한다. 추가 status 읽기는 없다. 기존에는 다음 ordinary packet이 `dispatch289()`에 도착해야 flush되므로, palette 추출·OAM 비용 비교 등의 준비가 첫 map DMA 시작을 막을 수 있었다. batch cut·압축 방식·token 배정·2슬롯 credit 검사·송신 실패 후 재시도 금지는 유지한다. 발행 실패면 뒤의 ordinary 준비로 진행하지 않는다. 선행 metadata와 tile 생산도 유지한다.

host는 SEAL head를 소유한 채 최종 RAM 작업을 한 번 시작하고 sealed를 기다린다. 검증기가 자신의 expected cursor로 queue port B를 읽으며 display24B→requirements166B→map256B를 독립 검사하고, retained hash digest→H2 certificate→seal까지 진행한다. host의 바이트 중계 및 hash/certificate/finish 왕복 상태를 삭제했다. validator의 receipt RMW·CRC·실제 소비 검사, source/plan FSM은 남는다. 저장 credit 반환과 실제 소비 완료도 여전히 구분한다.

expected RAM 배치는 map0..255, requirements256..421, display448..471이다. 기존 queue RAM1024B의 두 packet slot480/752는 그대로다. 새 RAM/포트/expected 복사본은 없다. 정렬된 주소의 bit 연결이 기존24/190 오프셋 덧셈을 대체한다. producer와 validator는 별도의 진행 정보와 값을 사용하며, 실제 receipt/CRC와 expected가 같아야 한다. `v_all_consumed` 상위 연결은 기존과 같이 상수이고, 실제 소비 순서의 보장은 host head/receipt/ordered consume 경로에 있다. 이를 새 독립 소비 증명으로 설명하지 않는다.

write 전에 manifest cursor가 requirements166/map256 미만인지 직접 검사한다. 기존 덧셈 후의 canonical 상한 검사를 그대로 없애면 literal map256 이후가0으로 접힐 수 있다는 검토 결과를 반영했다. 경계 오류에서는 RAM write 자체를 막는다. display는 parser의17..40 구간만 이 경로를 사용한다.

최종 ACK는12개 display read·token·VBlank를 거친 기존 SNES 경로를 유지한다. STOP은 phase/queue/staging RAM write와 seal을 차단하고 physical ROM을 drain해야 한다. 새 RAM scan과 certificate scan 도중 STOP도 별도로 주입한다.

## 시험과 판정 원칙

실제 M4 명령을 실행하는 CPI1/84MHz 모델, SPI/IRQ/2슬롯/ROM/staging 일정과 기존325의 실제65816 bus trace를 사용한다. SNES ABI가 같다는 hash를 확인하며 이번 CPU 실행으로 부르지 않는다. 고정 시작·ROM 위상과 제한/정상 연속 일정을 따로 비교한다. ARM-only 대조군은331 응답 ABI와 RTL을 유지한다. `NES331_ARM_ONLY`로 옛 ABI까지 되돌리지 않는다.

whole Lite MAP의 동일 경계·RAM·FF 비용으로 평가한다. 첫 중계 제거 후보board01은22584LE/17694comb/9097FF/307808bits로331보다21comb 증가했다. 정렬 배치만 넣은board02는17665comb이지만 cursor 경계 보호가 부족하므로 선택하지 않는다. 직접 경계 검사까지 넣은board03은22539LE/17649comb/9097FF/307808bits다. 세 결과는 구조 변경·결함 수정별로 보존한다. seed/FIT 반복은 하지 않는다.

window01/02의 무조건 조기 발행은 cold905에49.318µs 회귀와 cold 각각14B 추가 응답을 만들었다. final window03 이후의 queue-empty 조건과 구분한다. batch02는 이 문제와 경계 검토 후 다음 fixed 실행 전에 명시적으로 중단했고, FLOAT 서버는 wrapper가 정상 정리했다. 라이선스 실패가 아니다.

## 확정 측정과 판정

|warm907 일정|331 ms|332 ms|변화 ms|
|---|---:|---:|---:|
|고정 시작/ROM 위상|25.642783192|25.511557494|-0.131225698|
|제한 연속|17.849467622|17.727787264|-0.121680358|
|정상 연속|14.098785358|13.967514206|-0.131271152|

제한 warm 시작은261.470544ms(331 대비-0.009545)이고 첫 ROM 수락은274.905042ms로 같다. 절대 완료279.198377ms는-0.131226ms, duration은-0.121680358ms다. 시작 위상에 따른 차이를 섞지 않는다. 남은60Hz 초과는1.182800955→**1.061120597ms**다.

|cold 프레임|고정 Δ µs|제한 Δ µs|정상 Δ µs|
|---|---:|---:|---:|
|905|-9.591|-9.591|-10.045|
|906|-9.545|+0.045|-10.045|

|ARM-only 대조군/프레임|ARM 발행 변경 Δ ms|공동 RTL 추가 Δ ms|
|---|---:|---:|
|fixed01/905|+0.000136362|-0.009727156|
|fixed01/906|+0.000136362|-0.009681702|
|fixed01/907|-0.121498542|-0.009727156|
|window01/905|+0.000136362|-0.009727156|
|window01/906|+0.000000000|+0.000045454|
|window01/907|-0.121634904|-0.000045454|

고정 위상은 같은 source 시작 시각과 ROM cycle에서 비교한다. 연속 대조군의 추가 차이는 cold 완료에 따른 다음 프레임 시작 변화도 포함하므로 순수 RTL 지연으로 부르지 않는다. ARM-only는 331 RTL/응답 ABI를 유지하며 최종 공동 후보와 ELF PT_LOAD가 같다.

|전체 Quartus Lite|331|332|변화|
|---|---:|---:|---:|
|LE|22,563|22,539|-24|
|comb|17,673|17,649|-24|
|FF|9,100|9,097|-3|
|RAM_bits|307,808|307,808|+0|

조합 논리 부족은 2,265→**2,241개**다. host 자체는 2,407→2,348(−59), validator는 1,013→1,053(+40), queue는 276→285(+9)로 세 블록 합계는 10comb 줄었다. 전체 −24에는 변경하지 않은 블록의 mapping 변화도 포함한다. 이를 새 구현 절감으로 따로 합산하지 않는다. source/plan FSM, receipt RMW와 host ingress/storage 진행 제어는 남는다.

ARM text는 29,994B(331 대비 +36), BSS는 47,404B, data는 0B, 관측 stack은 1,288B다. 추가 payload buffer나 작업 상태는 없고 BSS/stack은 기준과 같다. 시험 ELF 범위이며 production SRAM·최악 stack 증명은 아니다.

|일정|3프레임 SPI B|SysTick/EXTI|
|---|---:|---:|
|window03|21759|27/70|
|fixed02|21759|36/67|
|normal01|21395|18/61|
|arm-fixed01|21759|36/67|
|arm-window01|21759|27/70|

제한 warm은 ARM 709,316명령(−4,151), SPI 1,077B(−28), E0 4회/E2 21회다. E1의 opcode별 payload, DMA 명령 순서와 E9 plan bytes는 기준과 같다. 저장·소비 credit, token/sequence, metadata 8,570B·receipt 754B·CRC 64B, 최종 표시 검사를 실제 일정에서 통과했다.

첫 map E1은 85B이며 276.976910ms에 완료됐다. 직전 ARM 실행 묶음은 38,020→5,692명령으로 줄었다. ordinary 준비를 뒤로 이동한 효과이므로 전부 삭제된 계산으로 세지 않는다. 최종 warm의 발행 호출은 ordinary 준비보다 앞서고, 이미 queue가 차 있는 cold는 발행을 보류한다. 실제 ARM 제어 시험 8건은 빈 queue, 1·2슬롯 점유, 16비트 wrap, 송신 실패 후 재제출 금지를 확인한다. 이 시험은 명시적 transport fixture를 사용하므로 시간 증거와 구분한다.

마지막 tile→첫 map은 0.569011ms, 마지막 소비→완료는 0.341930ms다. tail 전체를 무료로 가정해도 0.719190597ms가 남는다. ROM 수락 후 시간은 4.293335ms이며, 329의 설계 상한 3.180ms까지는 1.113335ms를 더 줄여야 한다.

|제한 warm 수락 후 구간|332 ms|329 설계상한 ms|추가 감소 필요 ms|
|---|---:|---:|---:|
|ROM_to_last_tile|1.548583|0.900|0.648583|
|tile_to_first_map|0.569011|0.400|0.169011|
|map_span|0.277720|0.280|0.000000|
|last_map_to_last_ordinary|1.556091|1.300|0.256091|
|final_tail|0.341930|0.300|0.041930|

map DMA 구간은 이미0.28ms 상한 안이다. 남은 시간은 tile 공급과 ordinary 준비·전송 구간이 더 크다. 위 상한은 구현 예산이며 동시에 달성된 실측이 아니다.

|회로 그룹|332 own comb|329 설계상한|추가 감소 필요|
|---|---:|---:|---:|
|host_validator|3401|2100|1301|
|queue_SPI|851|600|251|
|source|1771|1100|671|
|plan|460|310|150|

외부 11,166comb이 유지되고 위 상한을 모두 달성한다는 가정의 전체는 15,276comb이다. 이는 예산이며 합성 예측이나 확보된 여유가 아니다. 이번의 작은 scan 교체만으로 남은 회로 부족을 해결할 수 없다.

최종 15일정, ARM 생산 71프레임, 강제 재개 3프레임, 응답 205건, 발행 8건, RTL 오류 주입 11건과 aperture 검사가 통과했다. RTL 시험에는 partial E1 STOP, 조기 최종 ACK, 독립 expected 변조, ROM pending STOP, 실제 소비 CRC 변조, early expected 저장 중 STOP, 새 expected·certificate 순회 중 STOP, display 변조, map256·requirements166 overflow를 포함한다. overflow는write enable 차단과 alias/gap RAM 불변을 추가 확인한다. 세 RAM freeze와 미완료 seal/lease/ACK 비노출을 유지했다. raw0 최종 RAM 작업은 정상 완료, expected·certificate 변조, 조기 ACK, 미소비, 누락 receipt를 포함한 별도 7건의 공개 포트 RTL 시험으로 확인했다. 전체 ARM/ROM/CPU raw0 전환 시험은 아니다.

분석에 689개 hash를 결합했다. 시간은 실제 M4 명령의 CPI1/84MHz·IRQ/SPI/ROM 경쟁 모델이며, SNES는 변경 없는 325의 536B ROM 실제 bus trace를 재사용했다. 새 65816 실행, 71프레임 전체 ARM IRQ/fullRUN, raw0 전환의 새 전체 실행, FIT/STA, 실물 60fps는 미검증이다. production227/GBC164/saveSRAM은 변경하지 않았다.

**판정:** 시간·전체 회로의 작은 공동 개선 후보로 보존한다. 남은 시간과 회로 부족 때문에 제품 채택이나 60fps 완료로 승인하지 않는다.
