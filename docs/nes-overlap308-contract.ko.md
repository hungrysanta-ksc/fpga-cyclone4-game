# NES308 — ROM 대기 중 메타데이터와 공동 실행 제어의 교체 경계

## 판단

**manifest만 앞당기는 후보는 충분한 시간 개선 근거가 없다. map·일반 명령의 준비/전송까지 포함한 보관과 실행의 분리는 검토할 가치가 있지만, 기존 4-slot queue 위에 별도 보관기를 추가하는 방식은 채택하지 않는다.** queue 저장 방식과 host·validator 실행 소유권을 함께 대체해야 한다.

이번 단계는 307의 실제 ARM·IRQ·ROM 로그와 whole Quartus Lite 결과를 다시 분석한 구조 검토다. 새 ARM 실행·RTL 구현·MAP/FIT/STA 결과가 아니다. 따라서 실측 기준은 제한907 **17.616924958ms**, **17583comb/2175 부족**으로 변하지 않는다. 후보 시간과 면적은 null이다. 307의 부분 개선과 실패를 보존하며 제품 후보로 승격하지 않는다.

## 실제 일정에서 겹칠 수 있는 부분

307 제한907의 BG plan은271.124269ms, 첫 ROM miss 승인은274.905042ms다. 사이3.780773ms에 기존 OBJ planner slice와 E9/E2가 이미 실행된다. 마지막 승인 전 SPI 종료는271.935888ms다. 이후 약2.969154ms의 SPI 미사용 구간이 있지만, 이것을 곧바로 사용 가능한 CPU/metadata 준비 시간으로 간주하지 않는다. 현재 로그는 `video.valid`, `resident.prepared`, `dirty.prepared`가 동시에 확정되는 시각을 기록하지 않는다.

`prepare289`는 이 세 조건과 source COMMITTED·serial/generation/target 일치를 요구한다. 실제 planner는 마지막 단계에서 patch·palette·resident 사용 비트와 dirty 상태를 마무리한다. BG 완료 표식만 보고 전체 manifest/OAM이 확정됐다고 판단하면 안 된다. 기존 `work302`가 수행한 OBJ 계산을 새 이득으로 다시 세지도 않는다.

|후보|실제307 로그에서 확인한 비용|구조 판단|
|---|---|---|
|ARM 메타데이터 사전 준비만|manifest 두 전송 직전 instruction 구간 합6255, CPI1/84MHz 환산0.074464ms|구간에는 encoding 이외 작업도 포함. 전부 이동 가능한 함수 비용이 아님. 최소 위험의 첫 분리 실험이나 단독 목표 해결 근거 없음|
|requirements+map manifest 선행 전송|64+42=106 SPI B, 2.625Mbit/s wire0.323048ms|위 CPU 구간까지 모두 사라진다는 고정 일정 가정도0.397512ms, 초과 중0.552746ms 남음. 재일정의 절감 상한/불가능성 증명은 아님|
|map·일반 명령·manifest를 함께 선행 보관|9 packets, SPI414B/packet387B, wire1.261714ms; 직전 CPU 구간0.805726ms|범위상0.950ms를 다룰 만하지만 준비 시각·credit·RAM·DMA 의존성을 아직 검증하지 못함. 두 점유량을 실제 net gain으로 합산하지 않음|

마지막 일반 E1 종료279.213539ms부터 최종 완료280.265546ms까지1.052007ms다. 이 전부를 없애는 가정조차 여유가0.101749ms에 불과하고, 실제로는 미완료 DMA·독립 검사·최종 ACK가 포함되어 제거할 수 없다. 정책 여유0.25ms까지 달성하려면 마지막 manifest 구간 밖의 경로도 개선해야 한다. 모든 수치는 고정된307 추적에 대한 진단이며 ROM 위상 변화나 VBlank를 포함한 새 일정의 예측값이 아니다.

## 현재 경로에서 단순 순서 변경이 실패하는 이유

- host는 manifest 시작 뒤10/11/3 이외 명령을 거부한다. validator는 requirements를 받으면서 이미 소비된 receipt와 비교한다. op15를 BG DMA보다 먼저 실행하면 이후 정상 DMA가 거부되거나 미완료 coverage로 실패한다.
- queue RAM 주소는 NORMAL의 SNES, validator 실행 cursor, host parser 중 하나가 소유한다. 대기 manifest를 head에 고정하고 뒤의 tile packet을 읽으려면 새 head 선택과 lifetime 규칙이 필요하다.
- 907의 후보 packet bytes387B는1024B보다 작지만 **9개 packet은4개 고정 slot에 들어가지 않는다.** 바이트 용량만 보고 무료 보관이라고 할 수 없다. manifest 두 slot을 붙들어도 DMA용 slot은 두 개로 줄어든다. raw fallback은 requirements206B와 raw map 두 packet256+32B로 세 slot을 쓴다.
- phase RAM에서 보수적으로 예약한 live 범위는 [0,166),[256,422),[448,512),[512,678),[680,716),[768,1024)다. 주소 공백170B에 전체 display24+requirements166+map256=446B를 펼쳐 넣을 수 없으며276B 부족하다. 공백도 포트와 초기화/STOP 안전성을 입증한 사용 가능 RAM이라는 뜻은 아니다. 입력 source scratch를 output receipt/map과 동시에 재사용할 수 없다.
- OAM/CGRAM은 물리 PPU 자원이므로 수신/준비를 앞당기는 것과 PPU DMA 실행을 앞당기는 것은 다르다. WRAM HDMA 보관도 bank lease와 최종 표시 시점까지 유효해야 한다.

## 다음 후보의 구체적 교체 계약

첫 실험은 새 저장 장치 없이 ARM 준비 시각을 계측하고, 준비가 끝난 이후에만 bounded packing을 수행하는 분리 후보다. SPI 재귀 호출을 `work302` 안에 넣지 않는다. writable/unknown plan credit·DMA ready·IRQ가 나타나면 다음 slice 전에 즉시 기존 공급 경로로 돌아간다. 실제 순서/최종 ACK가 같은지 확인하고 비용을 측정한다.

전송까지 겹치는 공동 후보는 다음 범위를 **하나의 교체**로 취급한다.

|삭제할 기존 제어|대체 계약과 유지할 검사|
|---|---|
|고정 slot의 implicit head lifetime + 별도로 추가할 metadata 보관 FIFO|기존1024B queue 저장소의 bounded byte arena와 record table. slot/byte credit을 명시하고 최소 하나의 최대256B tile/실행 packet 진행 공간을 확보. 4credit 의미를 변경하면 기존 retired counter로 조용히 대체하지 않고 새 프로토콜·wrap 검증을 포함|
|host HREAD/HCAP와 payload parser, validator E_READ/E_CAP의 따로 유지되는 queue 주소 선택|단일 reader와 immutable active record. admission은 원본 bytes/CRC/identity/bounds를 검사하고 reader는 준비·실행을 구분. typed range/encoded/expanded cursor의 서로 다른 의미를 지우지 않음|
|host XBEGIN/XWAIT→CONSUME/retire와 validator executing/complete의 중복 완료 해석|record가 receive→stored→eligible→consumed→retired 상태를 소유. receipt commit과 마지막 RAM write 이후에만 consumed. completion relay를 상태 비트로 옮기기만 하는303 재시도는 제외|
|수신 즉시 manifest_phase가 terminal로 바뀌는 결합|수신은 원본 encoded bytes를 보관만 하고, 실행 fence에서 독립 coverage/CRC/manifest 검사를 수행. 일반 DMA가 끝나기 전에 sealed/display-ready가 되지 않음|
|별도 SPI/plan 진행 문맥과 위 구조의 중복 상태|307 공통 CRC/close 검사를 유지하고 실제로 중복된 byte/count/응답 제어만 삭제. plan의 NES clock CDC와 accepted/chunk/generation 소유권은 유지|

예상되는 새 record table·queue allocator·원본 보관 수명·예약 credit·읽기 포트 mux 비용을 모두 경계에 포함한다. 9개 record/387B는907 관측일 뿐 최대 프레임의 상한이 아니다. cold/raw fallback은 capacity에 도달하면 기존 refill로 진행하고, 보관된 manifest 때문에 DMA가 막히는 순환 대기는 금지한다. packet queue credit 반환과 실제 DMA receipt/final ACK를 분리하더라도 후자를 전자로 대체하지 않는다. 기존 four-credit 프로토콜을 유지하는 첫 실험과 credit 의미를 바꾸는 공동 후보를 섞어 성공으로 보고하지 않는다.

STOP은 수신·stored·reader handoff·DMA 중·receipt 직전·manifest 검사 중·표시 전 각각에서 모든 pending record/lease를 무효화하고 RAM write를 차단해야 한다. 취소 후 동일 bank/새 generation/token 재사용, 오래된 IRQ/credit 응답, 부족/중복 receipt, 손상된 CRC/codec/범위가 성공으로 바뀌지 않아야 한다. 최종12 display reads와 ACK, 실제 PPU DMA의 VBlank 및 최종 bank 전환 조건은 유지한다.

## whole Lite 예산과 진행 기준

307 own-cost는 host2093+validator1251+queue118+SPI713+plan506+glue49=4730comb, 경계 밖12853comb다. host를 완전히0으로 만들어도82comb 부족한다. host+validator3344만 바꾸고 나머지를 그대로 두면 둘의 합을1169 이하,128 여유까지 두면1041 이하로 줄여야 한다. 따라서 작은 host FSM 교체나 별도 staging 추가만으로 충분하다는 근거가 없다.

|공동 기능 예산|comb 상한|
|---|---:|
|admission·record·DMA ownership|700|
|독립 validator·CRC·manifest·display|900|
|queue 저장/credit·SPI ingress/응답|450|
|plan transport|328|
|glue|49|
|기능 합계|2427|
|정책 여유|128|
|경계 hard cap|2555|

이는 합성 예상치가 아닌 요구 상한이다. 새 allocator/보관/제어가 이 안에 들어갈 근거가 없으면 후보를 구현 성공으로 간주하지 않는다. outside 역시 새 whole MAP에서 재측정한다. 요구는 최소2175comb/0.950258ms 순감소, 정책 여유 포함2303comb/1.200258ms다. FF 감소와 inclusive hierarchy 중복 합산으로 비용을 맞추지 않는다.

검증 순서는 준비 시각과 실제 명령 비용 계측 → ARM-only 동일 byte/순서 비교 → bounded 공동 저장/실행 후보와 STOP/credit/port/독립 검사 → 정상·제한905~907 및 원본71 producer → 같은 소스의 whole Quartus Lite MAP이다. queue allocator만 합성하거나 ROM 위상을 바꿔 반복하는 단계는 두지 않는다. 새 일정은 ROM 허용 구간·core 우선권·VBlank를 그대로 쓰며 이전 프레임 시작 변화도 과금한다. 새 저장 구조가 충분히 작다는 근거가 나오기 전 FIT/STA를 반복하지 않는다.

`tools/analyze_nes_overlap308.py`는307의453개 입력 SHA를 재검증하고 이번 비용·의존 관계·주소 예산을 고정한다. 최초 분석은 tx가 빈 checkpoint/WFI event를 E1처럼 읽어 IndexError가 났으며, 빈 event를 건너뛰도록 수정했다. 입력 추적이나 제품 검사를 바꾸지 않았다. 새 하드웨어 검증 수는0이다. fullRUN/live65816/whole71 live/실물60fps는 미검증이고 production227/GBC164/saveSRAM은 그대로다.
