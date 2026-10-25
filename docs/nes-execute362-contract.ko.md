# NES362 — source·host 실행 경계와 후반 OBJ ROM 대기

338 RTL·355 ARM과 359 host 절감을 기준으로 검토했다. **source338을 유지한 BG5+OBJ2 선행 읽기는 시간 예산을 개선했지만 회로는 늘었다.** 공동 clock·CRC 경계는 앞부분 query 지연으로 연속 일정까지 악화시켰다. 시간 후보는 2,316comb, 공동 경계 후보는 2,357comb 부족하므로 둘 다 선택하지 않는다. 광범위한 source·host FSM 본체 교체는 아직 구현하지 않았다.

## 실제 삭제·유지한 경계

356/358의84MHz source 경계와 collector 취소 완료 수정을359 host에 연결했다. 기존 source transport의40bit descriptor 두 개/17bit prepared ACK mailbox, publish/sent와 양쪽 fault/up 동기화 제어를 제거했다. 같은 host clock의busy/pop과24bit descriptor 두 개를 쓰고 generation은frame namespace에서 재사용한다. 대신 collector query32bit/response65bit CDC, start/DONE/final ACK 및lease handoff 제어를 실제로 부담한다. STOP 때 collector release 적용 완료를 확인하고 늦은DONE을 양쪽에서 차단한다.

source와validator에 있던CRC16 함수 두 개를 제거하고 phase가 선택하는24bit 입력과 공통CRC 결과로 바꿨다. source/block checksum 및 독립 소비 검사 checksum은 별도로 유지한다. 실제 CRC 소비 시각마다 owner와 동시 사용 금지를 검사했다. 각 3프레임에서 source byte/CRC 경계 13244회, checker CRC 경계 747회의 owner 검사를 통과했다. source 횟수에는 checksum 값을 전송하는 trailer도 포함되므로 CRC accumulator 갱신 횟수로 해석하지 않는다. CRC 회로 공유가 독립 expected 데이터·coverage·receipt 공개 순서를 제거하지는 않는다.

359에서 제거한host tap continuation FSM/position/value는 복원하지 않았다. 반면 source의FETCH/FSTORE/SREAD/SBYTE, host의header/descriptor/PREAD/PCAP/PUT/RLE 진행은 남는다. 이것을 제거하지 않은 채 전체 공동 실행기로 완성됐다고 할 수 없다. 이번 구현은 실제 CDC·CRC 교체를 통합했을 때의 부정적 면적 판정이다.

|whole Quartus Lite MAP|LE|comb|FF|RAM bits|15408comb 대비 부족|
|---|---:|---:|---:|---:|---:|
|338 선택|22144|17274|9018|307808|1866|
|359 host|22083|17213|8999|307808|1805|
|358 경계+359, CRC별도|22122|17283|9056|307808|1875|
|위 경계+CRC공유|22146|17307|9056|307808|1899|
|361 BG5 hint|22499|17576|9093|308832|2168|
|BG5+OBJ2 경로만|22733|17724|9179|308832|2316|
|공동 경계+BG5+OBJ2 통합|22744|17765|9236|308832|2357|

전송 CDC 삭제를 새로운query/lease 경계까지 포함하면359보다70comb 늘어난다. CRC 공유는 대조 합성보다24comb 더 크며FF는 같다. 내부CRC 함수가 없어져도 입력 선택과 fanout의 전체 합성 비용은 커질 수 있다. 7tag와 공동 경계를 합친 값은실제 전체 합성17765이며 따로 측정한 절감/증가를 산술 합산한 값이 아니다. 각MAP 입력·원시 report를 고정했고 FIT/STA는 실행하지 않았다.

## OBJ 예측과 실제 입력·SPI·ROM 연결

직전 actual ARM commit RAM의resident 이력과 현재 실제 수신 첫N5 block만 producer에 제공한다. ARM은active bank에 있고target bank에는 없는 retained OBJ 중최대2개를 고른다. warm907에서는5082/5080이며, producer 실행 후 따로 읽은 실제OBJ plan과 일치했다. 미래plan이나 최종tag oracle은 producer 입력이 아니다. tag는예측이고 DMA/표시 권한을 만들지 않으며, hit하지 못하면 기존ROM 경로가 남는다.

최종 bounded OBJ scan은371명령이다. BG5 생성·OBJ2 scan·28B 패킷CRC까지4497명령으로361보다866명령 늘었다. source decode는18289명령 그대로다. helper object는text2320/BSS96이고, 별도 OBJ probe에서 관측한 stack은48B다. BG 생성과 전체 호출 chain의 firmware stack 상한은 이 probe로 확정하지 않는다. text/BSS는 기존5tag object1916/74 대비+404/+22B다. 이 값은 helper의 예산이며 전체 firmware의 메모리 사용을 새로 측정했다는 뜻은 아니다.

EA extended packet은24→28B, tag7개, 유효cache112B이며 물리RAM은같은128×8M9K다. tag/valid 및EA 제어 증가분은전체MAP에 포함했다. 실제shared SPI의CRC·namespace 검사와7B 기존EA retire를 유지한다. cache 포트는input hint와정상tile이중재하며 STOP 때physical READ16 drain/validity 폐기/늦은DONE 차단을 유지한다. ordinary2slot credit을hint가 차지하지 않는다.

새28B 패킷은실제M4가 만든다. TB는수신한block 시점에서M4 helper를 실행하고4497명령, 실제233 IRQ body66명령과예외24cycle 할당, SPI pin 시간을 청구한다. output ARM355/IRQ/refill/2slot은실행한다. source 입력 및추가hint의foreground 통합은여전히 harness 연결이며, 전체firmware ISR 선점/WCET를 증명하지 않는다. 현재통합 실행은905/906 준비 프레임과첫warm907에대해검증했다. 다른warm tag집합·부분hint·deadline fallback은별도gate다.

## 전체 일정과 시작 위상

|warm907 일정(CPI1 모델)|359 기준|공동 경계+7tag|source338 유지+7tag|338 유지 후보의 기준 대비|60Hz 예산 여유|
|---|---:|---:|---:|---:|---:|
|연속|20.689706ms|20.779023ms|12.156081ms|-8.533625ms|4.510586ms|
|동일 시작·ROM 위상|25.051563ms|12.328443ms|12.157717ms|-12.893846ms|4.508950ms|

source338·359 host를 그대로 유지한 7tag 대조는 연속12.156081ms / 동일 위상12.157717ms이다. 첫 block 해석 완료는 source338 대조 1.458201/1.458201ms, host clock 이전 후보 1.628915/1.628915ms이다. 이 값은 hint 시작에서 실제 추가 ARM·IRQ 비용을 뺀 시각이다. 같은 고정 시작 위상에서도 앞부분 지연이 유지되는지 비교하여, 전체 source 완료 시간에 가려진 query CDC 비용을 분리한다. source338 유지 후보의 whole17724comb/2316개 부족도 별도로 청구한다.

고정 일정은 기준과 각 프레임의 시작 시각·ROM cycle이 같다. 연속 일정은 직전 프레임 종료와 실제 비용이 다음 시작 위상을 바꾼다. warm 시작 ROM cycle은 기준 5677152, 공동 경계 후보 5677165, source338 유지 후보 5677489다. 고정 일정은 모두 7368026이다. 서로 다른 표 행의 차이를 최적화 이득으로 쓰지 않는다.

공동 경계 후보의 연속 hint SPI 시작/종료/fill은 1.683522/1.776856/16.948592ms다. OBJ 첫 plan/첫 tile은 연속 17.195998/17.196452ms, 고정 8.781008/8.781462ms다. OBJ 응답 자체는 빨라졌지만 hint fill을 기다리느라 BG 공급도 늦었다. source338 유지 후보에서는 fill이 1.682957ms에 끝났고 OBJ 첫 plan/첫 tile은 8.607828/8.608101ms다. 이전 361의 plan→tile 차이는 연속 8.263401ms, 고정 12.630530ms였다. 이 차이는 ROM/cache/실행 대기의 합이며 순수 pin 시간으로 부르지 않는다.

공동 경계 후보의 warm 비용은 source SPI 707B + hint 28B, output SPI 1084B, E2 progress poll 22회다. source338 유지 후보는 source 668B + hint 28B, output 1028B, E2 poll 18회다. 공동 경계에서는 빈 source poll이 8→11회로 늘어 39B가 추가됐다. source338 유지 후보는 기준보다 output 응답이 56B 줄고 hint 28B가 추가되어 전체 SPI는 28B 줄었다. source 압축 payload, opcode별 E1 payload, DMA 순서와 E9 bytes를 대조했다. 모든 SPI byte가 같다는 뜻은 아니다. cold 두 프레임의 비용·IRQ 수·ARM 명령 수는 verification JSON에 포함한다.

시간 수치는 **CPI1 할당을 사용한 모델의 warm907 결과**다. 실물 60fps 승인이 아니다. source338 유지 후보도 첫 ROM 허용 구간 종료 상한까지 약 29.361µs만 남는다. 실제 IRQ/foreground 지연과 CPI 변화에 대한 마감 여유를 검증해야 한다.

## RAM 소유권 정정과 다음 삭제 예산

357의두66B row slot 제안은640..705/800..865다. 현재338의실제주소식은ordinary receipt512..677, H2 680..711, display offset712..715, map receipt768..1023이다. 따라서첫slot은ordinary receipt/H2, 두번째는map receipt와겹친다. 이전H2 832..863 설명을357문서에정정했다. 기존source scratch delta512..577/header768..787/mask896..904와의비중복만으로전체소유권을증명할수없다.

후속구조는NES 고정portA row producer와host 고정portB codec/output 실행기로정하고, row descriptor반환·codec/전송 drain·입력ACK가모두끝난뒤receipt초기화/H2쓰기권한을넘겨야한다. 현재시험의두RAMport는host clock이며, 이NES row-fed구조를구현한것이아니다. collector 취소완료와STOP후DONE차단은이교체에서도유지해야한다. clock mux나미구현RAM회수는절감에넣지않는다.

중복없는통합분할은source+host(모든queryCDC·공통CRC포함)4033, 독립검사/aperture1216, queue/SPI784, plan462, 나머지11270comb다. 15253 목표와queue/SPI650 상한을유지하면source-host상한은1655이다. source-host에서2378, queue/SPI에서134, 총2512comb를실제로더삭제해야한다. 합격상한이며달성예측이아니다.

source338 유지+7tag 대조의 중복 없는 분할은 source-host3832/checker1250/queueSPI784/plan467/rest11391comb다. 같은 목표에서는source-host1495, queueSPI650이 상한이며 총2471comb 추가 삭제가 필요하다. 분할 간 합성 최적화와 CRC 위치가 달라지므로 상한 차이를 독립적인 회로 절감으로 계산하지 않는다.

현재선택338/355의공식부족은4.023039ms/1866comb그대로다. 새후보는시간과회로를동시에개선하지못했으므로선택하지않는다. 다음은CRC/clock공유의반복튜닝이아닌source codec와host byte/RAM continuation의실제삭제다. 이범위가상한에들어갈근거가없다면전송/역할분담을다시비교해야한다.

## 검증 범위

공동 경계 단독·공동 경계+7tag·source338 유지+7tag의 세 후보를 각각 2일정×3프레임으로 실행했다. sourcebytes·output wire·독립read→unit→privateRAM→ACK공개·최대2credit·최종12read를대조했다. STOP private receipt/rawCRC, wrong token, collector WAIT/returned reply/handoff STOP6건과aperture/독립raw0/final/reset8건, 실제EA·cache·arbiter·READ16 guard68건을통과했다. epoch/serial/mutable/STOP ARM guard도통과했다. 원시 로그와 중간 arm01/02를 보존하며 최종 ARM은arm03이다. EA guard01은68건을 통과했지만 패킷 길이 치환이 testbench의 주소 폭까지 넓혀 경고를 만들었다. 주소 폭을 유지하는 국소 치환과 미사용 output의 명시적 연결로 고친guard02를 최종 결과로 사용한다. DUT RTL 변경은 없다.

ordinary65816 trace와tile/display busmodel을사용했고독립검사·STOP·최종ACK·VBlank계약을제거하지않았다. 전체65816/VBlank 실행, 전체ARM firmware/모든IRQ/71프레임, FIT/STA/실물은미완료다. production227/GBC164/saveSRAM은그대로이며PR131을자동merge하지않는다.

근거: [검증JSON](../analysis/execute362-verification.json), probes/nes-execute362의원시실행·MAP결과.
