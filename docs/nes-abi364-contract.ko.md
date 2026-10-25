# NES364 — host 명령 ABI·descriptor/manifest·queue/plan 교체 범위와 삭제 예산

**source338·ARM355·359 host 및 BG5·OBJ2 선행 읽기를 유지한다. 이번에는 새 ABI의 ARM 변환 비용과 교체 예산을 검증했으며, FPGA 본체를 교체하거나 회로 절감을 달성한 것은 아니다.** 기존 RTL의 바이트 상태를 공유하는 작은 교체를 반복하지 않고, 어떤 해석·소유권·완료 제어를 통째로 없애야 하는지 정한다.

## 전체 Quartus Lite 비용에서 정한 교체 경계

BG5·OBJ2 기준 whole MAP은 **22733LE / 17724comb / 9179FF / 308832bits**다. source·독립 검사·aperture 및 범위 밖 회로를 유지하면 다음 중복 없는 합계가 된다. inclusive parent와 child를 더하지 않는다.

| 경계 | 기준 comb | 이번 설계의 취급 |
|---|---:|---|
| host 자체 | 2063 | descriptor·metadata·payload·DMA·완료 실행의 공동 교체 대상 |
| queue 자체 | 227 | 필드 로더·admission·저장 credit 제어 교체 대상 |
| 공통 SPI | 557 | 기존 source/EA 응답을 보존하면서 새 ingress·status 경계로 교체 대상 |
| plan transport + endpoint | 467 | 373+94; plan loader·발행·반환 제어 교체 대상 |
| **교체 대상 합계** | **3314** | 새 어댑터·포트 선택·CDC·검사를 모두 포함해 **843 이내** |
| source | 1769 | source338 압축·query·전송·CDC 유지 |
| 독립 validator + aperture | 1250 | 1042+208 유지 |
| 나머지 전체 보드 | 11391 | 유지 |
| **유지 합계** | **14410** | 새 교체 비용을 이 위에 더함 |

15408 device 한도만 맞추는 상한은998comb, 여유155개를 포함한15253 목표의 상한은843comb다. 필요한 순절감은 **2471comb, 교체 범위의 74.56%**다. 이는 합격 조건이며 구현 가능한 절감량의 예측이 아니다. 새 RTL 비용은 null, 이번에 실제 삭제한 comb는0이다. 구현 뒤에는 전체 MAP을 다시 측정해야 하며 기존 합계에서 모듈 수치만 빼서 fit을 선언하지 않는다.

host를 전부 무료로 없애도 기존 queue227+SPI557+plan467=1251은843보다408개 크다. SPI557만 그대로 남겨도 host·queue·plan·새 어댑터 전체에286개밖에 남지 않는다. 따라서 공통 헤더를 덧씌우고 기존 parser/plan 본체를 남기는 범위로는 이 예산을 설명할 수 없다. 이미 공유된 SPI bit receiver, CRC16, CRC8 snapshot 회전, NES source/plan cursor는 다시 삭제 이득으로 계산하지 않는다.

## 비교한 명령 형식과 실제 ARM probe

두 형식 모두 제안된0xEB 뒤10B 공통 헤더와 CRC16BE를 쓴다. 헤더는 kind/route/sequence16/body length16/**serial32**다. generation16과 epoch는 검증된 불변 frame admission/H2 문맥에 결합한다. receiver는 새 serial을 임의 패킷으로 받아들이면 안 되며 기존 lease 전이에서만 sequence를 재설정한다. sequence 소진은 거부하고 board reset namespace에는 기존 bus quiescence 조건을 유지한다.

| 항목 | A: 짧은 공통 헤더 | B: 고정 실행 record |
|---|---|---|
| 일반 출력 | start/span4B + 기존 압축 payload | start/span/encoded16 각2B + format/region 각1B + 기존 압축 payload |
| map 묶음 | 기존 tokenbase/count/3B 범위 descriptor | tokenbase/count 유지, 범위마다8B descriptor; 범위 경계에서 분할 |
| manifest | 기존 RLE | ARM에서 display24+requirements166 및 map256을 풀어 offset+dense bytes로 발행 |
| plan | 기존 short/full와 sparse ALT | 16B native header + 고정8×16bit ALT =32B; END/partial BG 표식도 동일 크기 |
| FPGA에 남는 일 | 기존 압축·가변 plan 해석 | 출력 repeat seed의 단일 확장, 모든 bounds/lease/소비 검사, 고정 record 실행 |

B도 출력 repeat2/repeat4 및 HDMA zero seed를 유지한다. 이를 dense DMA payload로 바꾸는 시간 비용을 숨기지 않는다. source MASK·SHIFT는 두 후보 모두 그대로다. source D0..D5, EA28 hint, 실제 SNES descriptor/소비 ABI 및 독립 read CRC·coverage도 변경하지 않는다. native SNES 주소를 ARM이 지정했다는 이유만으로 FPGA의 region/span 검사를 없애지 않는다.

공통 출력 header+body는 기존256B 슬롯 안에 들어가야 하므로 body 상한246B다. B의 map body는240B, dense metadata body는 offset2+data238B로 제한한다. literal240B는 두 record로 나눈다. 47개의2B map 범위는 실제 converter에서 **1→3패킷,259→524B**가 됐고, literal240B는 **1→2패킷,259→282B**가 됐다. 측정한 cold의64B×3범위 묶음은 한 슬롯에 그대로 들어간다. warm map256 manifest는 두 패킷으로 늘었다.

기존 진행 응답13B를 명령 byte 뒤에서 모두 받으려면 최소14B SPI 거래가 필요하다. B의 빈 SEAL record는 encoded13B이므로 CRC 밖의 zero dummy1B가 더 필요하다. 아래 wire 수치는 이를 포함한다. converter는 record 자체를 생성하며 새 receiver의 trailing dummy 규칙과 실제 sender padding은 후속 구현 대상이다. 양의 추가 wire만 청구하는 일정 진단에서는 원래 SEAL19B가 이미 이 길이를 넘으므로 padding을 반영해도 추가 지연은 변하지 않는다.

실제 Cortex-M4/Thumb `-Os` converter는1643text/0data/2576BSS, 전체 관측 최대stack160B다. output2048B와 body512B를 가진 **계측용 별도 helper**이며 실제 firmware에 무료로 더할 수 없다. 직접 serializer로 교체하거나 기존 buffer를 재사용할 때의 RAM 소유권과 절감은 아직 증명하지 않았다. 기존 ARM355 serializer를 유지한 채 converter를 실행했으므로 원래 serializer 비용은 빼지 않았다.

| 후보 | 프레임 | 기존/새 최소 거래 B | 추가 거래 | converter 명령 | 추가 비용 진단 ms |
|---|---:|---:|---:|---:|---:|
| A 짧은 헤더 | 905 | 9495 / 9425 | 0 | 547685 | 6.672440 |
| A 짧은 헤더 | 906 | 9647 / 9556 | 0 | 554450 | 6.737738 |
| A 짧은 헤더 | 907 | 676 / 666 | 0 | 37003 | 0.501464 |
| B 고정 record | 905 | 9495 / 12239 | 0 | 721127 | 17.038940 |
| B 고정 record | 906 | 9647 / 12354 | 0 | 727241 | 16.998964 |
| B 고정 record | 907 | 676 / 1371 | 1 | 83427 | 3.221750 |


warm B의 encoded 증가694B 중 fixed plan이280B, requirements manifest가141B, map manifest가244B다. 나머지 descriptor 증가와 control header 감소를 합치고 SEAL dummy1B를 더하면 실제 최소 거래 증가는695B다. 따라서 FPGA에서 parser를 없애는 후보일 수는 있지만 전송 측면의 최적화는 아니다.

## 실제 ARM·IRQ·2슬롯·ROM 일정에 대입한 결과

기준338/355/359와 BG5·OBJ2를 그대로 실행한다. 각 실제 E1/E9 발행 직전에 해당 패킷을 M4 converter에 넣고, 새 record의 의미를 독립 Python oracle과 대조한다. 계측한 helper 명령을 CPI1/84MHz로, **양의 wire 증가만** byte당256 ARM cycle로 추가한다. 분할 record마다 CS8µs+진행 응답14B+CS8µs를 더한다. 줄어든 바이트와 기존 serializer/새 FPGA의 예상 절감은 빼지 않는다.

**새 ABI가 FPGA에 전송된 검증은 아니다.** 원래 패킷이 실제 old receiver를 통과하며, 추가 비용으로 그 발행 시각을 바꾼 진단이다. 기존 ARM refill·IRQ·polling·2슬롯·ROM 경쟁은 실제로 다시 실행되지만, 새 fragment의 추가 credit 대기·응답 검사 CPU·새 RAM 포트/FSM 지연은 미검증이다. helper 구간의 모든 IRQ 선점과 pad 준비 WCET도 보장하지 않는다. 다음 수치를 새 구현의 처리 시간이나 상한으로 부르면 안 된다.

| 후보/일정 | 프레임 | 기준 ms | 추가 비용을 넣은 ms | 변화 ms |
|---|---:|---:|---:|---:|
| A 짧은 헤더 / 연속 | 905 | 99.270627 | 105.936229 | +6.665602 |
| A 짧은 헤더 / 연속 | 906 | 116.702145 | 115.187117 | -1.515028 |
| A 짧은 헤더 / 연속 | 907 | 12.156081 | 15.812674 | +3.656593 |
| A 짧은 헤더 / 동일 위상 | 905 | 98.643135 | 105.308737 | +6.665602 |
| A 짧은 헤더 / 동일 위상 | 906 | 117.983220 | 123.132976 | +5.149756 |
| A 짧은 헤더 / 동일 위상 | 907 | 12.157717 | 12.563531 | +0.405814 |
| B 고정 record / 연속 | 905 | 99.270627 | 137.990617 | +38.719990 |
| B 고정 record / 연속 | 906 | 116.702145 | 133.328400 | +16.626255 |
| B 고정 record / 연속 | 907 | 12.156081 | 15.512950 | +3.356869 |
| B 고정 record / 동일 위상 | 905 | 98.643135 | 137.363125 | +38.719990 |
| B 고정 record / 동일 위상 | 906 | 117.983220 | 140.841491 | +22.858271 |
| B 고정 record / 동일 위상 | 907 | 12.157717 | 15.242044 | +3.084327 |


warm의 시작과 ROM 공급을 따로 기록하면 다음과 같다.

| 후보/일정 | 시작 ROM cycle | hint fill ms | BG plan/tile ms | OBJ plan/tile ms | E2 poll |
|---|---:|---:|---:|---:|---:|
| A 짧은 헤더 / 연속 | 5790803 | 11.769564 | 11.771791 / 11.772155 | 12.053333 / 12.053606 | 20 |
| A 짧은 헤더 / 동일 위상 | 7368026 | 5.053871 | 7.212345 / 7.212709 | 8.797735 / 8.798008 | 17 |
| B 고정 record / 연속 | 6895121 | 10.305853 | 10.308081 / 10.308444 | 11.295614 / 11.295887 | 18 |
| B 고정 record / 동일 위상 | 7368026 | 5.053871 | 7.785247 / 7.785611 | 9.677588 / 9.677861 | 16 |

A의 같은 위상 변화는 0.405814ms, 연속 변화는 3.656593ms다. A 연속 hint fill은 기준1.682957ms에서 11.769564ms로 밀렸다. 이것을 converter 자체의 실행 비용으로 해석하지 않는다. 기존 패킷의 DMA·plan 의미와 순서는 네 일정 모두 동일했고, polling 횟수는 실제 일정에 따라 변했다. B 연속 warm이 A보다 짧게 나오더라도, 앞선 두 준비 프레임은 B가 합계50.195671ms 더 길다. 그로 인해 달라진 ROM 위상 효과를 B의 처리 효율 향상으로 세지 않는다.

동일 시작 비교는 프레임별 절대 시각과 ROM cycle을 기준과 정확히 맞춘다. 연속 비교는 cold/다음 bank 준비의 종료 지연이 warm 시작 위상에 반영된다. 세 준비/표시 프레임 모두 비용에 포함한다. source 첫 블록 및 EA hint 자체의 준비는 변경하지 않았지만, 앞 프레임 지연만으로 ROM 대기가 달라진다. 각 일정의 차이를 별개 최적화 이득으로 합산하지 않는다.

## 실제로 삭제할 제어와 남겨야 할 책임

| 기존 구조 | 교체할 실행 경계 | 삭제로 세면 안 되는 책임 |
|---|---|---|
| queue 필드 순서 로더 + host HLOAD315/HCHECK315 + 별도 headerwire/active 복사 | CRC가 확인된 ingress가 canonical record를 한 번 만들고 공통 reader가 직접 실행 | serial/sequence/길이/region 검사, CRC 완료 전 공개 차단, 불변 lease |
| DREAD/DCAP/DCHECK 및 map 전용3B 해석·end 주소 경로 | 같은8B descriptor reader와 checked cursor 사용 | 범위 정렬/초과/토큰 단조성, DMA 소비 수와 실제 receipt |
| metadata의 RLE 진행·주소 선택·별도 MREAD/MCAP/MNEXT/MISSUE 흐름 | dense offset record를 공통 RAM writer로 실행 | expected 영역 경계·전체 coverage, 독립 validator RAM 수락, SEAL barrier |
| ordinary PREAD/PCAP/PUT/EXPAND 및 map/manifest별 별도 완료 복귀 | 하나의 포트 요청/반환과 record 완료 경로 | repeat seed 단일 확장, 실제 read event CRC/coverage, private write 완료 뒤 ACK 공개 |
| E1/E9의 admission/header 경로와 queue/plan별 발행 준비 | 같은 수신 record 경계·원자적 publish·status 구성 | EA/source 기존 응답, CRC8 snapshot 안정성, source 전송 및 계획 CDC |
| NES plan short/full/popcount/sparse ALT loader | fixed32B stride reader, 기존 plan RAM·cursor 소유권 유지 | generation·slot/tag 의미 검사, READY/RUN/tile_done까지 descriptor 보존, BG 부분 완료와 frame END 구분 |

위 표는 **삭제 목표 목록**이다. 새 interpreter를 옆에 추가하고 옛 상태들을 보존하는 방식은 합격이 아니다. 새 common reader의 주소 mux·bounds comparator·status snapshot·SNES 어댑터도843 안에 포함한다. descriptor를 고정 길이로 바꿔도 address bounds와 RLE seed 진행은 남으므로 host2063 전체가 공짜로 사라지지는 않는다. A는 기존 가변 해석 본체가 남아 이 삭제 목록을 충족하지 못한다. B는 삭제 범위를 더 넓힐 수 있지만 시간 및 area 동시 달성은 아직 입증하지 못했다.

## RAM·credit·STOP·최종 표시 계약

1. host clock의 queue RAM은 expected0..471, output slot512..767/768..1023을 유지한다. 기존 write guard가472 미만으로 제한한 빈 영역472..503의32B를 **실행 중 문맥의 예약안**으로 둔다. header10+descriptor8+token4+cursor2+remaining/flags2+encoded end2+generation2+bank/reserved2=32B다. 큐 슬롯을 반환해도 이 문맥은 마지막 DMA·receipt까지 보유한다. 저장 credit을 먼저 돌려주려면 필요한 이 보존을 무료로 없애지 않는다. 추가 RAM 인스턴스는 예산상0이지만 context 적재·읽기·publish·주소 선택은 새 회로와 지연에 포함하며 미구현이다. 수신 중 반대 슬롯 쓰기, active record 읽기, checker expected 읽기의 충돌을 새 공통 소유자가 중재해야 한다. 특히 실제 SNES read/CRC 이벤트를 막는 긴 atomic RAM 순회는 허용하지 않는다. metadata expected 쓰기는 CRC/namespace 검사와 frame 취소를 결합하고 완료 전 기대값의 유효성을 공개하지 않는다.
2. plan은 기존2×512B dual-clock bank를 유지한다. host가 완성 packet과 CRC를 확인해 NES에 descriptor를 넘기고, NES는 필요한 필드를 안전하게 보유한 뒤 bank를 반환한다. 마지막 tile 완료와 bank 반환은 같은 사건이 아니다. source338의 입력 단계와 plan cursor 소유권 전환도 유지한다. RAM 절감은0으로 둔다.
3. output **저장 credit**, record 실행 완료, 실제 DMA 소비/receipt, frame 최종 ACK는 분리한다. plan bank credit도 output 2슬롯과 분리한다. 단일 전역 retire 순서에 묶으면 tile을 기다리는 출력 head 뒤에 필요한 plan이 갇힐 수 있다. 공통 ingress를 쓴다는 이유로 이 순서를 합치지 않는다.
4. token은 ARM이 예측 배정하지 않는다. 실제 tile chunk와 DMA 소비 순서에서 기존 FPGA가 배정하며, map tokenbase는 검증된 값만 이어 쓴다. split은 범위를 쪼개지 않고 tokenbase를 앞 범위 수만큼 이동한다. serial·generation·bank 재사용, FFFFFFFF token 소진, credit wrap에 같은 계약을 적용한다.
5. STOP은 partial record publish, payload/expected RAM 쓰기, plan 공개, 새 receipt를 차단한다. source collector 취소·응답 drain과 plan bank 반환을 확인하고 취소된 namespace를 재사용하지 않는다. STOP 뒤 뒤늦은 DONE는 차단한다. 기존 H2/expected와 실제 read CRC·coverage를 독립적으로 유지한다.
6. 마지막 record의 저장/파싱 완료는 최종 ACK가 아니다. 모든 DMA·receipt·checker가 끝나고12개 정확한 display context read와 token 조건을 만족한 뒤, 기존 VBlank 표시/최종 ACK를 거쳐 lease를 반환한다. 기존 ordinary65816 trace와 tile/display model 범위가 유지되며 전체65816 VBlank CPU 실행을 새로 증명한 것은 아니다.

## 판정과 다음 합격 조건

A와 B 모두 새 FPGA 비용을 측정하지 않았으므로 시간·회로 여유의 동시 확보는 **미입증**이다. A 짧은 헤더의 추가 비용 진단은 연속15.812674/고정12.563531ms이며, 두 warm 중 최소60Hz 여유는0.853993ms다. B 고정 record의 추가 비용 진단은 연속15.512950/고정15.242044ms이며, 두 warm 중 최소60Hz 여유는1.153717ms다. 음수는 해당 진단의 시간 초과다. 양수도 미구현 fragment credit·새 포트 제어·전체 IRQ에 쓸 수 있다고 보장한 여유가 아니다. A는 삭제 범위가 부족하고, B의 모든 비용을 감당하면서843comb 안에 들어갈지는 아직 알 수 없다.

후속 구현 범위는 **직접 ARM record serializer + 단일 ingress/record 실행기 + 독립 output/plan credit 소유자**다. 생산자가 다시 legacy packet을 만들고 변환하는 이중 경로를 제품에 추가하지 않는다. 위 표의 옛 host/header/map/manifest/plan 해석을 실제로 삭제한 한 후보만 전체 MAP과 두 일정으로 비교한다. fixed32 plan/전체dense manifest는 이번 비용을 그대로 감수할지 먼저 판단해야 하며, 압축을 다시 선택한다면 FPGA에 돌아오는 decoder 비용을 계상한다. 작은 상태 공유나 측정하지 않은 serializer 절감을 성공으로 간주하지 않는다.

합격은 모든 새 어댑터를 포함한 whole comb≤15253, 전체 RAM 증가 없음, source/EA 마감과 두 일정의 warm≤16.666667ms이며, fragment credit·status CPU·STOP·최종 ACK·VBlank 및 더 많은 warm 프레임의 연속 위상까지 실제 구현에서 확인해야 한다. 상위 firmware foreground/전체IRQ·실물 WCET·full65816·FIT/STA·물리 지속60fps는 여전히 별도 gate다. 현재 새 ABI는 선택하지 않는다. production227/GBC164/saveSRAM은 변경하지 않았다.

검증: 실제 M4 두 형식×두 기준 trace×905..907의 모든 E1/E9, 독립 plan/metadata/map/ordinary 의미 비교,47range/literal240 분할, full8ALT와 END/partialBG,14개 producer/envelope 거부 검사. 비용을 넣은4일정×3프레임에서 read→unit→private RAM→publish,최대2credit·최종12read를 확인했다. 기존 host/validator/queue STOP·token·final 검사와 EA/cache/arbiter68검사는 동일 RTL 해시에 연결해 유지했다. 이를 새 ABI receiver의 검증으로 전이하지 않는다. 이번 RTL은 기준과 모두 같으므로 이전 whole Lite MAP 입력을 재검증했으며 새 MAP/FIT/STA는 실행하지 않았다.

근거: [검증 JSON](../analysis/abi364-verification.json), [계획](nes-abi364-plan.json), [ARM probe](../tools/probe_nes_abi364.py), [결합 일정 진단](../tools/probe_nes_abipath364.py). 원시 소스·로그·disassembly·전송 byte는 probes/nes-abi364에 보존한다.
