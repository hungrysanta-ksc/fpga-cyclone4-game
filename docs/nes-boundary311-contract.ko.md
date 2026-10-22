# NES311 삭제할 교체 경계와 전체 예산

이번 단계는 **교체 계약 확정**이다. 새 ARM/RTL/Quartus 실행이나 달성 가능한 절감량 측정은 하지 않았다. 307의 실제 ARM·IRQ·ROM 일정과 whole Lite를 기준으로, 310의 실패를 반영해 삭제 대상·RAM 포트·완료 소유권·합격 예산을 정했다. 새 후보 시간/면적은 null이며 production 승격은 없다.

## 확정한 설계 경계

기존 raw packet queue → host parser → validator packet decoder를 **공통 admission/record 실행기 + 독립 소비/coverage 검사기**로 대체한다. SPI wire 압축과 map batch는 유지한다. requirements/map manifest는 공통 실행기가 한 번 해석해 정규화된 기대값으로 저장한다. 마지막에는 그 기대값과 실제 receipt/validity를 대조하며 packet/RLE를 다시 해석하지 않는다. ARM의 승인 비트로 독립 검사를 대체하지 않는다.

|현재 구현에서 삭제할 대상|새 소유자·대체 동작|반드시 남길 증명|
|---|---|---|
|queue260의 `buffer[{retired[1:0],sn_address}]`, `lengths[4]`, 4slot full/retire 결합, SNES queue read 인터페이스|같은 1024B RAM 재배치, 2개 record slot, 저장 완료 credit|예약·CRC commit·slot release 각각 정확히 한 번, wrap/과대 credit 거부|
|host HREAD/HCAP/CHECK 및 DREAD/DCAP/DCHECK의 별도 parser 주소/헤더 처리|공통 ingress가 frame identity/header를 검사하고 canonical record 생성, batch의 3B 범위는 같은 실행기가 한 번 해석|physical sequence/serial/generation/오버플로·도메인·token 검사는 삭제하지 않음|
|host NORMAL의 queue read mux, ordinary header 재읽기·ACK identity 재구성, ACKWAIT/OSETUP/OTILE/OSELECT/XWAIT 간 완료 relay|SNES는 staging의 payload와 공통 active descriptor를 읽음. 소비 통지가 직접 독립 receipt 작업을 시작|실제 DMA 끝·읽기 coverage·token/consume identity 후 receipt; staging copy만으로 소비 인정 금지|
|validator packet_at298, executing/complete relay, E_READ/E_CAP/E_NEXT/E_ZERO의 packet/RLE decoder|공통 실행기가 기대값을 완성. 독립 검사기는 domain bounds와 receipt/validity/expected-map을 비교|V_R/V_P receipt update, CRC 완료 mask, fresh/persistent validity, cold map exact coverage, certificate/H2 의미 유지|
|310 stored_length/replay opcode/REPLAY/REPLAYWAIT와 phaseRAM166..255 임시 보관|queue RAM의 canonical manifest 영역과 수신 완결 cursor|미완성 manifest로 검사/SEAL 불가, duplicate/gap/overflow 거부|
|SPI·plan 별도 admission/status 생성·소유권 relay 중 중복 부분|공통 transaction commit/credit/IRQ snapshot에 연결|E1/E9 CRC domain·plan bank credit·E9/EA 종료·IRQ wake 유지|

기존 `manifest_started282 → manifest_phase → 일반 DMA 금지` 결합도 삭제한다. 새 수신 directory의 collecting/complete와 소비 terminal fence는 별개다. 기대값을 일찍 수신해도 일반 DMA를 막지 않고, terminal fence가 앞 DMA의 실제 receipt 완료를 기다린다.

상태 이름은 삭제 검색 대상이며 그 이름을 지우는 것만으로 비용을 회수한 것으로 치지 않는다. 새 state/주소 adder/CDC/active record/IRQ 비용까지 whole MAP에 포함한다. source/query ROM 공급기, lease CDC, shared tile/map staging, 독립 CRC datapath·persistent RAM·display token은 외부 유지 비용이다. 동일 hierarchy의 parent/child를 합산하지 않는다.

## 기존 1024B queue RAM의 확정 배치

별도 저장 FIFO를 추가하지 않는다. phase RAM의310 임시 보관도 없앤다. 다음 배치의 용량은 검산했지만 M9K inference와 포트 지연은 구현 때 확인한다.

|주소(끝 제외)|내용|bytes|
|---|---|---:|
|0..190|display24 + requirements166 기대값|190|
|190..446|dense map 기대값|256|
|446..478|requirements/map 수신 directory 각16B|32|
|478..480|padding|2|
|480..752|stream record slot0|272|
|752..1024|stream record slot1|272|

기존 wire packet은16..256B다. canonical record24B+payload 최대240B=264B로 각272B slot 안에 들어간다. batch는 기존 token/count5B를 record로 옮기고 3B range entry를 유지한다. 47개 범위를 각각24B record로 확장하지 않는다. 실제307/310 제한3프레임의286개 E1 packet 형상도 이 상한 안이다. 이는 전체71프레임 실행 검증이 아니다.

record24B 필드: kind/domain(2), physical sequence(2), start(2), span(2), encoded payload length(2), token base(4), range count(1), codec(1), 내부 payload offset(2), receipt first/end(각2), reserved-zero(2). serial/generation/epoch은 frame lease 문맥에 한 번만 유지하고 admission에서 비교한다. offset·receipt 범위는 FPGA가 계산하고 overflow 확인 후 저장하며 ARM 입력을 무검사 신뢰하지 않는다. 하나의 active record snapshot(최대192bit)과 batch cursor가 필요하다. 기존 active305/중복 parser를 대체하되 이 FF가 무료라고 하지 않는다.

metadata directory는 두 도메인의 valid/수신 cursor/예상 길이/완결 상태를 소유한다. map의 순차 offset 검사로 gap/duplicate를 막으므로 별도256B 수신 bitmap은 추가하지 않는다. 독립 **실제** map receipt bitmap은 기존 phase RAM에 유지한다. 수신 기대값과 실제 receipt는 서로 다른 주소·write source다.

## 포트·credit·완료 규약

1. queue RAM port A는 SPI ingress만 쓴다. 비어 있는 record slot을 예약하고 wire header를 검사하며 normalized header/payload를 기록한다. CRC/namespace/길이가 모두 맞아야 publish한다. 부분 쓰기는 slot을 valid로 만들지 않는다. header 확장 쓰기는 wire byte 사이 또는 CRC tail 동안 끝내야 하며 추가 SS gap을 무료 가정하지 않는다.
2. port B는 공통 실행기만 사용한다. metadata일 때 압축 payload를 읽고 canonical 영역에 쓴다. RLE zero128은 입력 한 byte보다 오래 걸릴 수 있으므로 SPI 입구에서 즉시 전개하지 않는다. slot에 보관된 payload를 순차 처리하고 마지막 write 후 credit을 반환한다. 후반 검사는 canonical 기대값을 읽을 뿐 RLE 해석을 반복하지 않는다.
3. DMA record는 staging에 payload를 한 번 복사하며 CRC를 계산한다. 원본 packet을 SNES나 validator가 다시 읽지 않는다. 마지막 필요한 byte와 active descriptor가 안전하게 보존된 뒤 storage credit을 반환할 수 있다. batch는 아직 staging하지 않은 범위가 있으면 slot을 해제하지 않는다.
4. active descriptor/staging 소유권은 SNES 실제 소비와 독립 receipt commit까지 유지한다. queue slot 반환은 이 소유권을 해제하지 않는다. 다음 DMA를 같은 staging에 덮어쓰지 않는다. ordinary와 typed의 소비 통지를 공통 consume-id/token 규약으로 통합한다.
5. status의 저장 credit/physical accepted와 소비 완료/fence는 별개다. 4slot을 전제로 한 ARM `sent-retired<=4` 검사와 F8/FA 응답은 새 버전/2slot 계약으로 교체한다. 구·신 버전을 묵시적으로 호환하지 않는다. 저장 완료 통지로 final drain/표시 완료를 대신하지 않는다. IRQ snapshot에는 두 상태 변화가 모두 포함된다.
E1 credit이0이어도 ARM은 E9 plan refill과IRQ/DMA 진행 확인을 계속 처리해야 한다. E1 공간을 기다리며 E9 공급을 멈추는 순환은 금지한다. BG 범위 종료와 frame 종료의 구분도 유지한다.

진행 응답 예산은 E2 12→14B, E0 24→26B로 잡는다. 기존 accepted/storage-released/phase/plan flags/plan accepted에 소비 완료 record counter16bit를 추가하며 CRC는 늘어난 응답 전체를 덮는다. 소비 counter는 metadata를 제외하고 batch 마지막 receipt까지 끝난 record만 증가한다. 물리 packet sequence와 혼용하지 않는다. E1처럼 이미 충분히 긴 전송의 piggyback은 wire 증가가 없지만 짧은 E9는 checked E2 fallback이 필요하다. 307 제한907의 E2 25회만 고정해도50B/0.152381ms wire 점유가 추가된다. 실제 횟수·CPU 검사·IRQ 변화와 overlap은 새 실행에서 측정해야 하며 무료로 빼지 않는다.

6. phase RAM의 host port는 동일 실행기의 독립 검사 단계가 소유한다. source→output lease 전환 전에는 queue 기대값을 실제 receipt로 쓰지 않는다. SNES는 기존 staging의 전용 read 포트를 사용하고 queue RAM에는 접근하지 않는다.
7. 마지막 DMA 소비→receipt commit→requirements/map coverage→CRC/certificate→12 display reads→VBlank 표시→token final ACK 순서를 보존한다. 다음 frame/epoch는 final ACK 전 열지 않는다. STOP은 두 RAM write enable·active descriptor·slot valid·DMA/표시를 모두 막고 token/serial 재사용을 금지한다. board reset namespace는 기존 bus quiesce 규약을 유지한다.

이렇게 metadata의 slot 점유는 유한한 해석/저장 작업으로 끝난다. 뒤 DMA 완료를 기다리며 queue head를 붙드는 순환은 없다. 그러나 **4slot→2slot 감소로 공급이 느려질 위험은 별개**다. 307의905/906/907에서 이미 pending>=2인 E1 발행이32/32/8회 있었다. 이를 새 stall 횟수나 지연으로 환산하지 않았다. 새 실제 ARM/IRQ 일정에서 검증해야 한다. 모든 일반 metadata9packet을 미리 담는 설계도 아니다.

## whole Lite 회로 예산

|경계|기존 comb|유지 외부 comb|새 hard cap|128 여유 포함 기능 cap|
|---|---:|---:|---:|---:|
|queue+host+validator만|3462|14121|1287|1159|
|위 경계+SPI+plan+glue|4730|12853|2555|2427|

queue118+host2093+validator1251만 바꿀 경우 기능1159라는 매우 작은 예산이다. 현재 요구하는 공통 admission/DMA700+독립 검사900만으로도 이를 넘는다. 따라서 **SPI713·plan506·glue49를 포함한 실제 삭제 대체가 이번 구현 경계의 필수 조건**이다. 그 바깥 절감은 증명 없이 가져오지 않는다. 이는 이번 기능 예산에 따른 범위 선택이며 세 블록만으로 구현하는 것이 원리상 불가능하다는 증명은 아니다.

|새 기능 묶음|할당 comb|
|---|---:|
|공통 admission·record·DMA 소유권|700|
|독립 CRC/receipt/coverage/H2/display 검사|900|
|queue 저장·SPI·credit/status|450|
|plan transport/credit|328|
|glue|49|
|기능 합계|2427|
|정책 여유|128|

이 수치는 요구 상한이지 합성 예상치가 아니다. 전체는 기능2427+외부12853=15280 이하를 목표로 하며 최소2175개, 여유 포함2303개의 순감소가 필요하다. 새 mux/CDC/record FF/불규칙272B 주소 계산/slot 상태/2credit 응답을 제외한 local MAP은 승인 근거가 아니다. RAM layout 추가 bits0도 물리 M9K 여유 증명이 아니다.

## 실제 ARM·IRQ·ROM 증거로 보는 시간 예산

|제한907|307|310|
|---|---:|---:|
|frame start ms|262.648621042|262.269125562|
|첫 BG ROM 승인 ms|274.905042|274.905042|
|start→BG ms|12.256420958|12.635916438|
|BG→최종 완료 ms|5.360504|5.304641|
|전체 ms|17.616924958|17.940557438|

310은 후반55.863µs를 줄였지만 앞 대기379.495µs가 늘었다. 따라서 선행 전송만의 시간 이득을 목표 감소로 사용하지 않는다. 합격은 같은 고정 ROM 창·실제 ARM 명령/IRQ/polling·plan refill·DMA/VBlank/final ACK를 포함한 **자기 frame start 기준16.666667ms 이하**, 정책 여유 포함16.416667ms 이하다. 307 대비 최소0.950258291ms, 여유 포함1.200258291ms 순개선이 필요하다.

307 시작점에서의 완료 deadline은279.315287709ms지만310처럼 시작이 앞당겨지면278.935792229ms가 된다. 한 시각을 고정하고 무료 overlap으로 맞추지 않는다. manifest 두 packet의 wire+직전 CPU 회계0.397512ms를 모두 없앤 가정에서도0.552746ms가 남는다. 이 회계는 encoding만의 비용이나 재배치 이득 상한이 아니며, 새 전체 실행 비용을 요구하는 진단값이다.

## 후보 비교와 구현 통과 기준

|후보|시간/회로 근거|판정|
|310 압축 보관 후 재생|실제17.940557ms/17717comb,307 대비 둘 다 회귀|미채택 유지|
|기존 제어+별도 manifest FIFO|삭제 경계 없음, 추가 RAM/제어·포트 비용 미확정|채택하지 않음|
|311 canonical manifest + 공통 record 실행 + SPI/plan 공동 교체|1024B 용량/286 packet 형상/삭제 명세/whole 예산 확정. 시간·MAP null|다음 구현 계약, 성능 승격 아님|

다음 구현은 (a) 실제 E1/E9 admission과2credit ARM 검사/IRQ, (b) 일반·batch payload→staging→실제 소비→독립 receipt, (c) canonical manifest→coverage→display/final ACK를 한 경계로 연결한다. 일반65816 descriptor/staging 소비 프로그램도 변경 대상이며 기존 trace의 identity만 바꿔 새 CPU 비용을 검증했다고 하지 않는다. STEP별 small MAP 절감으로 whole 비용을 대신하지 않는다.

검증은 2slot full/wrap·CRC 오류·partial record·long RLE·batch 마지막범위·저장 후 미소비·중복/누락 consume·각 포트 STOP·bank/token 재사용·조기 final ACK·VBlank 경계를 포함한다. 먼저 같은 정상/제한905..907 일정과 whole Lite를 실행하고, 동시에 예산을 만족한 경우에만 whole71/heavy7/fullRUN/FITSTA/물리 검증으로 확대한다. 2slot 때문에 공급 회귀하거나 whole cap을 넘으면 이 배치를 폐기한다. 별도 FIFO를 붙인 채 목표를 달성했다고 하지 않는다.

분석 재현: `tools/analyze_nes_boundary311.py`. 근거307/310 원본과 hash는 `analysis/boundary311-verification.json`에 고정한다. 이번 단계는 새 라이선스/시뮬레이션/MAP/FIT를 실행하지 않았다. 기존 생산 코드와 실패 증거를 보존한다.
