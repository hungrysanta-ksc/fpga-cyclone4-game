# NES282 — 압축 전송을 유지한 직접 실행·진행 응답·tile plan 공급

PR130 / `codex/nes-wholepath-boundary-256`. NES280의 실제 경로와 NES281의 공동
교체 예산을 기준으로 한다. production227/GBC164/saveSRAM은 변경하지 않았다.

NES282: 기존 압축 E1/E9 바이트를 유지하면서 host event/return·manifest 중복 상태를 제거하고, checked 진행 응답과 tile plan 공급을 실제 ARM 경로에 연결했다. 정상71·제한ROM3 및 ARM25/SPI51/STOP·ACK17 검사를 통과했다. warm 최대 16.166761ms(frame954), 280 대비 -0.426631ms다. whole Lite는 17,910comb(+95), 부족 2,502개로 회로가 악화됐다. 시간·회로 공동 후보/P2로 채택하지 않는다. 제한 ROM907은 18.708230ms로 0.117817ms 회귀했다.

## 실제로 제거하고 연결한 제어

host의 `consumer_word` 24bit event 인코딩, `event_return` continuation과 OWAIT
분기를 제거했다. 원본 command의 범위가 독립 validator에 직접 전달되고, validator가
받아들인 클록에서만 host cursor가 진행한다. tile/CGRAM/body의 receipt는 최대 16개
단위로 묶는다. raw tail은 실제 읽기 tap이 만든 CRC mask를 확인한 뒤 granule별로
진행한다. ACK 전에 coverage를 확정하거나 CRC를 ARM의 힌트로 대체하지 않는다.

host의 별도 `manifest_at`·`manifest_phase` 레지스터를 없앴다. 독립 validator가
검사한 `cursor`·`rec_i`가 manifest 위치·진행 상태의 근거가 된다. dense/RLE 입력,
RLE zero 확장, H2 digest→certificate→finish를 직접 연결했다. PCAP/ORLE은
validator ready와 같은 클록에서만 전진한다. 기존 queue의 ordered retirement를
유지하면서 별도 BRET return bubble을 제거하고, `qretire`가 처리되기 전에는
다음 head를 잡지 못하게 했다.

queue와 plan의 중복 MISO bit 레지스터/선택 제어를 공통 SPI로 옮겼다.
source payload MISO는 별도 데이터 경로이므로 유지한다. reset·SS·STOP 선택 게이트,
source NES A / host B 고정 phase RAM 포트, query 선행 읽기도 유지한다.

이것은 실제 제어 제거와 연결 변경이다. 다만 독립 validator의 RAM 접근 FSM,
SNES read/ACK tap FSM, plan 두 bank의 reader·CRC·CDC는 남는다. 모든 제어가 단일
FSM으로 합쳐졌거나 과거 source/RPC/mailbox 절감이 이번에 새로 생겼다고 주장하지 않는다.

## 전송 중 진행 응답과 ARM refill

기존 E1(output)·E9(plan)의 MISO를 이용한다. MOSI payload, 압축 형식과 전송 길이를
늘리지 않는다. 명령을 받은 시점의 상태를 고정해 아래 12B를 반환한다.

| RX 위치 | 의미 |
|---|---|
| 0 | 기존 dummy |
| 1 | marker FA |
| 2 | output flags |
| 3..4 | output accepted, BE16 |
| 5..6 | output retired, BE16 |
| 7 | output phase |
| 8 | plan flags |
| 9..10 | plan accepted, BE16 |
| 11 | 위치 1..10의 CRC8 |

응답은 **현재 전송의 acceptance 이전 상태**다. ARM은 accepted가 전송 전 sent와
같고, retired 증가가 현재 pending 이내이며, credit가 4 이하인지 확인한다.
flags·phase·CRC도 검사한다. 늦은 retirement는 credit를 보수적으로 줄일 수 있지만
아직 처리하지 않은 packet에 credit를 부여해서는 안 된다.

tile plan 공급은 output IO 경계마다 최대 두 packet까지 시도한다. 빈 sealed bank가
없으면 output 실행으로 돌아가며, plan bank가 빌 때까지 output을 막지 않는다.
E9 직후에는 응답이 현재 seal 이전 값이므로 cache를 버린다. E0/E2는 plan 상태를
갱신하지 않으므로 이들 뒤에도 cache를 버리고 필요한 E8을 다시 읽는다.
tile 대기 중 stale busy 상태만 반복 사용해 plan 공급이 멈추는 것을 피한다.

3B terminal plan의 E9는 총 11B라 전체 응답을 담지 못한다. 이 경우에는 기존
E8 fallback을 유지한다. full credit·tile wait·최종 plan retirement의 checked status,
EA retirement도 유지한다. 전송 응답의 오류가 발견될 때 MOSI packet은 이미 수신됐을
수 있다. 따라서 실패 후 packet을 재전송하거나 성공으로 전진해서는 안 된다.
이번 검사는 ARM의 sticky failure와 RTL STOP 경계를 각각 다루며, 전체 firmware의
오류→STOP 발행 루프까지 새로 실행한 증명은 아니다.

출력 ARM은 text **4,642B**, BSS **624B**, 관측 stack **264B**다. NES280 대비
각각 +436/+12/+16B다. source decoder와 별도 ELF이므로 전체 firmware의 link 크기나
동시 peak stack으로 더하지 않는다. stack 관측값도 모든 경로의 상한은 아니다.

## 전체 Quartus Lite 비용

같은 whole-board 경계의 새 RTL로 Lite MAP을 한 번 실행했다. compiler 입력을 hash로
고정하고, simulation과 board wrapper의 기존 배선 차이도 NES280과 대조한다.

| 항목 | NES280 | NES282 | 변화 |
|---|---:|---:|---:|
| 전체 LE | 22,754 | 22,847 | +93 |
| 전체 조합 논리 | 17,815 | 17,910 | +95 |
| 전체 FF | 9,127 | 9,092 | -35 |
| RAM bits | 307,808 | 307,808 | 0 |
| 장치 15,408 대비 조합 논리 부족 | 2,407 | 2,502 | +95 |

| 중첩을 뺀 own 영역 | NES280 comb | NES282 comb |
|---|---:|---:|
| host flow | 2,488 | 2,494 |
| validator | 1,056 | 1,087 |
| queue | 129 | 127 |
| plan endpoint+reader/CDC | 577 | 565 |
| 교체 대상 합계 | 4,250 | 4,273 |
| 그 밖의 전체 영역 | 13,565 | 13,637 |

교체 대상은 +23개, 외부 영역은 +72개다. 후자에는 공통 SPI +4와 연결 wrapper +50,
동일 RTL의 다른 영역에서 생긴 전체 합성 배치 차이도 포함된다. +95 전체를 단일
연산이나 레지스터의 비용으로 단정하지 않는다. 독립 validator와 직접 range/진행
연결의 비용이 남아, 레지스터 제거가 전체 조합 논리 절감으로 이어지지 않았다.

새 외부 영역을 유지하면 교체 대상 허용량은 **1,771comb**, 계획 여유 128을 남기는
목표는 **1,643comb**다. 현재 4,273에서 각각 **2,502/2,630개**를 더 줄여야 한다.
validator·source core·host flow·tap·plan reader FSM은 실제 추출됐다. FSM 추출 실패나
RAM의 FF 대체로 설명할 수 없다. RAM 절감도 없으며 FIT/STA는 실행하지 않았다.

기존 로그와 경로·행 번호를 정규화해 비교한 새 warning은 공유 후 사용하지 않는
`status_reply270` wire 두 곳과 manifest cursor의 10→9bit 대입이다. map manifest 소비 시
cursor는 166..422, 결과는 0..256이라 9bit에 들어간다. RAM 초기화의 더 큰 cursor 값은
ready가 내려간 구간이며 manifest 소비를 허용하지 않는다. 이 범위와 end 검사를
유지하며, 원본 warning 로그도 보관한다. 기존 program ROM shell의 미사용 포트 warning은
전체 프로그램 linking이 완료됐다는 근거가 아니다.

## 시간 비교와 증거 범위

| 일반 조건 | NES280 | NES282 | 변화 | 16.667ms까지 여유 |
|---|---:|---:|---:|---:|
|952|15.337180ms|14.643870ms|-0.693310ms|2.022797ms|
|954|16.593392ms|16.166761ms|-0.426631ms|0.499906ms|
|955|15.070046ms|14.493553ms|-0.576493ms|2.173113ms|
|962|15.633540ms|15.143636ms|-0.489903ms|1.523030ms|
|963|14.801186ms|14.451417ms|-0.349769ms|2.215249ms|
|968|13.566474ms|13.257295ms|-0.309178ms|3.409371ms|
|970|16.002626ms|15.684994ms|-0.317633ms|0.981673ms|

warm69의 한도 초과는 0개다. cold905/906은 별도 시작 비용으로 남긴다.

| 제한 ROM | NES280 | NES282 | 변화 |
|---|---:|---:|---:|
|905|89.483199ms|89.140839ms|-0.342360ms|
|906|113.828089ms|113.987359ms|+0.159271ms|
|907|18.590413ms|18.708230ms|+0.117817ms|

제한 조건의 세 프레임 절대 종료는 263.928560ms, 기존보다 -0.065272ms다. 구간 변화와 절대 종료를 구분한다.

제한 ROM907의 E2는 279→280회, E8은 4→3회, SPI는 3,496→3,485B, ARM/IRQ는 236,148→248,854명령이다. ROM slot 대기는 누적값 차분 기준 225,567→225,524cycle로 줄었다. 추가 ARM 12,706명령은 CPI1/84MHz에서 0.151262ms, SPI 11B 절감은 2.625MHz에서 0.033524ms다. 차이 0.117738ms는 실제 구간 증가 0.117817ms와 거의 일치한다. ROM 대기와 SPI/ARM 시간을 다시 합산하지 않으며, 같은 타임라인에 이미 포함된 비용이다.

954의 source 5.424799ms + output 10.741962ms다. E2 91→85회, E8 11→7회, 출력 SPI 2577→2443B, 출력 ARM/IRQ 190251→195434명령이다. source codec 91786명령은 유지한다.

954에서 source codec만 CPI2로 바꾼 고정 일정 민감도는 17.259451ms다. 순수 parser 22.431µs·map receipt 1.753µs와 polling/공급 일정의 변화를 구분한다. 전체 절감을 FPGA parser 단독 효과로 돌리지 않는다.

일반 조건에서 계획상 0.5ms 여유까지 추가로 0.000094ms가 필요하다. source만 CPI2로 둔 고정 일정은 0.592784ms, 제한 ROM warm은 2.041563ms가 16.666667ms 한도를 초과한다. 이것은 명시한 진단 조건의 예산이며 미측정 full RUN/VBlank 비용의 상한을 뜻하지 않는다.


source는 NES280에서 실행한 실제 ARM codec/control 명령 비용을 block·transaction별로
재생한다. 출력 serializer/refill과 IRQ body는 실제 ARM을 live RTL과 연결한다.
공유 SPI polling, tile ROM 중재와 CPU 비용을 같은 일정에서 계산한다.
SNES 일반/OAM 실행은 기존 NES279의 실제 65816 bus trace를 재사용한다.
새 65816 실행이나 전체 N5 planner/RUN/NVIC preemption의 실행은 아니다.
84MHz CPI1은 하드웨어 WCET가 아니다. source만 CPI2로 바꾼 수치는 고정 일정의
민감도이며 ROM 경쟁을 다시 실행한 결과도 전체 ARM CPI2 결과도 아니다.
active VBlank 대기·전체 프로그램 ROM linking·물리 60fps는 여전히 미검증이다.
NES280 source의 raw 0..2개 범위와 STOP 뒤 cold/reset 계약도 그대로다.

## 검사와 실패 기록

선택 증거: test04, window01, guards01, armguards01, spiguards01, board01, analysis03. 71프레임의 E1 1,231개와 E9 payload를 기존과 바이트 단위로 대조했다. source 47,900B, map receipt 2,069범위, CPU bus trace 544명령, 최대 4-credit를 확인했다. metadata 8,570B/receipt 754B/CRC 64B의 프레임별 검사를 유지했다. 새 진행 snapshot 1295개도 CRC를 독립 재검산했다.


새 응답 ARM parser는 25개 입력(정상/부분 retirement·wrap 4개, 잘못된 counter/flags/
phase/CRC 21개)과 sticky failure를 검사했다. 실제 SPI의 51개 검사는 명령 중 상태가
바뀌어도 command-start snapshot이 유지되는지와 최대 길이 E9를 포함한다.
새 RTL의 STOP/ACK/manifest 17개는 malformed/final ACK, sequence/주소/alignment,
manifest gap, read/receipt/scroll/retire 중 STOP, host/NES clock pause를 포함한다.
독립 원본 bytes·CRC·coverage/H2·token·4-credit·12B 표시 read coverage와 최종 ACK를
유지한다. 변경하지 않은 source codec의 추가 guard는 NES280 증거를 재사용하며
이번에 모두 다시 실행했다고 합산하지 않는다.

`test01`은 BRET 제거 후 이전 queue head를 너무 일찍 재획득해 실패했다.
IDLE의 `!qretire` admission 조건으로 수정했으며, 독립 header 검사를 약화하지 않았다.
`test02`는 중간 3프레임 PASS다. 그 뒤 ARM의 sticky failure와 E0/E2 이후 plan cache
무효화를 추가했으며, 최종 `test03`과 전체 시험은 수정된 동일 ARM/RTL을 사용한다.
실패와 중간 결과는 삭제하지 않는다. 라이선스 문제로 분류하지 않는다.

분석 `analysis01`은 normal71/restricted3의 expected fixture 전체를 같다고 가정해
실패했다. 파일 길이는 같지만, 기존 generator는 LAST까지만 sparse coverage를 갱신하므로
restricted fixture의 미실행 tail에는 이전 gap16 값이 남는다. 첫 차이는 미실행 frame914이며,
실행한 905..907의 3×754B는 동일하다. 정상/제한 각각의 기존 fixture 전체와도 일치한다.
`analysis02`는 board transport에 남은 빈 줄 하나를 실행 논리 차이처럼 처리해 실패했다.
원본 hash와 정확한 diff를 보관하고, 해당 파일만 빈 줄을 제외한 모든 줄의 일치를
요구했다. 다른 leaf는 byte-exact, wrapper는 기존280 차이를 그대로 검증한다.
두 분석 실패와 수정 전 script를 보존하며 최종 선택은 `analysis03`이다.

각 ARM ELF의 원본 hash는 따로 보존한다. GCC가 assembly 임시 object에 붙인
`STT_FILE` 이름만 `.strtab`에서 달라진다. 비할당 문자열의 해당 이름만 정규화한 뒤
ELF 나머지 모든 바이트를 대조하므로 실행 코드·주소·심볼·메모리 배치의 차이를
허용하지 않는다. raw ELF hash가 같다고 잘못 기록하지 않는다.

생성·실행 진입점은 `tools/probe_nes_refill282.py`, `tools/guard_nes_joint282.py`,
`tools/guard_nes_spi282.py`, `tools/guard_nes_progress282.py`, `tools/map_nes_joint282.py`다.
새 출력 폴더에서 실행하며, 실제 정상71/제한3 명령과 승인 FLOAT wrapper의 child job은
로컬 `probes/nes-joint282/full-job.ps1`에 보관한다. `analysis03`은 원본 로그·ARM ELF·
RTL·기존 source 비용 입력·whole compiler 입력을 hash로 대조한다. 재실행 가능한 compiler
database는 보관 대상에서 제외하고 실제 source/report/log는 유지한다. 라이선스·서버 로그는
이 증거 보관과 Git에 포함하지 않는다.

## 판단과 다음 경계

새 경로의 기능·시간 결과는 위 범위에서 검증했으나 전체 회로가 95comb 늘어 공동 목표는 실패했다. host 2,494comb를 무료로 전부 없애도 나머지 15,416comb가 장치 한도를 8개 초과하는 산술이다. 이 가정은 실행 가능한 회로가 아니며, 작은 host 정리만으로 목표를 달성할 수 없다는 예산 검사다.


다음 후보는 검사 자체를 빼기보다, host의 command/receipt 범위 계산과 validator의
주소·RAM progression을 함께 소유하는 실행 경계를 검토해야 한다. 한 descriptor를
두 실행기가 해석하는 비용과 queue/plan의 서로 다른 수명을 구분하고, 독립 수신
CRC/coverage·ACK·STOP 조건을 보존한 실제 제거 목록과 새 외부 비용을 먼저 고정한다.
현재 helper/FF 일부나 poll 간격만 바꾸는 방식, seed/FIT 반복은 다음 단계가 아니다.
양쪽 예산 통과 전에는 P2/배포/물리 60fps 성공으로 채택하지 않는다. 자동 merge하지 않는다.
