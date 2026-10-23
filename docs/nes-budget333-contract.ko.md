# NES333 tile·ordinary 공급과 공동 실행 제어 교체 예산

NES332를 유지한 채 다음 구현의 삭제 범위와 합격 예산을 확정한다. 332의 실제 ARM/SPI/IRQ/2슬롯 일정 9개와 whole Quartus Lite 보고서를 hash로 다시 결합했다. **이번 단계는 재분석·설계이며 새 RTL/ARM 실행, 합성 또는 추가 성능 개선은 없다.** 근거는 `analysis/budget333-verification.json`, 재현 도구는 `tools/analyze_nes_budget333.py`다.

## 결론과 비교 기준

현재 제한 ROM warm907은 **17.727787264ms**, 60Hz 초과 **1.061120597ms**다. whole Lite는 **22539LE / 17649comb / 9097FF / 307808bits**, 조합 논리 부족은 **2241개**다. 선택 범위는 **ARM의 중단 가능한 H2·ordinary 준비 + host descriptor/receipt 실행 소유권 + NES-clock source/plan 실행 소유권 + host ingress 완료 제어**다. 단순 cursor 공유, 남은 final tail만 단축, source/plan만 교체하는 안은 목표 폐쇄안으로 선택하지 않는다.

|비교안|시간 측면|회로 측면|판정|
|---|---|---|---|
|ARM 공급만 변경|H2·ordinary 준비를 ROM/DMA 대기와 겹칠 후보|RTL이 같으면2241comb 부족 유지|ARM 효과를 분리하는 대조군|
|host·validator만 교체|receipt·final 완료 지연 감소 후보|3401comb에서2241개, 약65.89%를 줄여야 함|이 경계 하나로 해결된다고 가정하지 않음|
|source·plan만 교체|source 준비·plan 공급 개선 후보|합계2231comb을 전부 없애도10개 부족|단독 목표 폐쇄 불가|
|전체 공동 교체|수락 후4.293335→3.180ms 예산|6483→4110comb 예산|다음 구현 범위; 달성 여부 미검증|

## 실제 일정에서 확인한 병목

|warm907 일정|전체 ms|첫 BG ROM 요청→수락 ms|수락 후 완료 ms|
|---|---:|---:|---:|
|제한 연속 window03|17.727787264|5.004213|4.293335|
|동일 시작·ROM 위상 fixed02|25.511557494|12.785256|4.293608|
|정상 연속 normal01|13.967514206|0|5.537275|

제한 연속의 앞선 ROM 허용 구간은 source 시작보다 **1.693480ms 먼저 닫혔다**. 동일 프레임 plan을 조금 빨리 만드는 것만으로 그 구간을 잡을 수 없다. 반면 고정 위상에서는 앞선 구간이 source 시작 후6.089654ms에 닫히며, 실제 요청은 약2.343ms 늦다. 두 경우를 구분한다. 허용 구간 경계는 모니터링의 ±1 NES clock 불확실성이 있고, 제한 TB의 경쟁 모델이며 실제 보드 WCET가 아니다. 이전 프레임의 미확정 tile을 무료로 미리 읽거나 ROM 허용 구간을 넓히는 가정은 예산에 넣지 않는다.

제한 warm의 마지막 OBJ **첫 출력 바이트**는275.304628ms, OBJ bulk E1 완료는276.385652ms, 마지막 tile 소비는276.453625ms다. 첫 바이트→bulk 완료1.081024ms와 bulk 완료→소비0.067973ms가 보인다. 첫 바이트는 완성된 tile 준비 시각이 아니므로 전자를 전부 ARM 지연 또는 회수 가능한 시간으로 세지 않는다. 다음 실행에서는 last-byte-ready, staging seal, ARM bulk-ready, E1 시작, DMA 시작을 각각 찍는다.

`prepare289()` 반환→최종 `tiles290(1)` 진입 사이에 **21,186명령 / 0.252214286ms**가 있다. 그 호출 경로에는 `h2(seal289)`와 caller 검사가 있으며, H2는 이미 보낸 certificate와 비교하기 위해 의미 검사·CRC를 다시 계산한다. 이 값은 호출 경계의 비용이지 h2만의 PC profile은 아니다. 첫 ordinary OAM E1 직전 묶음은 **35,704명령 / CPI1 0.425047619ms**다. `oam227→span_cost227→span_piece/repeat_bytes`, 이후 `span`의 dry-run/발행 재탐색이 구체적 검토 대상이다. 두 묶음을 모두 무료로 만든다는 낙관적 산술에서도 **0.383858693ms**가 남는다. nested `tiles290/span/bulk289` 비용을 더하거나 이를 실측 개선으로 부르지 않는다.

## 시간 예산과 ARM 교체

구간은 서로 겹치지 않는 실제 소비 경계로 나눈다. CPU 명령, SPI와 DMA 시간을 이 표에 다시 더하지 않는다.

|제한 warm 구간|332 ms|다음 상한 ms|변화 요구 ms|
|---|---:|---:|---:|
|첫 ROM 수락→마지막 tile 소비|1.548583|0.900|-0.648583|
|마지막 tile→첫 map 소비|0.569011|0.400|-0.169011|
|첫 map→마지막 map 소비|0.277720|0.280|+0.002280 허용|
|마지막 map→마지막 ordinary 소비|1.556091|1.300|-0.256091|
|마지막 소비→최종 완료|0.341930|0.300|-0.041930|
|합계|4.293335|3.180|-1.113335|

다른 구간이 같을 때만 전체 **16.614452264ms / 여유0.052214403ms**가 된다. 이는 합격 예산이며 예상 실측값이 아니다. final tail을 전부 없애도0.719190597ms가 남는다. 고정 위상에 수락 후3.180ms만 적용하면 여전히 **24.397949494ms**다. 따라서 이 예산은 모든 ROM 위상의60fps 증명이 아니며, 고정 위상에서는 source/plan 요청을 앞당기는 별도 증거가 필요하다.

ARM은 기존 압축 wire와 tile 선행 생산을 유지한다. `work302()`의 준비 작업에 H2 재검사와 ordinary 비용 산정을 작은 단계로 넣고, 실제 DMA-ready/credit/IRQ 및 필요한 plan 공급을 먼저 처리한다. 현재 최대2회 E9 공급을 먼저 시도하는 `io259()` 경로도 DMA 준비 상태와 함께 우선순위를 검토한다. plan 공급을 굶기거나 SPI 재진입을 만드는 변경은 금지한다. E9 BG 완료와 프레임 종료의 구분도 유지한다. 준비 작업의 자격은 material 확정 및 lease 유효성으로 따로 정의한다. 현재의 `work_pending302()` 하나에 종속시키면 plan이 끝난 뒤 H2/ordinary 준비가 실행되지 않을 수 있다. `frame259()`의 IRQ 종료 시점도 모든 준비·공급을 끝낸 뒤로 옮길 수 있는지 검증하며, IRQ를 무조건 켜거나 기존 wait를 중첩하지 않는다.

H2 검사는 early certificate를 믿고 없애지 않는다. 입력 COMMITTED 및 video/patch/sizes의 최종 불변성이 성립한 뒤 의미·CRC 검사를 진행하고 기존 certificate와 비교한다. generation/serial/bank/epoch와 material 버전에 묶인 완료 상태가 있어야 마지막 synchronous 재계산을 대체할 수 있다. STOP·내용 변경·재시작이면 무효화한다. 불변성 증거가 없으면 기존 최종 검사를 유지하되 단계별 실행만 허용한다. OAM 전체544B와 packed high32B 구분, hidden-tail 비교와 압축 비용 선택도 유지한다. `span_cost227`의471 상수는 과거 wire 비교값이므로 현재 응답·IRQ 비용의 실측치로 사용하지 않는다.

추가 ARM 상태는 **최대32B**(H2 continuation≤16B, ordinary 선택·진행≤16B)를 설계 예산으로 둔다. payload 복사본은0B, metadata/first-map scratch의 동시 재사용도0B다. 기존 wire259는 송신 소유권이 반환된 뒤에만 작성한다. 모든 OAM/span 분할 목록을 저장할 공간이 있다는 가정을 하지 않는다. 정해진 상태로 표현할 수 없으면 큰 cache를 붙이기 전에 전체 비용과 범위를 다시 설계한다. BSS 상한47436B, 관측 stack 상한1288B는 **시험 ELF 기준**이며 제품 RAM 승인과 다르다. 준비 slice의 목표는 IRQ가 준비됐을 때 다음 service까지 CPI1 환산10µs 이하이며, 이를840명령 예산으로 계측한다. 비교·CRC 일부를 없애서 맞추는 예산이 아니다. wire-format 변경은 첫 후보에서0B, 추가 상태응답도0회를 예산으로 둔다. 현 warm1077B/E1 15회/E9 4회와 cold 전체 전송을 기준으로 실제 증감을 다시 재며, 추가 전송을 무료로 처리하지 않는다.

## 실제 삭제 범위와 클록·RAM 소유권

|영역|삭제·대체할 기존 실행 제어|유지할 검사·별도 상태|새 비용을 포함할 위치|
|---|---|---|---|
|host descriptor·receipt|host의 CHECK/DCHECK 뒤 분산된 destination/receipt 주소 선택, WAIT_RECEIPT→SEND→XWAIT298 왕복, host와 validator의 범위 진행·완료 제어를 하나의 host-clock 실행 상태로 대체|descriptor domain/길이/overflow 검사, 실제 SNES read count·순서·token, receipt 중복/누락, CRC 및 독립 expected scan|host+validator 상한2100 안에 admission record·RAM address mux·완료 상태 전부 포함|
|ordinary·manifest 실행|PREAD/PCAP/PUT와 metadata read/capture/write의 공통 queue-read 진행 및 terminal retire 제어를 통합|325의 단일 압축 확장,332의166/256 write-before-bound 검사, expected 내용과 실제 receipt 분리|동일 host 실행기; 별도 새 reader를 옆에 추가하지 않음|
|queue·SPI|host가 통합한 admission/완료 사실을 재해석하는 제어와 응답 선택을 대체|2슬롯 저장 credit, 소비 완료 순서, 불변 snapshot/CRC8, SPI 프레이밍, IRQ 발생/확인|queue+SPI 상한600 안에 CDC 및 event/snapshot 저장 포함|
|NES source·plan|source REQUEST/SREAD/SBYTE와 transport record-open/CRC 완료 제어를 core 실행 상태에 결합; 입력 은퇴 뒤 plan WAIT/READ/CAPTURE/CHECK와 같은 NES-clock byte 진행 상태 사용|query 선행 읽기, source/base CRC·row 선택, block publish/POP/D5 ACK, plan shape/lease/generation, BG 종료/최종 EA, ROM drain|source1100+plan310에 새 phase 전환·decode/address mux 포함|

332의 active record와319의 source/plan cursor 공유는 이미 구현되어 있다. 이를 다시 절감으로 세지 않는다. 위 이름의 상태를 지우는 것만으로 LUT가 그만큼 줄어든다고 가정하지 않으며, 실제 쓰이지 않는 legacy 포트/상수 신호 삭제에도 이미 합성으로 제거된 면적을 배정하지 않는다. host의 `v_all_consumed=1`도 독립 소비 증거로 쓰지 않는다. 소비 완료는 실제 bus read와 ordered receipt/ACK 경로로 증명한다.

host-clock 실행 순서는 admission→queue READ/CAPTURE→staging PUT/EXPAND→실제 DMA read→phase RAM receipt READ/WRITE→소비 event다. 한 개의 실행 cursor는 마지막 receipt write와 CRC 완료까지 재사용하지 않는다. incoming queue 저장 credit은 해당 payload의 마지막 사용 뒤 따로 반환하고, 실제 소비 credit과 섞지 않는다. 다음 head의 admission과 현재 receipt가 겹치면 기존 pending 저장 또는 명시적 backpressure로 처리하며 이를 무상 병렬성으로 세지 않는다.

phase RAM A는 NES clock source 소유, B는 host clock validator/공동 실행기 소유다. queue RAM은 ingress 저장 포트와 parser/expected 포트를 유지한다. final scan은 queue의 expected 포트와 phase B를 함께 예약한다. staging의 NES tile 생산→host 전달 및 SNES 실제 read 경로는 기존 ping-pong/CDC를 유지한다. **host와 NES FSM을 하나의 물리 FSM으로 합치지 않는다.**

NES 실행 소유권 전환은 마지막 source byte 발행→CRC 반영→immutable block publish→host POP 및 D5/input ACK→transport empty·미완료 query/write 없음→plan read다. `source_empty`만으로 물리 ROM 요청까지 없어졌다고 보지 않는다. source용 phase scratch,512B transport RAM,1024B plan payload RAM은 당장 합치지 않는다. 서로 다른 클록의 bank publish/retire mailbox와 queued plan을 유지한다. STOP은 두 클록의 write/seal/receipt/ACK를 막고 pending physical ROM 응답을 drain한 뒤에만 다음 lease를 허용한다. 12개 표시 read·정확한 token·VBlank 뒤 최종 ACK 조건을 유지한다.

## whole Quartus Lite 회로 예산

자식 포함 parent 수치가 아니라 entity **own comb**를 중복 없이 합산했다. source는 encoder+source transport subtree, plan은 wrapper own+plan batch subtree+plan SPI own이다. tile ROM backend 및 기타 바깥 회로는11,166comb에 남아 있으므로 공짜로 삭제하지 않는다.

|영역|332 comb|다음 상한|필요 순감소|
|---|---:|---:|---:|
|host+validator|3401|2100|1301|
|queue+SPI|851|600|251|
|source|1771|1100|671|
|plan|460|310|150|
|교체 범위 합계|6483|4110|2373|
|밖의 회로|11166|11166|0|
|whole|17649|15276|2373|

2241comb 부족을 없애려면 교체 범위는 최대4242comb이어야 한다. 목표4110은132comb의 산술 여유를 둔 것이며, 약36.60%의 순감소가 필요하다. 기존329 상한을332 실측에 재기준화한 **합격 요구조건**이지 달성 가능성이 입증된 세부 합성 견적이 아니다. 새 decoder, arbiter, handshake, scratch/state를 모두 상한 안에 넣는다. 변경 밖의 mapping 변동도 whole 결과에 반영하고, 이를 명시적으로 없앤 회로의 절감으로 따로 더하지 않는다. 추가 RAM/M9K는0, RAM bits≤307808, FF≤9097을 비교 예산으로 둔다. FF 증가가 필요하면 comb만 성공으로 보고 채택하지 말고 전체 tradeoff를 다시 기록한다. MAP 성공과15408comb 이하만으로 FIT/LAB/배선/STA가 통과한 것은 아니다.

## 다음 구현의 검증 순서와 중단 기준

1. 332 RTL에 ARM 준비/우선순위 변경만 연결한다. H2/ordinary 구간을 decode·검사·emit으로 계측하고 last tile-byte/staging seal/E1/DMA 시각을 추가한다. 고정 시작/ROM cycle과 연속 제한·정상905/906/907을 각각 비교한다. 전송된 명령·payload·E9 순서는 유지하는 안부터 검증한다. 신규 응답·IRQ·cold 준비 비용을 전부 포함한다.
2. host descriptor/receipt/queue reader와 NES source/plan의 두 실행 소유권을 실제로 대체한다. 코드상 기존 상태·주소·완료 경로가 사라지는 삭제 목록을 먼저 확인한다. whole Lite 단일 구조 후보의 순비용을 측정한다. 작은 FSM/cursor 교체가 예산에 못 미치면 seed/FIT 반복 대신 역할·ABI 변경을 다시 비교한다.
3. ARM-only, RTL-only, 공동 후보를 동일 시작·ROM 위상으로 대조하고 연속 실행에서도 순개선을 확인한다. 71 producer byte/token 비교와 최종15일정·11 RTL faults·raw0 7건·aperture를 새 입력 hash에 재결합한다. 이전 PASS를 새 RTL의 PASS로 재사용하지 않는다. shared cursor overlap, receipt RMW 중 STOP, source→plan 전환의 outstanding write/CRC/POP, 지연 ROM 응답,2슬롯 full+early manifest,IRQ와credit 동시 도착,material 변경 후 H2 완료표식 재사용을 추가 검증한다.

새 65816 ABI가 같으면325의536B 실제 bus trace 재사용임을 명시한다. ABI/DMA handshake를 바꾸면 실제65816 실행을 다시 수행한다. cold·normal 회귀를 warm 개선으로 숨기지 않고, 모든 비용이 두 목표를 동시에 개선한 경우에만 다음 후보로 남긴다. 수락 후3.180ms와whole15276comb의 실제 동시 달성, 고정 ROM 위상의 미해결 요청 지연, 전체71프레임 ARM/IRQ/fullRUN, FIT/STA, 실물 sustained60fps는 별도 미완료 항목이다. production227/GBC164/saveSRAM은 변경하지 않는다.
