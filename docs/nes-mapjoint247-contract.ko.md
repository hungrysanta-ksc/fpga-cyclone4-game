# NES247 P1: map 표현·수신 coverage·전체 비용 공동 비교

2026-10-18, PR128. **8-word mask가 이번 자료에서 가장 작은 wire 모델이지만, 시간·ROM·전체 자원과 두 VBlank 초과가 남아 구현 후보를 선정하지 않았다.** 새6502/65816/ARM/FPGA 제품 코드는 없다. SELECT `mapjoint03`;01의 비교와02의 반례·DMA 하한,03의 초기화 상태 증명·시간 민감도는 같은 기존 자료를 사용하며 모두 보존한다.

[분석기](../tools/analyze_nes_mapjoint247.py) · [공개 요약](../analysis/mapjoint247-verification.json) · [71 frame 표](../analysis/mapjoint247-frames.csv) · [이전 수신 계측](nes-coalesce247-contract.ko.md).

## 실제 변경량과 과전송

observer03의71 map4096B를 이전 표시 및 해당 목적 은행과 각각 비교했다. 두 은행의 stale words를 함께 표시하고 **최종 표시 ACK 뒤 목적 은행만 clear**하는231 수명을 유지한다. 목적 은행4096B 복제는 Python oracle이며 새 ARM 상태가 아니다.

|warm69 합|값|
|---|---:|
|이번 frame에서 새로 바뀐 words|1362|
|해당 목적 은행이 받아야 하는 words|2607|
|이전 변경을 따라잡는 words|1245|
|기존 dirty16B granules|1915|
|기존 전송이 포함하는 words 분량|15320|
|그중 필요 word 외 분량|12713, 약82.98%|

이번 창에서는 causal stale words가 실제 목적 은행과 다른 words와 정확히 같았다. 일반 장면에서 값이 되돌아오면 stale이 보수적으로 더 클 수 있다. 일반적으로 이를 제거하려고 두 은행의4096B 비교 복제를 ARM에 추가하지 않는다.

frame955는 현재 표시와 비교한 변경0인데 목적 은행에는76words/100bytes가 아직 다르다. 현재 frame 변경만 보내면 틀리는 실제 반례를 다시 확인했다. 기존225 원형 map이나231 dirty 수명을 새로운 개선으로 세지 않는다.

## 비교한 표현과 독립 복원

새 word 형식은 패킷마다1B 식별자를 비용에 포함하고 record를 나누지 않으며 총 payload≤240B로 묶었다. 각 레코드의 주소 순서는 frame 전체에서 엄격히 증가한다.

|형식|한 레코드|비교 의미|
|---|---|---|
|current16|기존 연속 dirty16B, 최대240B|실제 C 패킷 기준|
|batched16|offset2B+값16B, 최대13개|이미 분석한 목록형16B 기준|
|row64|변경이 있는64B 행 전체|기존16B 소비 경로로 행 전체를 전송하는 대조군|
|pairs|byte offset2B+word2B|word별 주소|
|mask8|granule index1B+mask1B+선택 word들|16B 범위의8words를 직접 mask로 표현|
|mask32|row index1B+mask4B+선택 word들|64B 행의32words를 mask로 표현|

3개 word 형식을 별도의 parser로 복원해 **213 maps/872,448B exact**를 확인했다. 범위·순서·중복·잘린 값·형식·누락/역순 manifest·목적 은행 초기화 등의 Python 반례34개를 거부했다. 실제 C/65816 decoder, CRC 오류/STOP 하드웨어 시험 또는 assembly 크기 통과라는 뜻이 아니다. cold2 frame도 전체 words를 이 형식으로 복원했으며, cold 최적화나60Hz 승인은 하지 않는다.

mask8의 mask는 word별 received bitmap의 한 byte에 직접 대응한다. 따라서 bitmap 검사·갱신에 그 mask를 사용할 수 있다. sparse 값 저장과 경계 검사·STOP service는 여전히 필요하며, 새 decoder 시간을 기존 mark 시간에서 임의로 빼지 않는다.

## 누락 검증과 초기화 상태를 같이 계산

word 수신 bitmap은256B로, 기존 map32B보다224B 크다. 기존 SEAL222B에 이를 그대로 교체하면 **446B>240B**다. 모델에서는 다음 비용을 명시했다.

1. 기존 map32B를 뺀 SEAL190B.
2. word manifest256B를240+16B의 두 패킷으로 전송. 주소 field로0→240 순서를 검사하고 수신 bitmap과 정확히 대조한다.
3. 총256B 검사가 완료된 뒤에만 SEAL/DMA 허용. 부족·중복·다른 word 수신은 실패하며 warm에서도 생략하지 않는다.

추가 wire는256+2×19−32=**262B/frame**, 준비 확인 비용은 별도로 모델에 반영했다. expected manifest256B의 추가 복제는 필요 없고, 각 조각을 이미 받은 bitmap과 즉시 비교하는 가정이다. 실제 새 버전/dispatch·sequence·epoch·CRC·완료 cursor·STOP·finalACK 연결은 구현 전이다.

ARM은 두 stale maps가 각각32→256B가 되어 **상주448B 추가**다. 이전233 margin1616−448=1168B,1024B gate 위144B는 산술값일 뿐이다. 새 입력 RUN/IRQ, decoder/packet 구성 stack 등을 통과한 여유가 아니다.

SNES의 received+두 target-valid maps를 모두 word bitmap으로 바꾸면 **672B 추가**다. 다만 map에는 다음 불변식이 있다.

- reset 직후 각 은행의 map은 미초기화다.
- 성공한 표시가 되려면 해당 map4096B 전체가 유효해야 한다.
- 따라서 성공한 표시 사이에 보존되는 map 유효성은 “전부 미초기화/전부 초기화” 두 상태다. sparse pattern의 유효성에는 이 축약을 적용할 수 없다.
- 첫 map에서 모든 words의 receipt가 있어야 초기화를 인정한다. 최종 displayACK 전에 초기화 상태를 공개하지 않는다. 부분 실패에서는 다음 BEGIN을 허용하지 않고 common STOP/reset이 양쪽 기준을 버려야 한다.

213번의 목적 은행 검사에서 이 불변식을 확인했다. 두 target-valid maps를 두 bit로 나타내면 map 관련 **추가 논리 저장량은161B**가 된다:received +224B, 기존 target-valid64B 대신 flags1B. 여기에 manifest cursor/완료 최소3B와 순서 상태 최소2B 등이 필요하다. 실제 정렬·주소 배치·assembly 크기를 검증한 allocation 결과는 아니다.

반대로 sparse word 하나를 받았다고 기존16B 전체를 초기화하면 안 된다. 각256 granule에서 첫 word만 받은 예는 coarse bitmap이 모두1이어도1792words가 미초기화다. 이 반례는 거부했다. 초기화 flag가1인 warm에서도 received==manifest 검사는 계속 수행한다.

## 이전 wire 가정을 실제 계획 길이로 갱신

이전231 계열 wire 모델에는32B 고정 계획과7개 배치의 보수적 비용이 남아 있었다. 이번에는 이미 검증한 ordinary196/199 길이, 실제15개/240B 배치, 배치 정렬 뒤193 chunk 수를 대입했다. 입력은 앞선 의미449B raster+rowshift 모델을 유지한다.

warm 계획/배치 비용 합은16,347→5,192B, pattern chunk 수는187→166이다. 이것은 새 실행 속도 개선이 아니라 **모델 가정 갱신**이다. 실제 전체 shared SPI trace나 runtime 상한으로 바뀐 것이 아니다. ready4/ready1의 반복 대기와 CPU 시간은 여전히 별도다.

|형식|ready4 최대B|ready1 최대B|warm DMA charge 최대|4192 초과|
|---|---:|---:|---:|---|
|current16|5017|5617|4336|952/955/963|
|batched16|4435|4615|4336|952/955/963|
|row64|5851|6151|4448|7개|
|pairs|4159|4339|4308|952/955|
|mask8|**4095**|**4275**|4308|952/955|
|mask32|4155|4335|4308|952/955|

word3형식은 위 manifest262B와 추가 준비 확인까지 포함한다. mask8의 map-data wire 합10,564B+manifest 순증18,078B=28,642B는 기존 map64,357B보다 약55.50% 작다. 전체 map 행을 보내는 row64는 ready4에서도4개 frame 초과여서 이 자료의 해결책으로 남기지 않는다.

## 아직 닫히지 않은 시간·DMA 경계

mask8의 최악 frame954는 wire와 실제 측정한 **map 이외 mark만** 제외해도 새 map decode+coverage에 낙관적으로 **1.47114ms**가 남는다. source·ARM·복사·대기·DMA·표시 비용은 아직 제외돼 있다. 기존 coverage1.79557ms를 유지하는 조건부 시나리오면 이미 **0.32443ms 초과**, 새 map decoder 시간은 더하지도 않은 상태다. 이는 재작성한 coverage의 하한이나 전체 파이프라인 불가능 증명이 아니다. 3936B ROM과 실제 전체 decoder/coverage 시간을 함께 확인해야 한다.

DMA는 word 쓰기 집합에서도 남는다. 독립 partition DP로 map 최소 charge를 확인했다.

|frame|word map 최소|현재 배치 pattern|pattern 순서만 자유롭게 한 최소|raw|fixed|현재 합/순서 완화 합|
|---|---:|---:|---:|---:|---:|---:|
|952|1988|1216|1088|144|960|4308 /4180|
|955|2006|1024|1024|208|960|4198 /4198|

952의128 차이는 batch 사이 순서를 자유롭게 한다는 가정이며 그 저장·정렬·시간·코드를 구현하지 않았다.955는 그 가정을 넣어도6 초과다.4192/96/fixed 정책을 임의로 낮추거나6을 반올림해 통과시키지 않는다. 새 표현은 source 전체LE/LAB/mapper 여유도 해결하지 않는다.

## 판정과 다음 경계

mask8은 **wire 비교의 우선안**이다. P2 또는 다음 제품 구현 후보는 아직 없다. 다음은 하나의 완전한 map 수신 경계에 대해 mask 기록·manifest 완료·초기화 flag·기존 pattern/raw coverage·STOP·최종 ACK를 함께 설계하고,3936B 및 실제 decode+coverage 시간의 가능성을 확인한다. 단독 mask opcode 반복, 범위 마스크3971/3950B의 미세축소, 기존193 묶음 재시험으로 바꾸지 않는다.

동시에952의 순서 비용과955의 잔여 전송을 final display 소유권 및 전체 일정에서 해결할 근거가 필요하다. source449B/rowshift의 whole-board LE/LAB/mapper, 새 입력 ARM RUN/IRQ, firstfault·CDC/IO·commit/lease/retire가 열려 있으면 최소 decoder 통과만으로 FIT/실기에 가지 않는다. 생산227·기능 기준240 미배치·기각241/246·GBC164·save SRAM과 모든 과거 근거를 보존했다.

## 재현

```text
python tools/analyze_nes_mapjoint247.py --observer <observer03> --prior <analysis06/result.json> --coalesce <coalesce-analysis04/result.json> --order <order-model01/result.json> --relocation analysis/relocation247-frames.csv --out <new-analysis-directory>
```

공개 파일에는 source와 수치만 있다. 게임 map·그래픽·ROM·trace는 private 입력에 남는다. 결과의 UNKNOWN은0비용이 아니다.
