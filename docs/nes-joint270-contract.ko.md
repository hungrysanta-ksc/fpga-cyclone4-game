# NES270 — 공통 SPI 제어와 짧은 상태 조회의 실제 비용

PR130 R1의 후속 검증이다. production227·GBC164·saveSRAM을 유지한다.
source/output/plan의 SPI 수신·상태 snapshot·CRC8 제어는 실제로 대체했다.
NES clock의 source·receipt core와 출력 parser 전체를 교체한 결과는 아니다.

## 실제 실행 결과

|항목|269|270|
|---|---:|---:|
|warm 직렬 진단 최대|18.391188ms|18.065374ms|
|16.666667ms 예산 부족|1.724522ms|1.398707ms|
|warm69 초과|6|5|
|E0 전체조회|3547|249|
|E2 짧은조회|0|7016|
|전체 공유SPI B|279471|263743|

최대 frame954는 source6.254970+출력11.810404ms다. 추가 full RUN/VBlank 비용을 포함한 전체 상한은 아니다. ARM3164text/604bss, 관측 stack200B이며269 대비 text+60/stack+8/static0이다.

954의 실제 polling은 E04+E2110=114회로 기존56회와 다르다. status wire는1344→1086B이며 전체 일정 변화는-0.325814ms다. 고정 polling 투영2.317ms를 실제 절감으로 적용하지 않는다.

|제한 ROM 창|269 ms|270 ms|차이 ms|
|---|---:|---:|---:|
|905 (cold)|103.609711|88.705799|-14.903912|
|906 (cold)|116.382149|113.888633|-2.493516|
|907 (warm)|19.291450|20.283029|+0.991579|


일반 ROM 창의 warm69프레임은 모두 이전보다 빨라졌으며 절감 범위는0.053954..0.495449ms다.
954의 상태 조회 합계 증가는 transfer setup을0.464ms 더 사용했다. 이 비용은 실행 일정에
이미 포함되어 있다. 상태 wire 감소만으로 절감량을 계산하거나 setup을 다시 더하지 않는다.

제한 ROM warm907은 **0.991579ms 악화**됐다. 조회118→290회로 상태 wire는
0.493714ms 줄었지만 setup은1.376ms, foreground CPI1은0.110119ms 늘었다.
이 항목들을 포함한 실제 합계가20.283029ms이며 60fps 예산보다3.616363ms 길다.
각 진단 항목은 이미 실행 일정에 포함되므로 총 시간에 다시 더하지 않는다.
공통 SPI 구조는 실험 기준으로 남기되 **E2 short polling의 일괄 채택은 보류**한다.
다음 시간 후보는 credit 대기와 ROM 준비 대기를 구분한 bounded polling 또는 E1 credit snapshot이며,
동일한 normal/restricted ROM 실행에서 양쪽 비용을 확인해야 한다.

analysis01의 source 시간이 완전히 동일하다는 가정은913에서 실패했다. 실제7프레임의
총 source 시간은 ACK·backpressure 위상에 따라±1 NES clock 차이가 났다. 동일 RTL·바이트의
증명과 시간 동일성은 별개이므로 analysis03은 이 실제 차이를 포함한다.
중간 analysis02와 실패한 analysis01의 코드·실패 기록도 보존한다.

## 교체한 제어와 유지한 소유권

`nes_spi270` 하나가 host clock에서 SPI SS/SCK/MOSI를 동기화하고 bit/byte 수,
명령, 상태 snapshot과 CRC8을 관리한다. 기존 source transport, output queue,
plan endpoint는 이 수신 결과를 받아 각자의 admission·RAM·완료 조건만 처리한다.
source와 queue의 9비트 byte 수는 공통 10비트 수에서511로 포화시켜 기존 과장 길이 거부를 유지한다.

동시에 활성화될 수 없는 세 상태 snapshot을 하나로 합쳤다. CRC8 연산 입력은 request 수신과
status 계산 사이에서 선택하며 request를 우선한다. CRC 결과는 별도8비트 레지스터에서 내보낸다.
처음 구현한 가변 snapshot 위치의 CRC 쓰기는 큰 선택 회로를 만들어 제거했다.
상태는 명령 수신 시점에 고정하므로 송신 중 credit·phase가 바뀌어도 snapshot과 CRC가 일치한다.
이는 실제2.625MHz SPI 검증이며 더 빠른 모든 SPI 속도나 새 STA의 승인이 아니다.

다음 소유권과 비용은 계속 남아 있다.

- source의 두 immutable block, query 선행 읽기, D2 POP, 입력 COMMIT와 src/host CDC.
- output4credit, packet CRC16, queue head의 parser 완료까지 보존, token과 실제 SNES 소비 증명.
- plan RAM 복사 완료 시점의 head 반환과 별도 credit, tile 완료 후 최종 retire.
- NES clock의 source/receipt phase RAM, retained CRC64B, H2·display 문맥과 공유 CRC16.
- 269의 sticky bank 무효화, `$6001/$6006` 계약과 STOP 중 local ROM 유지.

source/plan/output의 선택 신호와 기존 MISO 중재도 유지한다. loader·boot SPI와 다른 clock domain을
공짜로 합쳤다고 하지 않는다. common reset 뒤에는 SPI SS가 해제된 버스 정지 상태에서 재개해야 한다.
현재 변경은 이 namespace 재시작 조건을 없애지 않는다.

## ARM의 짧은 조회와 전체 문맥

E2의9바이트 응답은 dummy/F9/flags/acceptedBE16/retiredBE16/phase/CRC8이다.
평소 credit와 phase polling에는 이 형식을 사용한다. E0의24바이트 F8 응답은 계속 제공하며,
tile 명령과 첫 map token을 사용할 때 전체 token·bank·generation·길이·범위 문맥을 다시 읽는다.
전체 조회 뒤 phase도 재검사한다. 일반 packet E1과 source D0..D3, plan E8/E9/EA wire 형식은 유지한다.

ARM은 각 응답의 marker·CRC·accepted/retired 차이·4credit와 fault를 검사한다.
정적 status buffer24B는 유지하므로9바이트 전송을15B RAM 절감으로 계산하지 않는다.
짧은 조회로 phase 대기 허용 시간이 줄지 않도록 bounded retry를256→1024회로 늘렸다.
이 횟수는 하드웨어 deadline/WCET가 아니며 full RUN의 시간 제한 정책은 별도다.

실제 ARM ELF는 새 serializer와 기존 refill267·IRQ 본체를 실행한다.
새 polling은 E8 방문 횟수, tile ROM의 준비 위상과 IRQ 서비스 시점을 바꾸므로,
269의 고정 polling 투영2.317ms를 실행 결과에서 일괄 차감하지 않는다.
원시 worker의 `status_reads` 필드는 E0 횟수다. 최종 비용표는 SPI event에서 E0/E2를 각각 세고 합산한다.

## 회로 결과의 해석

board01은 가변 CRC 쓰기를 포함한 중간 구현이다. 전체17692→17769comb로 악화됐다.
CRC를 별도 byte로 출력한 board02는17680comb,8892FF,303712RAM bits다.
같은 전체 보드269 대비 comb−12/FF−154/RAM0이며, FIT/STA는 실행하지 않았다.

|서로 겹치지 않는 영역|269 comb|270 comb|
|---|---:|---:|
|source/query·receipt core|2445|2448|
|source transport|437|327|
|output parser 자체|2204|2206|
|output queue|571|282|
|plan endpoint|446|301|
|plan transport|409|410|
|새 공통 SPI 엔진|0|512|
|합계|6512|6486|

세 endpoint와 새 공통 엔진만 합친 비용은1454→1422comb다. 다른 영역의 재매핑까지 포함한
전체 순절감은12개이며, endpoint 절감32개를 전체 절감으로 기록하지 않는다.
source/receipt core RTL이 같아도 합성 문맥에 따라2445→2448처럼 비용이 변할 수 있다.
FF 절감154개나 MAP LE 감소를 packed FIT 여유로 바꾸어 말하지 않는다.

현재 전체 조합 논리는 한도15408보다2272개 많다. 현재6486개 교체 경계를 유지한다면
새 비용4214개 이하와 추가 배치·mapper 여유가 필요하다. 공통 SPI 엔진이 있으므로
앞서 제거한 snapshot과 CRC8 제어를 다음 절감량에 다시 넣을 수 없다.

## 다음 큰 교체의 검증 경계

현재 source/receipt core2448과 output parser 자체2206을 합치면4654comb다.
나머지1832개가 그대로일 경우 이 두 영역의 새 합계가2382 이하가 되어야 부족2272를 회수한다.
약48.8%의 순감소가 필요한 예산이며 구현된 절감이나 가능성의 보장은 아니다.
source core2448을 그대로 둘 경우에는 나머지4038을1766 이하로 줄여야 하며,
새 중재·문맥 제어도 이 예산에 포함해야 한다.

다음 후보는 immutable output queue의 byte 해석·CRC/receipt 갱신을 NES-clock core의 출력 phase로
옮겨 source phase와 해석·주소·문맥 제어를 공유하는 방식이다. 기존 queue RAM의 clock/port,
실제 SNES 소비와 host ACK, plan copy credit, 기존 mailboxes의 대체 범위를 먼저 고정해야 한다.
host 약84MHz의 parser를 NES 약22MHz로 옮기는 추가 service 시간은 실제 DMA·SPI 일정에서 다시 측정한다.
단순 endpoint 합치기나 FF 감소를 근거로 새 FIT를 반복하지 않는다.

현재 RTL에서 다음 경계가 확인된다. 아래는 다음 구현의 검증 조건이며 이번 절감량에는 포함하지 않는다.

|경계|현재 구현|다음 후보에서 반드시 포함할 비용·조건|
|---|---|---|
|output queue 읽기|1024×8 RAM의 host-clock 읽기 주소를 NORMAL의 SNES 주소와 parser 주소가 공유|NES parser로 읽기 port를 옮기면 일반 SNES packet 읽기도 연결해야 한다. 추가 port·복제 RAM·왕복 CDC 중 선택한 비용을 전부 포함|
|head 반환|host `qretire`가 retired·4credit를 갱신|NES 완료를 host로 안전하게 반환하고 head slot 재사용 전 완료를 보장. STOP·counter wrap·stale completion 검사|
|해석 결과|host→NES 24비트 consumed mailbox, NES→host 8비트 receipt mailbox|같은 NES phase 안의 해석·CRC/receipt는 직접 연결 가능성을 검증하되 DMA 완료·표시 요청·응답까지 일괄 삭제하지 않음|
|일반 명령 완료|실제 SNES packet 읽기와 ordered ACK 후 parser가 payload를 해석|SNES 소비 증명 이전에 receipt나 credit를 확정하지 않고, 이후 해석 지연도 일정에 포함|
|plan 수명|별도 dual-clock payload RAM과 copy/retire 제어|tile 완료까지 유지하는 plan 문맥과 조기 copy credit를 output head 반환과 혼동하지 않음|

시간 후보도 실제 기다림과 중복 조회를 구분한다. E1 송신 중 MISO로 credit snapshot을 함께 돌려주는
방법은 기존 wire 구간을 활용할 수 있지만, admission 전 snapshot과 송신 후 accepted 수의 관계,
CRC 실패·STOP 시 복구와 추가 polling 변화를 새로 검증해야 한다. 이번에는 구현하거나 절감으로 세지 않았다.

## 재현과 남은 한계

`probe_nes_refill270.py`는 실제 ARM serializer/refill과269의65816 일반 명령 trace를
공통 SPI·source/query·receipt·tile cache/arbiter/physical ROM RTL에 연결한다.
기존522명령·83240source B·2069map 범위·metadata/receipt와4credit를 검증한다.
`guard_nes_arm270.py`는 기존18개 오류/preflight와16비트 counter wrap에6개 short-status 오류를 추가한다.
`guard_nes_joint270.py`는 source·receipt·H2·최종 표시의38개 오류/STOP 검사를 유지한다.
`guard_nes_spi270.py`는 실제 세 endpoint에서 교차 조회, snapshot 불변성, CRC, 부분 SS, wrap을 확인한다.

Questa는 승인된 temporary Starter FLOAT wrapper를 사용하고 보드 합성은 Quartus Lite만 사용한다.
첫 생성기의 source 목록 형식, 비교식/식별자 치환과 선언 순서 오류는 실패한 원본과 로그를 보존한다.
성공한 중간 test04/board01도 보존하며 최종 결과에 다른 RTL의 MAP을 섞지 않는다.

ARM CPI1과 service-boundary IRQ는 전체 RUN/NVIC·진입/복귀·실제 MCU cycle 측정이 아니다.
SNES 일반 명령은 실제 forced-blank trace이며 map/tile/final display의 전체65816 실행은 아직 모델이다.
269의 STOP CPU 검사와 실제 RTL 검사는 별도이며 live CPU/FPGA 동시 STOP 증명으로 확대하지 않는다.
ROM 경쟁에는 실제 reader/arbiter를 사용하지만 경쟁 core 요청은 fixture다. 제한 창3프레임은 최악 상한이 아니다.
active VBlank·모든 WRAM writer·전체 program link·full firmware SRAM·전체 보드 기능/CDC/IO/STA는 남아 있다.
ROM/CHR/packet/ELF와 원시 로그는 비공개 증거에 보존하며 Git에 넣지 않는다.
