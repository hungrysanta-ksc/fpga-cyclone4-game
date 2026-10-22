# NES272 — 일반 명령 해석 이동과 source 문맥 공유 비용

PR130에서270 common SPI를 기준으로 두 회로를 구현했다.
A는 일반 명령·manifest payload 해석을 host에서 NES clock으로 옮긴다.
B는 A의120비트 packet 문맥을 입력 완료 후 비는 source/query 레지스터와 공유한다.
두 후보 모두 전체 회로 예산을 만족하지 못하므로 채택하지 않는다.

이는271에서 정한 전체 교체의 **일반 payload 해석 부분**이다.
header admission과 typed-map descriptor 해석은 host에 남으며,
source/receipt/parser를 단일 FSM으로 합친 결과가 아니다.
phase RAM의28B 문맥·128B 조각 버퍼도 이번에는 구현하지 않았다.
전체 교체가 실패했다고 일반화하거나60fps를 달성했다고 판단하지 않는다.

## 실제 바뀐 경계

host는 queue RAM 읽기·일반 SNES packet 창·정확한 순차 read/ordered ACK,
tile proof·map staging/DMA token·head 반환·최종 표시 ACK를 소유한다.
일반 명령은 SNES read/ACK 이후, 내부 manifest/fence는 기존 내부 명령 경로에서
NES parser에 전달된다. queue credit는 parser 완료 응답 전에는 반환하지 않는다.
map DMA receipt와 final display ACK의 구분은 그대로 유지한다.

기존 host의 `OSETUP/OTILE/OSELECT/ODATA/ORLE` 의미검사와
`event264` 생성 제어 및 그 문맥을 제거했다. 새로운 NES-clock parser가
같은 검사를 실행하고 기존 core의 CRC·receipt·display 의미검사에 직접 요청한다.
source/receipt core의 알고리즘과 ARM wire packet 형식은 유지한다.

기존24비트 forward mailbox의 kind9는16비트 문맥, kind10은 원시 payload byte다.
문맥은 op/type·start·payload length·output length·queue length/tile proof·
token32·scroll length/raw count를8word로 보낸다.
기존8비트 reply mailbox는16..255 읽기 주소,0 완료,1 오류를 구분한다.
host가 요청 주소의 RAM byte를 돌려주는 동안 queue head를 유지한다.
한 번에 하나의 요청만 진행하며 별도 FIFO·packet RAM·mailbox를 추가하지 않는다.
기존 map receipt·display reply와의 중재도 합성 비용에 들어 있다.

바이트별 의미 이벤트 CDC가 사라져도, 원시 byte를 요청하고 응답하는 왕복과
packet당8word 문맥 전송은 남는다. 외부 SPI payload 재전송을 제거한264의 이득을
추가로 얻었다고 세지 않는다. 같은 SPI packet bytes를 실제 실행 결과에서 대조한다.

## source 레지스터 공유의 정확한 수명

B는 `q_held[63:0]`에 header8B, `old1/old2/new1/new2`에 token32,
`edge0/edge1[1:0]`에 queue length/tile proof10,
`q_maps`에 scroll length11, `q_raw_seen`에 raw count3을 둔다.
총120비트이며 source 단계와 출력 단계의 의미가 다르다.

쓰기 조건은 output phase·유효 display lease·pending query 없음·reset/STOP/fault 없음이다.
입력 query/row 비교가 끝난 뒤에만 쓴다. 다음 frame의 source는 원래 초기화와
query/row capture를 거치며,905→906→907의 source bytes/CRC를 기준과 대조한다.
공유를 위해 생기는 write 선택 회로는 비용에 포함한다.
source 레지스터 재사용은 RAM 절감이 아니며 기존 phase RAM 배치는 바꾸지 않는다.

## 측정 결과

|whole Lite MAP|270 기준|A: NES 해석|B: A+source 문맥 공유|
|---|---:|---:|---:|
|LE|22487|22767|22726|
|comb|17680|17834|17945|
|FF|8892|9052|8943|
|RAM bits|303712|303712|303712|

A는+154comb/+160FF, B는+265comb/+51FF이다. B-A는+111comb/-109FF다. B의 parser는227→107FF로120비트 줄었지만 source core는537→548FF로11개 늘었다. RAM은두후보모두303712bits로같다. A는2426comb, B는2537comb 초과하므로 FIT/STA에 진행하지 않는다.

|disjoint 조합 논리|270|A|B|
|---|---:|---:|---:|
|source/receipt core|2448|2452|2582|
|host flow 자체|2206|1547|1550|
|NES parser|0|784|773|
|합계|4654|4783|4905|

flow inclusive 수치에 parser를 중복해서 더하지 않았다. 기존2382 이하 목표와 비교하면 양 후보 모두 미달이다. 전체 보드와 disjoint 부분의 delta가 같다고 가정하지 않는다.

|warm907 source+output 직렬 진단|270|A|B|
|---|---:|---:|---:|
|normal|11.543680ms|11.543680ms|11.543680ms|
|restricted|20.283029ms|미실행|20.156985ms|

일반 ROM의 cold905/906은 두 후보 모두 기준보다 각각 84.135µs, 249.497µs 느렸다. warm907이 같다는 사실로 cold 비용 증가를 생략하지 않는다.
905는 E2 조회2회,906은 E2 조회4회와 E8 조회1회가 늘어 총74SPI bytes가 추가됐다. E1 payload 동일성은 전체 SPI 전송량 동일성을 뜻하지 않는다.

제한 ROM B의60Hz 예산 초과는3.490319ms이다. 새 heavy954나71프레임 전체의 최대값은 아니다. 출력 완료·polling을 다시 실행했으며 SPI bytes와 ARM 명령 차이는CSV에 기록했다. 구현이 바뀌어도 SPI/CPU 서비스에 가려진 내부 시간 변화가 있을 수 있으므로 이 작은 차이를 전체 경로 개선으로 해석하지 않는다.

제한 ROM warm907은 E2 조회3회,27SPI bytes,1659ARM 명령이 줄었다. 0.126044ms 차이는 이 polling 일정 변화와 함께 발생했으며 parser 자체의 독립 처리시간 절감이나 하드웨어 Fmax 개선을 측정한 것이 아니다.

|restricted B 실제 내부 전송/프레임|문맥word|요청/응답byte|로컬event|완료packet|
|---|---:|---:|---:|---:|
|905|192|724|988|24|
|906|256|756|986|32|
|907|96|246|482|12|

문맥word=완료packet×8, 요청수=응답byte수를실제RTL에서확인했다. byte왕복과 문맥전송은실행일정에포함한다. ARM의 PT_LOAD 코드·데이터,주소·크기·진입점·함수주소는270과동일하다. 전체ELF파일은각각별도해시를보존한다. 관측stack200B이며fullRUN추정은하지않는다.

기존38 semantic/STOP 검사를 새회로에서 다시 실행했고,metadata중간·body응답대기·local event·완료응답의4추가취소도PASS했다. fault후최종완료차단과1024B phaseRAM freeze를포함한다. test01의mailbox ready 선언순서와window01의계측TB변수선언순서 compileFAIL 및원본을보존한다. test02(A),test03(B)는기본실행,window02(B)은같은RTL에계수·소유권검사를추가한restricted실행이다.

## 판정과 남은 교체

host 의미 해석 제거만의 비용 절감은 전체 절감과 다르다.
별도 NES parser와 왕복 제어가 이를 상쇄하고, source 레지스터 공유는
FF 수를 줄이는 대신 조합 선택 회로를 늘렸다. core·flow·parser 상태는
Quartus에서 FSM으로 추출됐다. FSM 추출 실패나 seed 문제가 아니다.

다음 작업은 이 두 후보의 counter/encoding/seed/FIT 미세조정이 아니다.
host admission/map과 NES parser 사이에 남은 문맥·cursor·continuation 중복을
제거할 수 있는 **단일 source/receipt/parser 실행 제어**를 먼저 검토한다.
동시에 ARM이 FPGA의 제한된 primitive를 생산하는 표현과 비교해,
header·descriptor 처리까지 포함한 전체 경계를 더 작게 만들 수 있는지 판단한다.
ARM 추가 명령·wire bytes·refill/IRQ·ROM 경쟁·SNES polling과
FPGA RAM port/CDC/receipt 검사를 모두 장부에 넣는다.

기준270의 core+host parser4654comb가 다른1832개 유지 시2382 이하,
전체 교체 영역6486→4214 이하가 되어야 한다는 예산은 유지한다.
기존 source/receipt core만2448comb이므로 이 core를 그대로 두고 host/parser만
줄이는 방식은 output 제어를0으로 가정해도 해당 고정 경계 예산을66개 넘는다.
따라서 core 실행 제어 또는 전송 표현까지 실제로 바꾸어야 한다.
아직 미구현인 전체 경계를 이번 부분 실험의 수치로 통과시킬 수 없다.
phase RAM170B의 빈 공간에 전체256B packet을 복사하지 않으며,
어떤 새 buffer도 H2/CRC/receipt/validity를 덮지 않아야 한다.
넓은 교체에서 이 차이를 줄일 구조가 없으면 역할 분담·전송 표현을 바꾼다.

## 재현·한계

`probe_nes_refill272.py` 기본은 A, `--shared-context`는 B이며
`--rom-window 1`은 제한 ROM 조건이다. ARM은270 바이너리 그대로다.
`map_nes_joint272.py`에도 같은 옵션을 쓴다.
`guard_nes_joint272.py`는 B의 기존 STOP/의미 오류와 새 경계 취소를 검증한다.
Questa는 승인된 Starter FLOAT wrapper, 합성은 Quartus Lite만 사용했다.
보드 flow는 기존270부터 `tiles_closed`를 `tile_closed267` 출력으로 노출하고,
테스트벤치는 같은 신호를 계층 경로로 읽는다. 이 출력 선언과 assign 두 줄만
제외하면 같은 후보의 flow 내용이 일치한다. 원본 파일 해시는 각각 보존하며
core/parser/phase wrapper는 그대로 대조한다.

실제 ARM 명령은84MHz·CPI1 일정으로 모델링하며 IRQ 본문만 실행한다.
일반65816 명령은269에서 얻은 실제 bus trace이고, map/tile/final display는
모델이다. ROM 경쟁자도 synthetic이다. source+output 직렬 합은 진단값이며
전체 RUN/NVIC·active VBlank·전체 CDC/IO/STA·실기 frame deadline의 상한이 아니다.
새 heavy954·71프레임 전수 검사·FIT/STA는 실행하지 않았다.
production227·GBC164·saveSRAM은 변경하지 않는다.
