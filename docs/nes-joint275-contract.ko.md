# NES275 — 실제 참조 전송과 descriptor 결합, 교체 비용

실제 ARM이 참조 프로그램을 SPI로 보내고 FPGA가 이를 실행하는 경로를 연결했다.
SNES가 읽는 원본 descriptor와 FPGA receipt/hash/manifest 참조의 일치를 검사한다.
이 후보는 기존 일반 명령 해석 루프와 queue의 중복 길이·CRC 수신 제어를 대체했지만,
source/query/core는 유지한다. 단일 source/receipt/parser FSM 완료로 해석하지 않는다.

## 같은 descriptor와 데이터에 결합하는 방법

E1 wire는 `command + [00, logical_length-1, original_packet, program] + CRC16BE`다.
프로그램이 없는 H2/BEGIN/map/OAM 등의 packet은 원본 형식을 유지한다.
queue는 SS 종료 시 실제 바이트 수와 CRC zero residue를 확인하고 슬롯을 공개한다.
논리 header의 길이·identity는 flow가 검사한다. 이전 payload_size16/received_crc16
레지스터와 header 길이에 따른 별도 CRC 수신 분기를 제거했다.
CRC는 오류 검출이며 인증이나 충돌 없는 증명으로 취급하지 않는다.

SNES aperture에는 원본 packet만 공개한다. 길이·header·payload·ordered ACK는
기존 65816 코드가 읽은 값과 같다. SNES 일반 명령의 reference는 원본 read coverage와
ordered ACK 뒤에 실행한다. 내부 manifest는 SNES 재읽기·ACK 없이 처리한다.
tile은 실제 staging read/token consume을 먼저 확인한다. map은 기존 per-range
DMA/token/receipt 경로를 유지한다. queue head와 credit은 프로그램 완료까지 유지한다.

range(first,count)는 원본 명령의 section/address/length와 현재 진행 위치에서 계산한
범위와 정확히 일치해야 한다. opcode의 문법만 맞는 잘못된 receipt는 거부한다.
hash의 offset/pattern/count/start도 같은 descriptor와 H2 scroll/raw 문맥에 결합한다.
manifest는 원본 held payload를 읽는다. RLE는 원본 token의 count/zero/literal과
reference를 대조하므로 ARM이 생략하거나 다른 주소를 주장할 수 없다.
SEAL은 hash 완료·certificate·최종 finish의 정해진 순서를 요구한다.

추가 packet RAM이나 mailbox는 없다. 기존 host flow FSM, READ/CAP 경로,
24bit event mailbox, map 단계가 끝난 cursor/header16..20을 사용한다.
기존 OTILE의 granule 반복과 OSELECT/ODATA/ORLE/OCHECKNEXT/OCERT/OFINISH 처리를 제거하고,
program fetch/decode/reference read/descriptor 검사를 넣었다. 기존 shared core의
source/receipt 42-state FSM과 query, map staging 및 실제 최종 display 검사는 남는다.

## 기능 및 시간

ARM71프레임/1231패킷이 256B 이하이며, 실제 SPI E1 bytes와 standalone ARM 결과가 모두 같다.
source83240B/map124묶음2069범위13406B/map·tile DMA26350B를 유지한다.
각 프레임 metadata8570B/receipt754B/CRC64B를 대조했다. 일반65816 trace544개,
논리 출력128041B(재사용 포함),PPU DMA39648B/223회,bank zero DMA2회/2200B는 기존274와 같다.

|조건|274|275|차이|
|---|---:|---:|---:|
|frame905|63.615873ms|64.804541ms|+1.188668ms|
|frame906|51.692289ms|53.107999ms|+1.415710ms|
|frame954|18.222145ms|19.187997ms|+0.965852ms|
|제한 ROM907|18.246508ms|17.522699ms|-0.723809ms|

정상warm 초과는7/69개이며, 최대 진단 부족은2.521330ms다.
frame954의 추가 reference wire는226B다.
E2는110→106회이고,전체SPI는2748→2938B(+190),ARM·IRQ event명령은
200937→236117(+35180),transaction은4회감소했다. 같은SPI속도/CPI1 조건에서
wire+명령+transaction 차이0.965857ms가실제0.965852ms 차이와약5.1ns 차이로맞는다.
새로목표를넘은frame938은16.350395→17.545789ms다.
전체추가E1 wire는13385B(프로그램12023B+prefix1362B)이며전체SPI증가는11369B다.
제한 ROM3프레임의 절대 종료시각은264.959866→265.316862ms,
차이+0.356996ms다. 907만0.723809ms 빨라졌지만,앞두프레임이
합계1.080805ms 늦어졌다. 대기 위치 이동을 독립적인 처리량 이득으로 계산하지 않는다.

ARM standalone text/BSS는5866/392B,full 실험 link는6498/684B다.
기존274 full4206/612B보다2292text/72BSS 증가했다.
관측 stack은 standalone336B/full336B다.
208회 IRQ 본문 실행을 포함하지만 full RUN/NVIC stack 상한은 아니다.

시간은 기록된 plan을 입력으로 받은 실제 ARM serializer/reference producer 명령을
CPI1/84MHz로 진행시키는 동일 직렬 진단이다. ARM 화면 계획 전체를 재실행한 결과는 아니다.
실제 refill/IRQ 본문, SPI/queue/core/tile ROM arbiter, 기존 actual65816 일반 명령
bus trace를 같은 일정에서 실행한다. 실제 full RUN/NVIC, 코어의 실제 ROM 부하,
전체65816/active VBlank/whole pixel/실기60fps 상한은 검증하지 않았다.
ARM E0/E2 polling은 실제 실행 횟수를 세었다. SNES ready 탐지와 map/tile/final display는
기존 버스 모델이며,대기 중65816 polling 전체의 실행 상한은 아니다. 일반65816 trace는
forced blank 실행 자료다. ROM 경쟁도 실제 arbiter에 넣은 모의 core 요청이다.
새 SNES ROM이나 새 실제 CPU 캡처는 없으며, 동일 논리 view에 대해 기존 trace의
모든 read byte와 ACK를 대조했다. 전체 실기 비용 full_path_ms는 null이다.

## 같은 whole-board Quartus Lite 비용

|항목|270/274 기준|275 inline 교체|차이|
|---|---:|---:|---:|
|LE|22487|22898|+411|
|조합 논리|17680|18130|+450|
|FF|8892|8877|-15|
|RAM bits|303712|303712|0|
|15408 대비 조합 논리 부족|2272|2722|+450|

queue는282→174comb(-108), output의 own 제어는2206→2798(+592)다.
core는 소스 RTL이 같지만 최적화된 연결 경계에서2448→2451(+3)이다.
직접 교체한 queue/output own 합계는+484이며, 나머지 계층의 합성 최적화 차이는-34다.
그 합계가 whole+450이다. core의+3도 나머지 계층에 포함한다. RTL을 바꾸지 않은
계층의 변동을 구조적 절감으로 주장하지 않으며, inclusive parent와 child를 중복 합산하지 않았다.
board flow에는270부터 있던tile_closed267 출력/assign2줄이 simulation과 다르다.
270과275 모두 그2줄만 제외하면 실행 flow와 정확히 같고,queue는byte-identical하다.
이 기존 board 연결을 유지한 경계끼리 합성했다. core/flow FSM은 정상 추출됐다. FF 감소나 RAM 유지가 면적 게이트 통과는 아니다.
FIT/STA는 실행하지 않았다. 기존 whole490LE/40LAB 배치 실패가 해소됐다고도 주장하지 않는다.

## STOP 및 반례

ARM은 기존 오류12개·frame preflight6개·split bounds16개·늦은 RLE 오류1개와
credit wrap65530→54/60패킷/max4credit을 실제 통합 ELF에서 검사했다.
RTL guard19개: 기존 STOP·조기 최종ACK·불완전 display read·stale ACK와
새 range first/count 위조,참조 offset/pattern/hash identity 오류,manifest 범위초과,
inline 길이·opcode 오류,CGRAM→OAM 재지정,operand/hash/ACK 이후 STOP을 거부했다.
변형 패킷은 SPI CRC를 재계산했다. fault 뒤 lease·최종ACK·stale ACK 차단과
1024B 공유RAM의256cycle freeze를 확인했다.
SPI 검사171개는0/15/16/255/256/257B 경계,CRC 단일비트144개,
4credit·counter wrap·부분 바이트·full queue overwrite·기존 source/plan CRC를 포함한다.

오류 guard의 SNES consumer는 모델이다. 새로운 CPU/RTL STOP 동시실행 증거는 아니다.
중간 실패 arm01(namespace),test01(old queue framing),test02(diagnostic begin/end),
test03(internal oracle prefix view),guards01(RLE tail 길이 가정)은 원본 로그와 함께 보존한다.
guards01의17 PASS는RTL·TB·원본입력 해시가 같은guards02에 재사용했고,추가2개RLE검사를 실행했다. test01은 실제 이전
queue framing 불일치이며, 나머지는 검사 하네스 오류다. 기존 생산 경로 오류로 분류하지 않는다.

## 판단과 다음 경계

참조 프로그램을 덧붙이는 표현은 이 교체 범위에서 시간·회로 최적화로 채택하지 않는다.
실제로 제거한 제어가 있지만 descriptor와 별도 프로그램의 일치를 증명하는 비용이 더 크다.
검증된 STOP/descriptor 결합 규칙은 남기되, 별도 reference byte stream을 유지하면서
개별 opcode·FF·FSM 인코딩·FIT seed를 조정하는 작업으로 이어가지 않는다.

다음 비교는 원본 DMA descriptor 자체가 공통 실행 descriptor가 되도록 두 표현을
하나로 줄이는 경계다. source/query/CRC/receipt의 읽기·진행·복귀 소유권까지 실제로
대체할 구조가 나와야 한다. queue의 부분 절감을 whole gate 해결로 계산하지 않는다.
270/274 비용과 비교할 제거 목록·RAM 포트·CDC·실제 ARM/wire 비용을 먼저 고정하고,
두 게이트를 만족할 근거가 없으면 역할 또는 전송 형식 재설계로 돌아간다.
production227/GBC164/saveSRAM은 변경하지 않는다. P2 미선택이며 자동 merge하지 않는다.
