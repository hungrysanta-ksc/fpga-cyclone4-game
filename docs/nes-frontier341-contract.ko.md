# NES341 일반 warm 첫 BG 확정 경계와 데이터 경로 삭제 예산

선택 구현은 **338 RTL·336 ARM 유지**다. 이번 단계는 실제 소스 감사, 기존 실행 증거 재검증, 유한 상태 모델과 다음 구현의 통과 예산이다. 새 RTL/ARM 실행·Quartus MAP을 하지 않았다. 따라서 실제 부족은 여전히 **4.022994145ms / 1,866comb**다. 340 후보의 시간·면적 실패를 기준 구현에 합치지 않는다.

## 일반 warm의 첫 plan 경계

338의 실제 warm907 첫 E9는 clear와 slot **82,83,84,85,86**을 포함한46B다. 이것은 정렬 후 패킷이며 최초 allocator 호출 순서나 slot1..81이 확정되는 시각을 알려주지 않는다. 340의 slot1 조건을82로 완화하는 것은 안전하지 않다.

`nes_resident211_slot`은 used slot을 다시 evict하지 않고 exact-key 중복은 emit하지 않는다. 그러나 아직 사용하지 않은 낮은 slot은 retained hit, invalid 선택 또는 eviction으로 나중에 emit할 수 있다. `nes_resident287_touch`도 동일한 used 전이를 만든다. 다음 경계를 제안한다.

- 기존 used bitmap에서 **가장 낮은 미사용 BG slot**을 frontier로 유지한다. clear0은 별도다. pending batch를 기존 order247 순서로 정렬하고, frontier보다 작은 확정 prefix만 발행한다. hit로 plan을 만들지 않은 slot도 used 갱신에 포함한다.
- slot 선택·exact key·map 기록이 완료된 뒤 frontier를 갱신한다. 증가만 하며 BG 전체에 최대1023 slot 검사다. 매 호출 무제한 스캔하지 않고 최대8 slot씩 작업을 끊어 DMA/credit/IRQ를 우선한다. 검사당 실제 M4 비용과 새 상태 크기는 미측정이다. 별도1024slot 목록은 만들지 않는다.
- prefix를 보내도 원래 batch의 byte/plan 용량을 예약한다. 15plan/240B 경계, 이후 OBJ 정렬 범위, BG 완료 표식은 그대로다. 기존 flush가 확정되는 시점에는 전체 pending batch를 보낼 수 있다. frontier가 움직이지 않으면 기존 batch 완료까지 기다린다.
- 입력 CRC·semantic·generation 전체 COMMIT 전에는 private 계산만 가능하다. source RAM 소유권을 빌리거나 E9/ROM·token을 공개하지 않는다. STOP은 private frontier/prefix/reservation과 해당 generation을 폐기하고 기존 cold 재시작을 따른다.

8slot의 모든 used 집합과 선택 slot 조합1024건에서 위 조건을 모델 검사했다(255건 안전,769건 후속 낮은 slot 반례 가능). 이는 allocator 추상 모델이며 실제 M4/전체 slot 공간의 실행 증명은 아니다. 실제 first-ready 시각은 **null**이다. 첫 plan이 slot82라는 이유만으로 빨리 준비된다고 주장하지 않는다.

대안인 “먼저 발견한 slot을 정렬 밖으로 즉시 전송”은 제외한다. plan parser에 명시적 단조성 검사가 없더라도 DMA 순서·staging 경쟁·후속 map 안전성은 동등하지 않다. 전체 allocator를 prepass한 뒤 보내는 방식도 준비 비용을 이중 청구하므로 기본 후보로 삼지 않는다.

## 시간 예산과 ROM 구간

| warm907 | 실제338 총 시간 | 앞선 ROM close까지 | 18B prefix 포함 nonwire 여유:338 전송 | 206B 전송 가정 |
|---|---:|---:|---:|---:|
| 동일 시작·ROM 위상 |25.051199382ms|6.089721952ms|4.280198142ms|5.387245762ms|
| 제한 ROM 연속 |20.689660812ms|1.728002082ms|**−0.081521728ms**|1.025525892ms|
| 정상 ROM 연속 |13.410066350ms|해당 앞선 구간 없음|별도 전체 비교|별도 전체 비교|

206B는340의 실제 성공 wire 길이만 빌린 조건이며340 source/ARM 비용이나 새 후보의 전송 크기를 보장하지 않는다. polling·생산·decode를0으로 두어도338 전송+18B prefix는 제한 일정 구간에81.522µs 늦다. 따라서 frontier 단독 변경은 분리 측정 가치가 있지만 공동 목표 해법은 아니다.

다음 source/ARM 후보의 **통과 상한**을 nonwire 합계1.000ms로 낮춘다: source query/비교/record/seal .350, ARM decode .100, BG 준비/frontier .300, 첫 plan/refill .150, IRQ/poll/CDC .100ms. 206B·1bank·18B prefix 조건이면25.526µs 여유뿐이다. source .350ms 상한은 기존2cycle/byte scan 하한.446364ms보다 작으므로 word 처리나 파이프라인의 실제 포트 처리량 입증이 필요하다. 단순 cursor 공유로 달성했다고 보지 않는다. 실패한340의2.692377ms source+입력 준비와 첫 요청6.969666ms가 이 예산의 실현 가능성을 입증하지 않는다. warm이46B prefix를 유지하면 약85.333µs를 더 써 이 상한도 실패한다. 새 wire가 늘면 예산에서 즉시 빼고, 확인되지 않은 중첩은 더하지 않는다.

제한 일정은 post-ROM **3.180ms 이하**를 위해0.653795ms를 별도로 줄여야 한다. 나머지 앞부분의 필요 이득은3.369199145ms다. 동일 위상은 각각0.653249/7.731283715ms다. 요청을 앞당겼다는 이유로 ROM 주기 전체를 절감량으로 차감하지 않는다. prefix 분할의 전체 추가8wireB+gap=32.381µs와 cold 분할/응답/IRQ도 포함한다. 시작 시각·ROM cycle을 고정한 비교와905→906→907 연속 비교를 각각 보존한다.

## 실제 삭제 구조와 소유권

**host: 하나의 checked-run 실행 경로.** 현재 PREAD/PCAP/PUT/EXPAND325와 MREAD/MCAP/MNEXT/MISSUE의 입력 cursor·literal/반복 진행·출력 주소 갱신을 한 byte 수락 이벤트로 묶는다. descriptor는 opcode별 admission에서 검사한 뒤 destination class/start/span/encoded-end/seed-width로 정규화한다. 기존 metadata run_left/run_zero/manifest_byte, ordinary expanded/lane/별도 next cursor가 새 실행 상태와 공존하면 교체로 인정하지 않는다. 필요한4B seed와 target selector는 명시적으로 비용을 낸다. map batch descriptor 경계, dense/RLE 요구량166/256, H2 길이, 원본 encoded 길이 검사는 남는다.

host 실행기는 queue read 포트를 소유하고 destination class로 staging 또는 expected RAM 쓰기를 선택한다. validator의 실제 SNES read event·CRC·coverage·private receipt 진행은 **독립 소유자**로 남긴다. producer의 완료 카운터를 expected와 actual 양쪽의 증거로 쓰지 않는다. expected 최종 순회와 진행 응답 공개는 실제 소비 및 job drain 뒤에만 허용한다. 동기 RAM 대기·선택 mux·STOP freeze는 새 비용에 포함한다. 현재 expected RAM과 staging의 물리 포트가 하나로 공짜 합쳐지는 것으로 계산하지 않는다.

**source: 전 영역 공통 record 생성기로 map MASK 경로까지 삭제.** 340처럼 map MASK와 nonmap run을 나란히 남기는 후보는 제외한다. 338의 mask_acc/mask_bytes/mask 저장·선택, diff scratch 기록 후 MASK 재순회, 별도 nonmap run offset/seed/lane를 함께 대체해야 한다. 공통 영역 cursor/query-lane/base 비교/run 생성/serial CRC 경로를 사용하고, map SHIFT는 같은 record emitter에 붙이는 제한된 연산으로 남긴다. SHIFT의 이전 base 이웃값·경계·cold 금지 검사와 query 의미 검사는 유지한다. 두 pass의 결과를 다시 byte 주소로 복원하는 기존321/323 구조는 재도입하지 않는다.

source/NES 클록의 query/base RAM과 host 클록의 packet/expected 포트는 별개다. 공통 ISA나 코드 형태를 쓴다고 물리 datapath를 공유한 것으로 세지 않는다. input/output phase RAM 중첩은 COMMIT 이후에만 가능하며, 기존 source transport/CDC/mailbox는 유지 비용399comb를 먼저 예약한다. RAM을 추가하여 로직 감소로 보이는 방법은 whole RAM packing까지 다시 확인해야 한다. 기본 상한은 기존307808bits이며 추가 M9K를 전제하지 않는다.

전 영역 bounded greedy 모델은71프레임 wire32858B지만7프레임 회귀, 최대782B=2.383238ms 추가 wire다. offline DP26385B/회귀0은 구현된 streaming encoder가 아니므로 선택하지 않는다. 공통 generator가 map의 압축 효율을 유지할 수 있는지, literal/skip/shift 선택과 scratch 재사용을 먼저 입증해야 한다. raw4910B를 ARM에 보내 FPGA encoder를 없애는 대안도 wire만14.963810ms라 제외한다(프레이밍·CPU·출력 제외).

## 회로 통과 예산

| 중복 없는 범위 |338 comb|상한|필요 순감소|
|---|---:|---:|---:|
|host|2161|1146|1015|
|독립 validator/aperture|1159|1160|−1|
|queue/SPI|798|600|198|
|source+transport/mailbox|1747|1100|647|
|plan|459|297|162|
|합계|6324|4303|2021|

범위 밖10950을 포함해 whole15253comb, 용량15408 대비155개 여유가 통과 목표다. 상한은 합성 예상치가 아니다. source transport399를 유지하면 encoder 상한701(기존1348)이며, host1146 역시 미입증이다. queue/SPI·plan의360개 감소도 자동 제공되지 않는다. 이 둘을 그대로 두면 host/source 상한만 달성해도 whole15613으로205개 부족한다. 독립 검사를 희생해 부족분을 메우지 않는다.

338 전체22144LE/17274comb/9018FF/307808bits와340 전체22489/17602/9041/307808을 함께 보존한다. 340 source+320,host−13은 새로운 구조의 예산 근거가 아니라 실패 경고다. source FSM은 이미 추출됐으므로 FSM 추출·seed·opcode만 바꾸는 합성 반복은 하지 않는다.

## 다음 실행과 중단 조건

1. **ARM 분리 검증:**338 RTL·336 ARM 위에서 frontier만 추가한다. allocator slot/touch/hit/used·prefix-ready 시각을 실제 M4로 기록하고 slot82의 낮은 구간 상태를 확인한다. lower-slot 반례, exact 중복, retained hit/miss, full eviction,15plan/240B 경계, OBJ 재사용, STOP·generation wrap·credit 부족을 검사한다. 원래 E1/DMA/receipt/최종 ACK를 비교하며 공급 순서가 바뀌면 동등성을 새로 증명한다. 새 RAM/stack/명령·IRQ 비용을 포함한다.
2. **삭제 가능성 검증:** host의 두 run 경로와 source의 MASK/scratch 재순회가 실제로 사라지는 최소 prototype을 만든다.71프레임 exact byte/CRC·cold/raw 복구, 모든 새 admission 오류를 검증한다. 7개 회귀 프레임922/938/941/954/963/970/973의 wire·ARM 비용을 개별 비교한다. 범용 압축 모델의 낙관값으로 통과시키지 않는다.
3. **공동 gate:** 동일 시작·ROM 위상과 제한/정상 연속 일정,2슬롯·SPI·IRQ·staging·ROM 경쟁을 모두 재실행한다. 독립 검사·STOP·최종 ACK·VBlank를 유지한 동일 소스로 whole Quartus Lite MAP 한 번을 수행한다. 시간 또는 면적 상한에 실패하면 선택338/336 유지. FIT/STA는 합리적인 whole 적합 후보 이후이며 자동 merge하지 않는다.

341의 신규 근거는887개 기존 파일 해시 재검증, 실제 warm 첫 패킷 해석,1024건 추상 frontier 검사와 예산 산술이다. 새60fps 이득·회로 절감은0으로 기록한다. production227/GBC164/saveSRAM은 그대로다. 물리 WCET/full ARM RUN/전체65816/실물 지속60fps는 미검증이다.
