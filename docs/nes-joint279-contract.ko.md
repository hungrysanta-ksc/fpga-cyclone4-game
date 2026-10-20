# NES279 — ROM 위상 원인, OAM DMA와 source/제어 공동 비용

PR130 / `codex/nes-wholepath-boundary-256`. 기준은 NES278의 실제 71프레임과
전체 Quartus Lite MAP이다. 이번 단계에서는 실제 65816 OAM 후보를 측정하고,
같은 RTL·ARM에 새 CPU trace를 연결한 905~907 일정을 확인한다.
source 전송 대안은 원본 데이터 복원과 비용 계산이며 새 RTL/ARM decoder가 아니다.

## ROM 경쟁 회귀의 원인

276→278의 제한 ROM 프레임 907은 출력 구간 시작이 **212.224714µs 앞당겨졌다**.
끝나는 절대 시각도 **44.454µs 앞당겨졌지만**, 구간 길이는 167.770714µs 늘었다.
앞 프레임이 빨리 끝나 다음 프레임의 대기가 더 많이 보이는 현상이다.
개별 구간 증가를 전체 3프레임 처리의 회귀로 해석하면 안 된다.

ROM fixture의 사용 가능 구간은 프레임 시작마다 초기화되지 않는다.
NES 클록의 전역 `romcycle`에서 주기 357,368, 열린 구간 [330,088,354,640),
12사이클마다 한 slot을 사용한다. core 요청은 120사이클마다 우선 처리한다.
이것은 실제 core 실행이나 실기 ROM의 WCET가 아닌 명시적인 경쟁 fixture다.

- 907의 tile 160B와 누적 ROM/core 응답 수는 같다. ROM 완료 marker의 시간은
  이전 [258.970964,259.012975]ms와 변경 후 [258.968620,259.010632]ms 사이로
  추적된다. marker 자체에 timestamp가 없으므로 정확한 완료 시각을 만들지 않는다.
- 열린 slot을 기다린 횟수는 4,684 NES 사이클 증가했다. core 우선 경쟁은
  1회 더 발생했으며, upstream tile 대기는 총 4,685사이클 늘었다.
- E2는 236→240회, SPI는 +36B, ARM/IRQ event 명령은 +2,189개다.
  이 차이의 비용은 167.773810µs이며, 관측 구간 차이와 남는 차이는 약 -3.1ns다.
  이 일치는 비용 귀속이다. poll 네 번을 단순 삭제해 같은 대기를 없앨 수 있다는 뜻은 아니다.

276→278의 제한 ROM 세 프레임 절대 종료는 265.001456→264.957002ms다.
앞으로는 구간 길이, 시작·종료 절대 시각, ROM slot 위상, 입력·출력 거래 수를 함께 비교한다.
E2 wire를 없애고 같은 준비 대기를 CPU idle로 바꾸는 것만으로는 처리 시간이 회수되지 않는다.

## 실제 65816 OAM 후보

기존 op8/section4의 `00 f0 00 00` 패턴을 WRAM에서 MVN으로 늘리던 경로에
정확한 패턴 전용 ROM→WRAM DMA를 추가했다. WRAM 내용을 유지한 뒤 기존
WRAM→OAM DMA와 ordered ACK를 수행한다. WRAM→WRAM DMA는 사용하지 않는다.

패턴, opcode, section, 길이 4B, 출력 길이 4의 배수/1~512B를 모두 확인한다.
조건이 다르면 기존 일반 경로를 실행한다. ROM template는 512B, 새 코드 증가는
130B다. 커널은 코드 783B + zero 1B + template 512B = 1,296B다.
기존 보드의 4,096×8 program ROM 범위에 들어가는 커널 용량 계산이며,
전체 표시 프로그램을 통합·합성했다는 뜻은 아니다.

동일 544개 패킷의 WRAM 128,041B와 CGRAM/OAM DMA 결과를 확인했다.
template 순차 ROM 읽기와 WRAM DMA 바이트 수도 직접 계수했다.
기존 HDMA zero 채우기 2회와 bank 재사용 동작을 유지했다.

프레임 954의 OAM 명령 자체는 0.825244ms 짧아졌다. 다른 명령에 추가된 분기·refresh
위상 변화까지 포함한 일반 CPU 명령 합계의 **순이득은 0.779056ms**다.
큰 OAM 명령 하나의 절감만 전체 비용에서 빼지 않는다.

별도 실제 CPU 검사에서는 packet DMA 중, template DMA 중, copied 직후,
일반 MVN 중, 부분 ACK, 짧은 STOP, 실행 직전의 7개 STOP을 확인했다.
10개 명령이 재시도 후 정확한 WRAM을 만들고, invalidation clear 8회,
stale ACK 거절 1회를 확인했다. 비일치 패턴 두 개는 일반 경로로 복귀한다.
STOP endpoint는 모델이므로 새 live CPU/FPGA 동시 실행 증명과 구분한다.

## 같은 RTL·ARM에 OAM 후보를 연결한 결과

|조건|프레임|278 진단 시간|279 진단 시간|차이|E2 이전→신규|
|---|---:|---:|---:|---:|---:|
|일반|905|63.489965ms|62.647748ms|-0.842217ms|137→117|
|일반|906|51.566199ms|50.724482ms|-0.841717ms|155→135|
|일반|907|11.529453ms|10.560373ms|-0.969079ms|77→54|
|제한 ROM|905|90.225463ms|89.383291ms|-0.842172ms|354→334|
|제한 ROM|906|114.266947ms|113.913815ms|-0.353132ms|1124→1102|
|제한 ROM|907|18.372461ms|18.578732ms|+0.206270ms|240→245|

제한 ROM 3프레임 절대 종료는 264.957002→263.967969ms다.
새 CPU trace를 실제 ARM/refill·IRQ/polling/tile ROM과 연결했다. RTL과 원본 E1 packet, source block은 278과 같다. map/tile/final display는 기존 모델이다. 이번에 다시 실행한 일정은 3+3프레임이며, heavy954/전체71의 새 일정이나 full RUN·실기60fps 검증은 아니다.


## source 전송 전체 비용

954는 source payload 1,758B, block 9개, 준비되지 않은 D0 4회다.
총 1,969 SPI 바이트와 32거래는 6.256762ms이며 관측 source 6.254970ms와의 차이는
최종 D3의 SS tail/카운터 샘플 시점 약 1.792µs다. 같은 계산을 71프레임에 대조했다.
source의 prepare/blocked/WAITACK 카운터는 이 SPI 일정과 겹친다.
WAITACK 23,272사이클 전부를 별도 낭비 시간으로 빼지 않는다.

검토한 교환 형식은 다음과 같다. 새 wire RTL이나 ARM 실행은 아직 없다.

- 8B 요청 prefix: 명령, 이전 block token, generation, flags, CRC8, tail.
- 5B 동결된 응답 header: 상태, 길이, token16, header CRC8.
- 준비된 경우 payload + 기존 payload CRC16 2B. 준비 전 응답은 총 13B다.
- 이전 block의 CRC 검증 후 POP을 다음 READ 요청에 넣고, 마지막 POP·input COMMIT은
  별도 8B 요청으로 남긴다. input COMMIT을 최종 표시 ACK와 합치지 않는다.
- 전체 prefix 검증 전 POP 금지, 부분 응답은 다음 block 소비로 취급하지 않기,
  정확한 read coverage, generation/token/wrap, STOP·epoch 재시작 규칙이 필요하다.
  header CRC와 payload CRC를 무료로 합치거나 ACK 의미를 약화하지 않는다.

현재 D0/D1/D2 3거래를 한 교환으로 줄여도 빈 응답은 8→13B로 커진다.
이 비용까지 세면 954의 source 절감은 0.192762ms다.
여기에 raw의 6비트 포장을 더해도 전체 조건부 계산은 16.764427ms로 약 97.760µs 부족하다.

## 우선 비교할 source 후보: raw도 기존 MASK 차분으로 통합

현재 raw 512B는 매 프레임 모두 보내지만, warm 69프레임에서 이전 source 프레임과
달라지는 값은 2~22개다. 954에서는 같은 64B 구간의 3개 값만 다르다.
기존 geometry의 `block id + bitmap + changed values`를 raw에도 적용하면
raw record 3개/521B가 record 1개/12B로 줄어든다.

각 raw block은 64B다. block id 68~75, bitmap 8B, 달라진 값 바이트를 사용한다.
별도 6비트 포장기는 추가하지 않는다. 전체 원본 36,352B의 71프레임 복원을 대조했고,
CRC 일치만으로 동일성을 추정하지 않았다. 중복/역순 block, 범위, 길이,
6비트 값 위반, cold coverage 누락, raw0 뒤 stale delta 등을 모델에서 거절했다.
이 8개 모델 거절 사례는 RTL STOP 검사로 계산하지 않는다.
반대로 cold raw는 8개 전체 bitmap block으로 584B가 되어 기존 521B보다 63B 크다.
이 비용도 905의 후보 payload 계산에 포함했다. warm 절감률을 cold/reset 경로에 적용하지 않는다.

FPGA 입력 base는 현재 4,608B 중 4,398B를 쓴다. raw 512B를 이어 붙이면 4,910B가
필요하므로 `base_hi`를 512×8→1,024×8로 늘린 5,120B 배치를 검토한다.
현재 Lite 보고서는 이 배열을 single-port M9K로 추론한다. 논리 RAM은 4,096bits 늘고,
같은 M9K 용량 안에 들어갈 것으로 계산되지만 **새 합성으로 물리 RAM 수를 확인하지 않았다**.
ARM에 별도 입력 raw history가 필요하면 최대 512B를 추가로 청구해야 한다.

이 cache는 바로 전 **입력 source serial**의 상태이며 SNES 표시 bank 재사용과 다르다.
기존 epoch/base serial 검사를 유지하고, STOP·입력 거절·epoch 변경·raw 개수 변경 시
raw를 cold로 보내야 한다. raw0→2에서는 과거 표시 bank나 CRC만으로 값을 복원하지 않는다.
geometry trailer와 raw 범위, 새 frame CRC, source commit 이전의 잠정 base 갱신,
query response 검증도 새 N5 버전의 ARM/RTL 양쪽에서 연결해야 한다.

없앨 대상은 별도 RAWASK/RAWWAIT/RAWCHECK와 raw gather/offset 전송 제어다.
기존 FETCH/FSTORE/MASK/base RAM 흐름을 확장하되, geometry span 의미와 raw coverage는
분리해서 유지한다. 7bit block id는 75까지 표현할 수 있다.
기존 fixed NES A/host B 포트 계약을 유지하며 새 클록 mux나 RAM 제3 포트를 추가하지 않는다.

|954 조건부 비교|시간|16.666667ms 대비|
|---|---:|---:|
|278 기준 진단|18.180055ms|+1.513388ms|
|OAM CPU 순절감만 반영|17.400998ms|+0.734332ms|
|OAM + source D0/POP 비용 전부 0 가정|16.688618ms|+0.021951ms|
|OAM + 비용을 센 교환|17.208237ms|+0.541570ms|
|OAM + 교환 + raw 6비트 포장|16.764427ms|+0.097760ms|
|OAM + 교환 + raw MASK 차분|15.495856ms|-1.170811ms|

마지막 후보는 954 source payload 1758→1249B, block 9→6개, 거래 32→11회다. source wire/setup 조건부 절감 1.905143ms와 CPU 순절감 0.779056ms를 더하면 계산상 여유는 1.170811ms다. warm69개가 이 고정 횟수 계산에서는 한도 이내지만, 실제 새 경로의 최악 시간은 아직 모른다.


모든 조건부 시간은 기존 poll 횟수와 ROM 위상을 고정한 계산이다.
예컨대 raw MASK 공동 후보에서 source 빈 응답이 10회 더 생기면 약 0.476190ms가
추가된다. ARM source decode/CRC·RAM 접근·CDC·경쟁 변화·full RUN 비용도 별도다.
새 source와 전체 heavy 프레임을 연결하기 전에는 60fps 수치로 사용하지 않는다.

## 전체 회로 예산과 교체 경계

기준 whole Lite는 17,815 combinational functions로, 장치 한도 15,408보다
2,407개 많다. 새 MAP은 실행하지 않았다. 실제 회수로 확정한 논리 수는 0이다.

|대상: 서로 겹치지 않는 own count|조합 논리|
|---|---:|
|source/query codec|1,399|
|source transport + 그 CDC|334|
|이미 공통화된 SPI front|512|
|plan endpoint/transport + 그 CDC|711|
|host output 실행기 own|2,486|
|output queue|174|
|독립 validator|1,063|
|위 전체|6,679|
|나머지 보드|11,136|

source+transport+SPI의 2,245개를 전부 없애도 whole은 15,570개로 **162개 초과**한다.
따라서 source 압축이나 polling만 고쳐 회로 목표를 달성한다는 주장은 성립하지 않는다.

source transport·공통 SPI·plan control·host output·queue를 함께 교체하는 경계는
4,217개다. source/validator를 유지한다면 새 공통 엔진은 **1,810개 이하**여야 한다.
raw cache/decoder, ROM 통합 등의 추가 논리는 이 예산에서 더 차감한다.
source와 validator까지 포함한 전체 6,679개를 재구성한다면 새 합계는
4,272개 이하가 되어야 한다. 이는 필요한 예산이며 합성 절감 추정값이 아니다.

공통 엔진은 세 endpoint의 요청 해석·RAM 주소 진행·CRC/완료 응답을 교체해야 한다.
기존 SPI sampler/CRC8은 이미 공통이므로 같은 절감을 다시 세지 않는다.
source의 NES→host immutable block, output의 SNES 소비 ACK, plan의 NES tile 소비는
각각의 완료 의미를 유지한다. 특히 plan refill과 output은 동시에 살아 있으므로
상태 하나로 합치는 것만으로는 안 된다. 별도 live context와 bounded arbitration,
각 RAM의 고정 클록·포트와 source/plan CDC를 새 엔진 비용에 포함한다.
source/plan/output RAM을 한 RAM으로 바꿨다고 가정하거나 검증기를 삭제해 예산을 맞추지 않는다.

## 판단과 다음 검증

OAM DMA는 실제 CPU와 연결된 일정으로 확인하되, source 교환/차분 및 회로 절감은
아직 후보다. 우선 비교할 경계는 **OAM DMA + raw MASK 재사용 + 공통 교환/완료 제어**다.
6비트 포장만 추가하거나 E2 간격만 조정하는 최적화는 전체 예산을 해결하지 못한다.

다음 구현은 raw cold/reset/STOP과 ARM source decode를 먼저 실제 패킷에 연결하면서,
기존 endpoint·plan/output 제어를 대체해야 한다. 같은 whole Lite MAP에서 추가 RAM·
CRC·포트 중재까지 포함해 4,217→1,810(또는 확장 경계 6,679→4,272)을 확인하고,
heavy 952/954/955/962/963/968/970 및 71프레임을 실제 polling/ROM 위상으로 다시 실행한다.
회로 또는 전체 일정이 목표를 넘으면 이 경계를 채택하지 않는다.
FIT/STA·full RUN·active VBlank·물리 보드 검증은 여전히 남아 있다.
production227/GBC164/saveSRAM은 유지한다.

선택 증거: cpu02/guards01/test01/window01/analysis04. cpu01은 같은 ROM의 초기 PASS이며 cpu02에서 template 읽기/쓰기 계수를 추가했다. analysis01은 포장 비교, analysis02는 raw MASK 비교를 보존했다. analysis03은 CRLF source 로그와 LF로 구성한 문자열의 비교가 실패했으며, 전체 37개 원본 행이 동일함을 확인하고 최종 analysis04에서 줄 단위의 정확한 비교로 수정했다.
