# NES393: 최종 DMA job·payload 공통 ABI의 교체 경계와 예산

## 판정과 검증 범위

다음 구현 경계는 **ARM이 최종12B DMA record와 실제 payload 순서를 함께 결정하고,FPGA가 실제 소비 기반 독립 검사를 수행하며,SNES가 record를 복사·검사·실행하는 방식**으로 정한다. 변경된 값만 담는 row/column run을 선택한다. SNES의 map job 재구성·64열 순회·gather 및 map cache를 없애고,기존 FPGA flow/context/queue/SPI/source-transport/plan/tile-adapter의 실행 제어도 같은 경계에서 교체한다.

이번 작업은 교체 범위·실행 조건·예산을 확정하는 단계다. 실제 M4 map component219case와 기존 Lite/ARM/SPI/IRQ/native trace를 분석했다. **새 ABI는 live firmware/RTL/65816에 아직 연결하지 않았고 새 whole MAP이나 연속 일정은 실행하지 않았다.** 392의 첫 capture 실패911·2336comb 부족은 그대로다. 여기서 계산한 byte/clock 예산을 새로운60fps·FIT 성과로 세지 않는다.

## 최종 record와 wire 경계

12B record는 SNES가 그대로 저장하는 실행 형식이다. source 수신 시 주소를 다시 구성해서 새 job을 만들지 않는다. bounds·length·bank·canonical 관계와 누적 DMA 예산 검사는 유지한다.

|offset|bytes|의미|
|---|---:|---|
|0|2|PPU destination:VRAM word 주소,그 외 domain 기준 주소|
|2|2|payload가 저장될 WRAM 주소,이후 PPU DMA의 source|
|4|2|decoded byte 수|
|6|1|PPU class·source mode·reference/store-only·stride32 flags|
|7|1|WRAM bank,허용7E/7F|
|8|1|VMAIN,VRAM80/81·그 외0|
|9|1|canonical region:BG/OBJ/map/CGRAM/OAM/HDMA|
|10|2|canonical first:tile slot/map word/region별 단위|

offset0..8은 현재 native12B job의 실행 필드와 같다.9..11을 canonical binding에 사용한다. MAP HOST_LITERAL component는 이 형식을 실제 M4에서 생산했다. TILE·일반 명령·REF·wire serializer의 전체 생산기는 아직 구현하지 않았다.

출력 wire의 공통 envelope는10B를 목표로 한다:kind/version1,flags/job-count1,sequence16,**serial32**,encoded-body-length16. generation/epoch/bank는 BEGIN의 기존84bit admission·H2 문맥에서 확인한다. 매 packet의 serial32와 sequence 검사는 유지하며,짧은 frame handle로 대체하지 않는다. STOP은 serial/token을 소각하고 보드 reset은 기존처럼 bus quiescence를 요구한다.

JOBS body는12B record table 다음 encoded payload다. record별 literal/repeat16/repeat32/TILE을 지원한다. 큰 HOST literal은 HEAD_ONLY를 저장한 뒤 DATA(offset16,payload)로 이어간다. 동시에 열린 HOST fragment는 하나이며 offset은 정확히 다음 위치여야 한다. physical packet은 계속256B 이내,source 순서대로 최대16record를 묶는다. data가 아직 준비되지 않았다는 이유로 DMA/refill을 막고 batch를 기다리지 않는다.

HEAD_ONLY의 storage credit은 record를 안전하게 보관한 뒤 반환한다. 뒤의 DATA나 실제 PPU 완료를 기다리면2슬롯 순환 대기가 생긴다. storage-retired·실제 source-consumed·PPU job-completed는 구분한다. fragment마다 fresh32bit token을 배정하고,actual read/CRC·private receipt가 끝나야 소비를 공개한다. PPU job ordinal과 fragment 소비 ordinal도 다르다.

N5 D4의13B prefix·MASK/SHIFT와 기존 E9 compact wire는 우선 유지한다. 공통 ABI는 ingress 뒤의 실행 record와 진행 규칙을 공유한다는 뜻이다. E9를 wire에서도32B로 늘려 첫 BG 공급을 늦추지 않는다. host의 공통 reader가 compact E9를 한 번 해석해 기존1KiB plan RAM의32B native record로 저장하고,NES decoder 본체를 대체한다.374처럼 별도 host decoder를 추가하는 범위만으로 회로 절감을 주장하지 않는다.

TILE record는 미래 FPGA token을 ARM이 만들어 넣지 않는다. canonical kind/slot/count와 이미 수락된 E9 plan 순서에 결합하며,FPGA producer가 그 job의 명시적 byte 경계로 staging을 끝낸다. 기존 producer의 독자적인 append/seal/chunk descriptor 진행을 중복 유지하지 않는다. tile32B RAM과 CDC ownership은 보존하고 새 실행기가 ACK까지 소유한다.

CGRAM/OAM의 기존 bank WRAM은 유지한다. 변경된 store 부분과 실제 PPU에 보낼 전체512/544B reference 실행을 구분한다. REF는 data를 읽거나 coverage를 생성한 것으로 취급하지 않는다. MAP REF는 금지한다. map은 항상 아래의 변경 값만을 새4KiB spool에 담아 보내므로 SNES row cache가 필요 없다. HDMA zero-tail은 기존의 offset21/length1100/seed0 조건에만 ROM-zero DMA를 허용하며 실제 채우기 비용을 계속 낸다.

## 독립 검증 인터페이스의 필요한 변경

현재 `nes_validator278`는 `unit359<v_map_end`를 거절한다.908은 두 screen의 run이라 우연히 오름차순이지만,909·914·915 등은 column 순서에서 이 조건을 위반한다. 또한 마지막 map bitmap은 expected와 **정확히 같아야** 한다. bounds 전체를 전송하면914에서20개의 변경되지 않은 word를 추가로 방문하므로 기존 검사가 거절한다.

선택한 방식은 변경 값만의 연속 column run이다. original required bitmap을 바꾸거나 실제 write에 맞춰 expected를 다시 만들지 않는다. 단순 오름차순 frontier를 없애되,단위 범위·RAM의 중복 bit 검사·최종 exact bitmap 비교를 모두 유지한다. actual SNES read에서만 canonical unit 완료를 생성한다. 새 cursor는 word 완료마다1/32를 진행하며 opcode·byte 주소를 여러 블록에서 복원하지 않는다.

packet/declared span/ARM의 END count만으로 receipt를 만들지 않는다. 기존 transport CRC·HDMA CRC/certificate·tile/palette validity·H2 의미 검사와 최종 expected scan은 유지한다. 독립 validator의 의미·fault 상태를 공통 executor의 성공 bit와 합치지 않는다. 현재1038comb checker를 보존 비용으로 잡았으며,새 interface의 순증분은 아래1,387 상한에서 추가로 차감한다.

|frame|row run|선택 column run|전송 map bytes|비고|
|---|---:|---:|---:|---|
|907|7|7,이 frame은 row 선택|40|12개 column보다 유리|
|908|16|2|32|두 screen,기존 ascending과도 호환|
|914|28|15|82|기존 표시14job/122B의 빈 셀 제거|
|915|41|15|128|순서 변경에 대한 validator 수정 필요|
|962|기록별 JSON 참조|22|140|빈 셀22word를 보내지 않음|

71개의 원래 map packet·material에서 row/column/auto를 실제 M4로 실행하고,decoded PPU 주소·payload가 required와 정확히 같은 집합인지 비교했다. duplicate·누락·extra word가 없어야 한다. 6개 추가 case는 empty·경계·column holes·정렬 패턴·256job 초과·잘못된 bank를 포함하며,거절은 job 공개 전에 일어난다. 총219case 통과다. 이것은71frame live 실행이나 새65816·RTL 검증이 아니다.

## 실제 비용과 시간 예산

component는604B text·관측 stack68B다. unit BSS11808B는 input4352B+output7168B+transpose256B+통계32B로,production RAM 비용이 아니다. 실제 streaming callback을 만들어7168B output 배열을 없애야 한다. provisional ARM 추가 BSS는377 대비320B 이내,전체 관측 stack은1536B 이내를 목표로 하되 fullresident RAM·IRQ 최악 조건은 별도 검증한다. unit stack68B를 전체 call chain으로 부르지 않는다.

|frame|390 bounds producer|393 최종 map job·packing component|CPI1/84MHz 차이|
|---|---:|---:|---:|
|907|9791명령|5776명령|−0.047798ms|
|908|10441명령|3328명령|−0.084679ms|

component는 common serializer/CRC·TILE/all-ordinary 생산·IRQ·credit 대기·새 SNES 수신 비용을 포함하지 않는다. warm69 fixture의 auto component는3168..8189명령이며,첫 hint보다 먼저 전체 call을 넣지 않는다. 구현 시16bitmap-byte/16changed-word 등 중단 가능한 quantum과 DMA/IRQ/refill 우선순위를 실제로 계측해야 한다.

다음 E1 byte 표는 실제392의907/908 전송을 대조한 **wire 예산**이다. 새10B envelope·12B record·literal/기존 압축 seed·fragment·reference job을 모두 센다. TILE head는 관측 chunk마다 개별 packet으로 계산한다. nonmap batch는 source 순서를 유지하지만 준비 시각·2credit 대기를 재현한 새 schedule은 아니다. E2/IRQ 감소는 전혀 세지 않는다.

|출력 E1 wire|907|908|
|---|---:|---:|
|실제392|647B|774B|
|새 record,nonmap 새 batching 없음|673B|617B|
|새 record,nonmap source-order batch|595B|526B|
|변화 범위|26B 증가~52B 감소|157~248B 감소|

907을 무조건 SPI 개선으로 부르지 않는다.908의 wire 감소는 현재SPI clock에서0.478476..0.755810ms이고 component 차이는0.084679ms다. 현재 view 뒤 phase339307에서 cutoff335544를 이미0.175209ms 넘는다. post-view ≤0.100ms를 목표로 하면 ready를 최소0.275209ms 앞당겨야 한다.

wire와 component 감소가 **전부 critical path에 반영된다**고 가정했을 때만,새 수신·검사·serializer·SS gap·IRQ/credit/ROM 경쟁의 추가 비용에 남길 수 있는 상한이 **0.287946..0.565279ms**다. 실제 여유나 완료 시간 예측이 아니다. SPI 수치는 byte clock만이며 SS gap 감소나 E2/IRQ 감소는 세지 않았다.907은 현재cutoff238행까지 더 여유가 있어 같은 공식의 추가비용 상한은2.321440..2.559154ms다. 이 차이를 평균으로 숨기지 않는다.

908의 첫 hint fill282.681539ms와 좁은 ROM 허용 구간을 보존한다. DMA/IRQ·E9 refill과 causal hint를 먼저 처리하고,그 뒤 남은 구간에서 map packing을 진행한다. 시작/ROM 위상을 바꾼 이득을 섞지 않는다. 새 fixed-start 실행과 별도 연속 실행에서 capture908..917을 검사하며,911 누락이 해소되어도 완료 간격·71/heavy7·다중 위상을 별도로 확인한다.

### VBlank budget gate

**3328clock commit/control**,8clock/PPU byte와512clock 예비를 유지한다. 71 fixture의 tile 범위와 palette/OAM 전체 실행도 합쳤다.1280clock/job이면962는50400clock이고,512 예비까지 넣으면50912로49104 한도를1808clock 초과한다. 다른 warm68개는 이 screening 한도 안이다. 이는 hardware 불가능 증명이 아니라 현재 allocation의 실패다.

새 소비기 목표는 **VRAM job≤1200clock,기타 job≤1408clock**이다.962는29VRAM+1OAM,1084B이므로 `3328+29*1200+1408+1084*8+512=48720`이 된다. 남은384clock을 mapper 여유로 승인하지 않는다. 이 목표를 적용하면 fixture69warm이 budget에 들어가지만,새 CPU에서 증명하기 전에는 통과로 세지 않는다.

기존391 실제 trace의 inter-job control+DMA fixed/refresh 관측 최대는 VRAM1062/OAM1300clock이다.1280을 일괄 낮추면 안 되는 근거이기도 하다. 새 raw12B 실행기에서 입력 단계로 검사를 옮기고 VBlank 중 재구성을 삭제한 뒤,첫 job·채널 변경·CGRAM/OAM·refresh·시작 위상·STOP까지 재측정해야 한다. budget/cutoff/512 예비를 억지로 낮추지 않는다.

## 전체 Lite 비용과 실제 삭제 예산

현재 실제 Lite392 전체는22471LE/17744comb/8985FF/300640bits다. 새 map component는 FPGA를 합성하지 않는다. 다음 표의 숫자는 현재 MAP의 **self comb**이고 parent inclusive를 더하지 않았다.

|교체할 제어|현재 self comb|새 hard cap|
|---|---:|---:|
|flow1937+context102|2039|380|
|queue 저장·credit|213|104|
|공통 SPI snapshot/CRC8/응답|576|320|
|source transport400+plan350+endpoint100+tile adapter200|1050|460|
|새 RAM port arbiter/bridge 증분|0|123|
|합계|3878|1387|

기본9블록 pool은3678이고,고정 chunk 경계를 실제로 대체할 tile adapter 자체200을 포함해3878로 넓혔다. tile mailbox11과 aperture207·staging RAM·capture gates는 바깥에서 계속 낸다. N5 encoder1336과 독립 checker1038도 보존한다. 현재 pool self FF는1665이며 새 controller의32B NES resume 상태도 여기에 포함해 budget을 검증한다. RAM을 FF로 바꿔 절감처럼 보이게 하지 않는다.

이 표는 기능별 예산이며 clock 이전을 통한 절감표가 아니다. 기존 source transport와 plan endpoint의 host 부분은 새 host/SPI cap 안에서,실제 NES 진행은 NES cap 안에서 각각 한 번만 낸다. 최종 report의 disjoint self 비용으로 다시 합산한다.

전체 식은 `17744=11492(기타 보존)+2374(codec/checker)+3878(교체pool)`이다. 목표는 `11492+2374+1387=15253comb`,device15408 대비155예비다. **3878−1387=2491 순삭제**이며 새 checker/ROM/범위 밖 CDC 증분이 있으면1387에서 더 차감한다. cap은 구현값·예측값이 아니라 중단 기준이다. 392의 옛1091 조건을 현재 self pool처럼 사용하지 않는다.

RAM300640bits와FF8985는 기존 전체 비용의 기준이다. 새 제어 ROM이나 프로그램 확장이 논리에 유리하면 검토할 수 있으나,M9K 실제 용량·port/fetch latency·주소 decode와 전체 MAP/FIT 비용을 별도로 낸다. RAM 증가를 무조건 금지하거나,작은 ROM·상태 저장을 공짜로 계산하지 않는다.

flow/context/queue만의2252는 전부 삭제해도2491보다 작다. tile200까지 전부 없애도2452라 새 executor를 넣을 공간이 없다. host만 바꾸는 구조를 성공 후보로 삼지 않는 이유다. host ingress와 manifest/descriptor/receipt 실행뿐 아니라 source·plan·SPI의 주소·진행·완료 제어도 함께 교체해야 한다. 순수 source codec/query FSM까지 삭제했다고 주장하지 않는다.

## 소유권·포트·삭제 목록

host에는 공통 record reader/executor를 두고 NES clock에는 source/plan/tile의 중단 가능한 실행기를 둔다. 현재의 host clock과46561ps master test 조건을 유지한다. 서로 다른 clock을 FSM 하나로 묶거나 RAM clock을 mux하지 않는다. independent checker는 별도의 fault/expected 의미를 유지한다. input D4와 display E1/E9의 namespace 문맥도 합쳐 덮어쓰지 않는다.

|기존 RAM/상태|새 소유권과 제한|
|---|---|
|queue1KiB|expected0..471·2×256B slot512..1023 유지. expected/actual 검사 요청을 head reader보다 우선.472..511을 공짜 buffer로 세지 않음|
|phase RAM52B716..767|host active job12/token4/cursor8/unit-lane4/ordinals4/manifest-fragment4/D4 snapshot6/cold-token4/flags2=48B+spare4. init278 이전 금지·frame clear 보존·STOP 취소|
|read-critical cache|unit/counter/flags를 실제 read 간격 안에 응답하도록 FF cache. byte마다52B fetch 금지. 관측31host clocks를 물리 WCET로 간주하지 않음|
|source ring1KiB+shadow512B|NES write/host D4 read·4packet Gray ownership 유지. footer6B와 immutable response snapshot을 덮어쓰지 않음|
|plan1KiB|host native32B×16×2bank/NES8word read. 기존374의 실제 M9K 방식 사용. sealed bank에 resume state를 숨기지 않음|
|tile32B+staging4KiB|dual-clock tile lifetime/2×2KiB immutable aperture·실제 read capture 유지. producer의 독자 descriptor/append/seal FSM은 공통 job으로 대체|
|NES resume 상태|source/plan2context32B를 명시적으로 FF 예산에 포함. ROM reply·cancel drain·DONE 차단 우선|

flow의 HLOAD/HCHECK·PREAD/PCAP·DREAD/DCAP/DCHECK·MREAD/MCAP/MISSUE/MWAIT·ordinary EXPAND·중복 완료 state와 active305/payload cursor/legacy destination·PPU export를 제거 대상에 넣는다. shared-context header/token reader,queue의 별도 field loader·완료 제어,plan endpoint의 별도 lifetime/address 제어,NES byte/shortform/alt operand decoder와 tile chunk descriptor 제어도 교체한다. 물리 SPI shifter·immutable snapshot·CRC·slot credit·token/serial burn·read capture·fault gates는 새 실행기 안에서도 실제 비용으로 유지한다.

SNES는 source별 typed/ordinary adapter와 `job()` 재구성·strategy/column loop·gather·map 좌표를 제거한다. immutable12B를 table에 복사하고 정적 검사를 수행하며,source 단계에서 saturating budget을 누적한다. store-only는 table에 남기지 않고,REF는 coverage를 만들지 않는다. source 단계의 copy·bounds·context read 비용도 위 시간 상한에 포함한다.

SNES 예약은 tile spool8192+job table3072+map spool4096+VRAM-bank validity1=**15361B**를 목표로 한다.392의23841 대비8480B 감소 예산이며 아직 새 consumer의 link 결과가 아니다. 기존 CGRAM/OAM/HDMA 양 bank8948B·DP/view/stack은 별도 보존한다. 새 전체 resident ROM/decoder 증분은 미확정이고4KiB를 하드 목표로 두지 않는다.

## 완료·취소와 구현 gate

BEGIN에서 namespace를 고정하고 SNES에는8B readonly 문맥을 frame당 한 번 제공한다. JOB/DATA의 storage credit·actual source receipt·PPU 완료를 혼동하지 않는다. expected/SEAL은 모든 source read와 private receipt 뒤에만 진행한다. BG 범위 완료는 frame END와 구분한다.

END는 empty warm에도 항상 보낸다. source가 없는 경우 마지막 map token을 재사용하지 않고 **fresh32bit fence token**을 할당한다. TILE/HOST/fence는 공통 allocation/burn 규칙을 사용하며 `ordinary_next313`의 별도 진행을 중복 유지하지 않는다. independent seal·모든 source 소비·12회 정확한 view read가 끝난 뒤 실제 PPU job 완료와 VBlank를 확인한 CPU만 최종 ACK를 보낸다. fence 자체는 가짜 byte receipt를 생성하지 않는다. 실제 tile mailbox generation/kind/slot/length와 job 경계를 대조한다. blank tile kind2는 BG slot0/16B에만 대응하며 BG partial-end와 혼동하지 않는다.

STOP은 모든 authority와 SNAPSHOT을 취소하고 token/serial을 소각하며,실제 pending ROM/collector 취소 완료 전에 소유권을 재사용하지 않는다. STOP 뒤 DONE·최종 ACK를 차단하고 SNES는 forced blank·HDMA off·bank validity0으로 간다. cold/empty/warm 모두 같은 v2 경로를 구현해야 기존 legacy PPU/header 제어를 실제로 없앨 수 있다. A/B legacy는 별도 test top으로만 두고 새 보드에 runtime fallback으로 합성하지 않는다.

구현 순서는 (1) common record·단일 MAP/TILE/일반5·empty END/FENCE와 독립 중복/누락/STOP 검사,(2) 실제 M4 serializer/refill/IRQ 및 실제65816 raw-job 수신·PPU 경로,(3) 두 clock 실행기와 기존 제어 본체 삭제·동일 보드 Lite MAP,(4) 동일 ROM 위상/연속 capture·heavy7/71·다중위상/cold/STOP 정상복구다. 최소 slice만 통과한 상태에서 area/60fps 성공으로 채택하지 않는다.

예산 밖 증분까지 포함한 새 whole comb≤15253,2슬롯 credit 정확성·포트 충돌 없음·독립 검사·STOP·final ACK·VBlank,962 포함 budget 증명,911 이후 capture와 완료 간격을 **동시에** 통과해야 한다.1387 cap에 실패하면 또 다른 adapter나 opcode/seed/FIT 반복을 하지 않고 역할/전송/하드웨어 경계를 재검토한다.

375/377·392 증거와376 mapper gate,production227/GBC164/saveSRAM을 보존한다. MMC4/5·physical60fps·fullresident WCET/FIT/STA는 미승인이다. 근거는 `analysis/jobs393-verification.json`;raw component 및 실패 기록은 `../probes/nes-jobs393/`에 보존한다.
