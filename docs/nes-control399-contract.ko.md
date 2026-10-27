# NES399: 실제 read·공개·RAM 포트와 다음 입력의 소유권 재검토

## 판정

다음 구현 후보는 **고정 transaction 수신 경로 + 실제 read 완료의 단일 진행 소유자 + 표시 대기 중 다음 입력 수신**이다. SNES는 같은17B header를 DMA로 받는다.398의 범용 바이트 실행기에 FSM을 더 붙이는 방식은 선택하지 않는다.

이번에는 후보 전체를 구현하거나1,172comb 달성을 입증한 것이 아니다.398의 정확한 일정과 포트 사용을 재계측하고,header DMA를 실제65816과 전체 보드 ROM에 분리 연결했다. **전체 공동 구조의 비용·917 복구는 아직 미입증**이다. 기존 실패를 PASS로 바꾸지 않는다.

실제 개수 EA·ARM 발행 소유권 수정·FIFO3584B·ordinary512B·frontier33·2슬롯·907 복구·908 VBlank17·911 캡처/표시/최종 ACK를 보존한다. 독립 expected/CRC/coverage·STOP·최종 ACK·VBlank를 제거하지 않는다.

## 이번 증거의 범위

|증거|변경과 결과|
|---|---|
|trace01|398 live11을 수동 계측.33RTL·ARM ELF·프로그램·全 joint-events.csv·ARM worker log가 정확히 같음|
|native01|같은 canonical job/payload의17B header를 DMA로 수신.905/906/907/908/914/915/916 및 STOP PASS|
|map01|새1778B 65816 ROM을 기존4KiB 보드 ROM에 실제 설치한 전체 Quartus Lite MAP|

trace01의 실제12프레임 표시·최종 ACK와917 캡처 실패는398과 같다. 이 일정에 새 header DMA CPU 시간을 빼서 새 성능으로 선언하지 않는다. native01은 이전 표시 bank를 fixture로 둔 CPU kernel 검사다. 전체 resident 또는 새로운 ARM·IRQ·SPI·2슬롯 일정은 아니다.

전체 비용은 **22157LE /17428comb /8916FF /382304 logical RAM bits**로398과 같다. header DMA만으로 FPGA 제어는 줄지 않는다. 제어는3471, 예산1172보다2299개 초과한다. FIT/STA는 실행하지 않았다.

## 시간: ROM 뒤의 소비 비용과 표시 대기

914의 마지막 tile 생산은389.481159ms, 마지막 실제 데이터 job 소비는398.756203ms, 마지막 REF job 소비는400.167672ms다. 모든 구간을 ROM 대기나 순수 CPU 비용으로 분류하지 않는다. 입력 생산·공유 SPI·FPGA 준비·SNES 소비가 겹친 실제 일정이다.

source17B header는 현재 CPU가17회 indexed load/store와 loop로 받는다. 새 CPU kernel은 cartridge A-bus `$00:6080..6090`→B-bus `$2180`→기존 WRAM `$0030..0040` DMA를 사용한다. WRAM→WRAM DMA가 아니다. 그 뒤의 bounds·reference·zero 처리와 token·PPU·VBlank·최종 ACK 검사는 그대로다. 추가 WRAM은0이며 기존15360B source/job/map 배치를 유지한다. ROM body는1738→1778B다.

|프레임|기존 job source-service clocks 합|header DMA 후|CPU component 절감|
|---|---:|---:|---:|
|905|310050|226250|3.901812ms|
|906|354362|257354|4.516789ms|
|907|115992|87372|1.332576ms|
|908|80510|60334|0.939415ms|
|914|161348|120972|1.879947ms|
|915|161548|121252|1.876222ms|
|916|67262|50510|0.779990ms|

17B header 첫 read→마지막 read는2216..2256 master clocks에서128..168로 줄었다. 표의 합계는 각 job 첫 fault read→실제 consume write의 실제65816 시간이다. VBlank 원점 변경이나 ARM·ROM·credit의 재배치를 포함하지 않는다. 새 DMA는8 master clocks 간격의 header read를 만들므로, 기존 느린 CPU loop에서 metadata 충돌0건이었던 결과를 재사용해 새 포트 마감 통과라고 할 수 없다. 다음 결합 시험에서 이 실제 burst와 stage atomic 접근을 함께 검사해야 한다.

|동일398 원점에서의 목표|실제 표시 gate|목표 VBlank의 마지막 허용 gate|필요 선행|header component 절감을 전부 얻는 가정 뒤 남음|
|---|---:|---:|---:|---:|
|914→VBlank23|400.234403ms|397.377043ms|2.857360ms|0.977413ms|
|915→VBlank25|434.922682ms|430.655866ms|4.266816ms|2.390594ms|

마지막 열은 낙관적 동일 원점 민감도 계산이며 retimed bound가 아니다. 이전 프레임의 완료·SPI 응답·ROM 창이 바뀌면 전체를 다시 실행해야 한다. header DMA 단독을917 해결로 세지 않는다.

917의 캡처 기한416.485026ms보다916 source 시작417.932677ms와 materialized418.514969ms가 각각1.447651/2.029943ms 늦다. 특히 ARM은914의 packet을 모두 발행하고 consumed 대기를 마친 뒤가 아니라 **sent=retired=304, pending=0인 출력 drain 경계**에서 `finish267`에 들어간다. storage retire와 실제 소비 완료를 혼동하지 않는다.

|실제 ARM 호출|시작|종료|시간|
|---|---:|---:|---:|
|914 finish267|400.284361ms|415.125336ms|14.840975ms|
|그 뒤915 source_receive367|415.152883ms|417.936667ms|2.783784ms|

따라서 **출력 발행이 끝났지만 표시/plan retire를 기다리는 동안 다음 N5 입력을 받는 것**이 검증할 가치가 큰 후보다. 단순 buffer 증설보다 이 직렬 장벽을 먼저 다룬다. 관측된 대기14.841ms가 수신2.784ms보다 크다는 사실은 새 일정의 성공 증명이 아니다.

## 다음 입력 수신과 표시 commit 분리

다음 N5를 미리 받는 동안 이전 output의 resident/dirty/video·lease·fence는 유지한다. 다음 `begin285`·tile plan 발행·bank 재사용은 이전 표시의 정확한 final ACK와 retire가 끝난 뒤에만 한다. 수신 credit·입력 CRC 완료를 표시 성공으로 쓰지 않는다.

현재 `publish352()`는 `receiver280.epoch/serial/raw_count`를 읽는다. 다음 수신이 이 값을 바꾼 뒤 기존 commit을 그대로 호출하면 **다음 입력 identity를 마지막 표시 이력으로 잘못 게시**한다. 그러므로 다음을 별도로 소유해야 한다.

- 이전 표시용 source epoch·serial·raw_count snapshot과 pending 표시 상태.
- 다음 입력의 receiver/history·raw-group·geometry-group 변화와 CRC 완료 상태.
- 기존 resident/dirty commit과 source 저장 credit, plan retire, final display ACK 각각의 완료.

현재 source CRC decoder와 history는 이전 packet을 base로 사용한다. 이전 출력 packet의 생산이 완전히 끝난 뒤에만 history 덮어쓰기를 검토한다. 이전 `video285`·resident/dirty는 commit 전 보존한다. `wire_busy394`·분할 D4 SS·출력 serializer가 같은 scratch를 소유한 동안에는 수신을 시작하지 않는다. 실패는 STOP/무효화로 끝내며 입력을 성공 표시로 되돌려 해석하거나 불명확한 패킷을 재시도하지 않는다.

선행 수신 중에는 다음 hint를 표시 권한으로 사용하지 않는다. source_hint367의 displayed/open/prepared 조건을 삭제하지 말고, 다음 입력의 causal geometry 집합을 보존해 이전 표시 commit 이후에 정확한 identity로 EA를 발행한다. 추가 ARM RAM·cycles·SPI/IRQ 비용은 아직null이다.4.9KiB history의 무조건 이중화를 승인하거나 새 비용을0으로 세지 않는다.

## 실제 read와 완료 공개의 경계

계측된25462건에서 accepted read와 read_end 수는 같고 거부는0이다. read_pending은407392 host cycles, 즉 건당16cycles다. 최소 연속 read 간격은`$time`으로 기록한404000ps, 약34 host clocks다. timestamp의 ns 반올림과 이번 버스 모델의 관측값이며 실제 DMA 모든 위상의 보장값이 아니다. read 시작→끝에 이미 시간을 쓰므로 전체34클록을 read 종료 뒤 CRC 처리 예산으로 쓸 수 없다.

단일 진행 소유자의 계약은 다음과 같다.

1. RAM 응답의 address·data·generation/token을 고정하고 실제 read의 소유자를 기록한다.
2. 유효한 read 종료를 확인해 같은 byte를 한 번만 CRC·coverage 진행에 넘긴다. 중단된 read·주소 변경·중복 read는 fault다. 실제 데이터와 독립 expected는 계속 별도다.
3. 마지막 byte의 read 종료와 checker drain이 모두 완료된 뒤 token consume을 허용한다. 마지막 token·12view·sealed·empty·VBlank/PPU 완료 전에는 final ACK를 공개하지 않는다.

capture/read_end 두 사건을 같은 것으로 취급하거나, 완료 callback이 왔다는 이유만으로 CRC·read_pending을 건너뛰면 안 된다. 새로운 경계는 실제 SNES DMA 간격에서 끝나는 bounded pipeline이어야 하며 byte마다 프로그램 문맥을 가져오지 않는다. STOP은 interpreter·RAM 응답을 기다리지 않고 write/publication을 차단한다.

## RAM 포트와 제어 삭제 후보

|실제 RAM|고정 포트 소유권|새 구조의 제약|
|---|---|---|
|4KiB payload|host A:tile prefill/ordinary write, host B:SNES source read|3584/512 분할 유지. header/status를 세 번째 포트처럼 끼우지 않음|
|1KiB metadata|host A:stamp/prefill/header 중재, NES B:tile mailbox/hint tag|불변 record와 제한된 hot state를 보관. header DMA에도 같은 포트의 지연을 지불|
|1KiB source|NES encoded packet write, host pinned-head SPI read|4packet ring·CRC·Gray ownership 유지|
|1KiB plan|host unpublished bank write, NES sealed bank read|CRC/shape/lease 확인 전 NES 공개 금지. host normalizer와 NES decoder 중복을 같이 삭제|
|새 status 저장|제거할 program 공간의 일부를 별도 RAM으로 재사용하는 후보|SS 전 coherent snapshot 준비·CRC 완료, SS 동안 bank 고정. metadata에 추가 포트가 생기는 가정 금지|

12프레임에서 interpreter 문맥 read431054/write203701, 문맥 대기1269605 host cycles를 관측했다. 반면 header grant3084건은 stage atomic과 대기 충돌0건이었다. 기존 header 포트 충돌이 이번 큰 지연 원인이라는 근거는 없다. 문맥 대기 cycles도 다른 진행과 겹치므로 전체 시간에서 그대로 빼지 않는다.

source footer와 plan read의 동시 request는 이번 일정에서0이었다. 이를 근거로 두 RAM을 하나로 합치거나 일반적으로 동시 접근이 없다고 선언하지 않는다. source/plan 본체를 바꾸면 일정도 달라진다. 고정된 물리 포트와 저장된 재개 문맥으로 두 종류의 작업을 중재해야 한다.

|현재 제어 비용|398 comb|교체 후보와 반드시 남길 것|
|---|---:|---|
|host + byte core + program decode|1462|범용 ISA·IRQ 문맥·임의 IO selector를 삭제하고 고정 packet-field/payload 실행과 실제 read/publication 소유자를 함께 구현|
|source/plan/hint|1012|footer 서비스만이 아니라 writer·plan field/shape 실행 본체 교체. 두 lifetime과 취소 drain 유지|
|SPI|686|176bit variable lane·snapshot/진행 비교를 prebuilt RAM snapshot과 set-dominant dirty publication으로 재검토. bit/SS/terminal CRC 마감 유지|
|queue|263|공통 ingress에서 한번 검사하고 immutable slot에 게시. opcode 시점 reservation·accepted/retired/consumed 구분 유지|
|tile bridge|48|고정 소유권과 STOP/반환 handshake 유지|
|합계|3471|기존1172 예산 대비2299개 더 줄여야 함|

새 구조의 합성값은null이다.397의1172는 여전히 합격 상한이며, 적당한 분배 숫자를 만들어 구현 가능성으로 제시하지 않는다. 독립 codec/validator2335와 outside11622를 보존한 현재 조건부 전체 상한1296보다도 이 기준이 엄격하다. 전체15253 목표/실제15408 장치 한도·FF/LUT packing·M9K·새 port/CDC 비용까지 함께 검사한다.

source와 plan의 host 수신/완료 제어를 공통 ingress로 옮기면서 NES 실행 본체도 삭제해야 한다. host normalizer를 추가하고 기존 NES decoder를 남기는 방식이나, byte interpreter만 제거하고 기존938comb IO 층을 남기는 방식은 충분한 삭제 근거가 없다. MASK·SHIFT·ordinary/RLE 압축은 보존하고 FPGA에서 한 번만 확장한다. 불필요한 map hole 전송이나 검사를 없애는 방식으로 CPU 시간을 맞추지 않는다.

## 실기 테스트 가능 시점

**현재398/399 전체는 장치 한도를2020comb 초과하므로 실기에 올릴 수 있는 새 전체 이미지가 없다.** header DMA만의 절감이나 가드 통과 횟수로 설치 가능 시점을 앞당겨 말할 수 없다. 지금은 최적화 마지막 몇% 단계가 아니라 새 제어 경계가 보드에 들어가는지 입증해야 하는 단계다.

가장 이른 제한 실기 시점은 다음 두 큰 단계가 끝난 직후다.

1. 고정 transaction/read/publication·source/plan 교체가 전체 용량에 들어가고, 새 경계의 STOP·token·최종 ACK가 작동하는 구현을 확보한다. 해당 실제 이미지로 전체 FIT/STA와 변경된 CDC/외부 IO를 확인한다.
2. 같은 이미지에 맞는 실제 resident ARM·65816·loader/메뉴·sound/input/STOP을 연결하고 full-link RAM/stack·짝 해시·기존 복원 경로를 확인해 제한된 첫 레벨 관측 패키지를 만든다.

다음 구현이 첫 시도에 예산과 timing을 통과한다면 **그 뒤 보드 통합·패키징 단계에서 첫 제한 실기**가 가능하다. 그러나 그 구현이 아직 없으므로 “며칠 뒤”나 특정 날짜를 약속할 근거는 없다. 이번 측정에서 전체 연속 시험 한 번은 약25분30초였으며, 이 도구 실행 시간을 설계·디버깅 소요 일수로 바꾸지도 않는다.

첫 제한 실기를 MMC4/5 완성·모든71 heavy·완벽한 지속60fps까지 기다리도록 새 조건을 쌓지는 않는다. 용량과 필요한 변경 경계가 확인된 맞는 짝으로 최소 구동·표시·중단·메뉴 복귀를 관측한 뒤 실기에서만 알 수 있는 실제 ARM/SPI/IO 지연을 얻는다. 그 시험과 지속60fps 성능 승인은 구분한다. production227/044의 같은 부팅·복원 시험이나 새로운 범용 진단 체계를 반복하지 않는다.

이번 결과는 자동 merge·실기 배포·유료 라이선스 구매가 아니다. production375RTL/377ARM·227/GBC164/saveSRAM을 유지한다. 분석과 파일 해시는 `analysis/control399-verification.json`, 원시 증거는 workspace 상위 `probes/nes-control399/`에 보존한다.
