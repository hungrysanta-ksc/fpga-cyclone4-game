# NES268 — HDMA 채우기·bank 재사용과 출력/tile 제어의 공동 비용

PR130의267 결과를 이어받는다. 시간 후보는 실제65816에서 실행하고, 그 버스 추적을 같은 ARM serializer/refill,
SPI queue, source/core, tile/cache/ROM 우선권 회로와 다시 실행한다. 제어 통합은 기존 whole-board 비용과 실제
staging 회로의 교착 반례를 먼저 확인한다. 작은 제어 블록의 합을 실제 보드 절감량으로 보고하지 않는다.
production227, GBC164, saveSRAM은 변경하지 않는다.

## 비교 범위

수치는 [검증 JSON](../analysis/joint268-verification.json), [프레임 비용표](../analysis/joint268-costs.csv),
[다음 계획](nes-joint268-plan.json)을 따른다. 실제 ARM 명령의 CPI1 민감도, forced-blank65816 실행,
실제 RTL 버스 replay를 함께 사용한다. 실기 전체 프레임 시간이나 WCET를 측정한 것은 아니다.

## 최종 수치

|항목|기존267|DMA 후보|재사용 후보|
|---|---:|---:|---:|
|HDMA1100B 명령 warm 최대|2.889566ms|0.598679ms|0.150392ms|
|71프레임 source+출력 직렬 진단 warm 최대|20.909704ms|전체71 미실행|18.294508ms|
|warm69 중16.667ms 초과|25|전체71 미실행|6|
|E0 poll 합계|5380|전체71 미실행|3465|
|전체 공유SPI 바이트|323463|전체71 미실행|277503|
|kernel bytes|374|557|565|
|zero DMA 쓰기 횟수|해당없음(MVN)|71|2|

|frame|기존 출력 ms|DMA 출력 ms|재사용 출력 ms|기존 ROM 제한 ms|재사용 ROM 제한 ms|
|---|---:|---:|---:|---:|---:|
|905|44.561556|43.594477|43.594477|85.295022|84.327943|
|906|47.790608|46.823074|46.823074|112.455741|112.475287|
|907|10.372694|8.146902|7.663226|16.949160|15.207499|

최대 진단은 frame954의 source 6.254970ms + 출력 12.039537ms다. 목표까지 **1.627841ms**, 현재 진단의 **8.90%**를 더 줄여야 한다. 같은 frame의 순수 shared SPI는 14.966857ms이고 나머지 경과 시간은3.327651ms다. 새 일정에서 wire만16.667ms를 넘는 warm프레임은0개다.

|목표 게이트|현재 부족량|해석|
|---|---:|---|
|진단 프레임 시간|1.627841ms|full RUN/VBlank/mapper 추가 비용 제외|
|FPGA comb|2271개(현재12.85%)|FIT/STA 여유 이전의 최소 필요량|
|queue·plan3블록을 비용0으로 대체하는 장부|밖에서844개+새 제어비용R|합성 절감량 아님|
|전체 ARM SRAM·프로그램/M9K·active VBlank|미확정|0 비용이나 확보된 여유로 두지 않음|


## HDMA의 동일한 결과를 더 적게 쓰기

실제71프레임에 반복되는 `op5 / section5 / offset21 / pattern0000 / count1100`만 특수 처리한다.
그 외 명령은 기존 MVN 경로를 유지한다. DMA 후보는 ROM의0 한 바이트를 fixed-source로 읽어 `$2180`에1100회 쓴다.
WRAM을 DMA source로 삼지 않는다. 실제 Mesen callback에서 ROM 읽기1100회, 값0, `$2180` 쓰기1100회와
최종 WRAM 결과를 검사한다. CGRAM/OAM DMA는 종전처럼 수행한다.

재사용 후보는 물리 WRAM bank별2개의 유효 flag를 둔다. 초기화 시 모두0이고, zero DMA가 끝난 뒤에만 해당 flag를1로 한다.
같은 bank의 정확한 zero-tail 명령이 다시 오면 쓰기를 생략한다. 일반 HDMA 쓰기의 반열린 범위가 `[21,1121)`과 겹치면
첫 쓰기 전에 flag를0으로 한다. scroll prefix `[0,21)`와 raw tail `[1121,...)`만 바뀌는 것은 이1100B의 유효성을 깨지 않는다.
이는 generation이 같은지를 이용하는 재사용이 아니라, 해당 물리 영역의 값이 계속0이라는 불변식을 이용하는 재사용이다.

일반522명령의 논리 결과128041바이트와 실제39648PPU DMA 바이트를 기존 입력 패킷으로 검사한다. DMA 후보는71번,
재사용 후보는 cold 두 bank에 각1번만 zero DMA를 수행한다. 생략되는 것은 SNES의 물리 쓰기다.
원래 패킷, FPGA payload 처리, CRC·receipt·H2 요구 범위, ACK identity와 최종 display ACK는 생략하지 않는다.
따라서 비활성 영역을 무조건 유효하다고 취급하거나 HDMA 종료 바이트를 임의로 제거하지 않는다.
OAM의 숨김 sprite 반복 명령도 그대로 남긴다.

별도33명령은 첫/마지막 tail byte, 양쪽 경계에 걸친 쓰기, prefix/raw disjoint 쓰기, nonzero 반복,
다른 opcode의 zero 반복, 다른 범위, 다른 bank 덮어쓰기를 포함한다.10번 재채움과 전체 이전 쓰기 영역의
불변성을 검사한다. 다른 bank/영역이 손상되지 않았는지도 매 ACK에서 확인한다.

ROM kernel은 기존374B에서 DMA557B, 재사용565B가 된다. ROM 상수1B, WRAM 유효 flag2B와 bank-index scratch2B(총4B)가 추가된다.
두 후보는 공통 범위 검사 코드와 flag 관리를 유지하고 재사용 branch만 다르다.32KiB probe ROM 안에서 실행했으며
이 kernel을 전체 제품65816 프로그램에 link한 결과는 아니다. 전체 프로그램/loader RAM·M9K 예산은 별도로 확인해야 한다.
4KiB를 맞추려고 시간을 희생하지 않는다.

현재 flag 소유자는 이 kernel이다. board STOP, 다른 WRAM writer, 전체 NMI/표시 경로와 무효화를 연결하지 않았으므로
제품 펌웨어에서 즉시 쓰기를 생략해도 된다는 승인이 아니다. cold 초기화와 이 kernel의 겹침 쓰기만 새로 검증했다.
267/266의 기존 STOP·token·receipt 검사를 이 새 경계까지 확장한 것으로 표현하지 않는다.

## polling과 ROM 경쟁을 같은 일정에서 계산

재사용의71프레임은 실제 ARM의 E0/E1/E8/E9/EA와 live credit 응답을 다시 실행한다. 이전 polling 횟수를 고정하거나
CPU 절감 시간과 SPI 절감 시간을 독립적으로 더하지 않는다. ARM ELF의 로드되는 segment가267과 같은지도 비교한다.
명령 수가 달라지는 것은 새로운 polling 응답·대기 일정 때문이다. IRQ 본체도 기존 service boundary에서 함께 실행한다.

DMA 후보는905–907의 같은 통합 일정으로 비교한다. 실제65816 단독 명령은 두 후보 모두71프레임분을 실행하지만,
DMA 후보의 ARM/RTL 전체71프레임을 새로 측정했다고 하지 않는다.

ROM 비교에는267과 같은 실제 cache/arbiter/physical reader,70ns PSRAM 응답, periodic core request를 사용한다.
기본71프레임은 항상 허용되는 ROM 슬롯이다. 별도905–907은357368클록 주기의330088..354639 구간 중 매12번째
클록만 허용하는 합성 stress다. 허용 슬롯에서 core가 fill보다 우선하는 경우도 관측한다.
이 세 프레임 결과는 live NES workload 또는 모든 프레임의 최악 시간 상한이 아니다.
CPU가 빨라져 ROM 창의 위상이 바뀔 수 있으므로, 기존 ROM 대기 시간에서 CPU 절감량만 빼지 않는다.
제한 창의 warm907은 출력15.207499ms, 입력 포함19.291450ms로 목표보다2.624784ms 길다.
이는 한 warm 예제다. cold906은112.455741→112.475287ms로 약19.545µs 늘어, 모든 경우가 같은 폭으로 빨라지지는 않았다.

## 출력과 tile 계획 제어를 합칠 때의 교체 경계

현재 E0/E1 출력 queue와 E8/E9/EA 계획 경계는 SPI shifter, CRC, admission, accepted/retired 문맥,
frame identity 및 종료 확인을 각각 보유한다. 공유 후보는 다음 수명을 분리해야 한다.

1. 공통 E1의 CRC·identity 검사가 끝난 뒤에만 immutable plan packet을 내부 소비할 수 있다.
2. plan packet을 전용 plan RAM으로 완전히 옮기고 소유권을 넘기면 출력 queue credit을 반환한다.
3. 디코딩된 plan은 실제 tile_done까지 유지한다. copy/queue retire는 tile 완료나 표시 완료가 아니다.
4. 최종 display ACK, 모든 tile/plan 소비, ROM reader drain, capture lease/epoch 조건을 함께 확인한 뒤에만 frame을 retire한다.
   이전 EA를 단순히 제거하거나 source input commit을 최종 ACK로 바꾸지 않는다.

계획 저장소를 없애려고 queue head를 batch 끝까지 잡는 정책은 선택하지 않는다.
실제949번 프레임 첫 batch에는 palette, 연속 BG 및 서로 떨어진 OBJ 슬롯이 섞인다. 이 기록으로 기존206 decoder,
260 tile producer,188 dual-chunk aperture를 실행한다. 두 staging bank가 sealed되면 뒤의 tile은 대기한다.
같은 queue head 뒤에 있는 tile 소비 명령도 진행할 수 없으면 대기가 서로를 막는다.
head 반환은 마지막 plan의 CHECK에서 word_ready가 나오는 시점으로 두었다. 마지막 tile_done까지 기다리는 것보다
이른 조건인데도11계획 중5개/96B에서 멈추고 두 staging bank가 sealed된 상태를 유지했다. 복사 후 해제 정책은11계획/288B/6chunk를 완료했다.
`guard_nes_plan268.py`는 head 유지 정책과 기존 plan RAM에 복사 후 해제하는 정책을 비교한다.
여기서 queue-head 정책과 tile byte 생산자는 test model이다. 새 통합 queue RTL을 구현·검증했다고 하지 않는다.

다음 검증 대상은 공통 SPI/CRC/identity를 사용하되 early-copy 후 head를 해제하고 기존 plan RAM을 유지하는 방식이다.
plan copy credit은 일반4 packet credit과 구분해 예약해야 한다. E0 snapshot의 plan-ready flag만 보고 여러 packet을
중복 예약하거나, plan RAM이 찬 상태에서 head가 copy를 기다리도록 하면 같은 교착을 다시 만들 수 있다.
plan RAM을 phase RAM으로 옮기는 경우에도 source/receipt/H2와 동시 수명 및 실제 read/write port 중재가 필요하다.
현재는 이 제어의 net 절감량을0으로 기록한다.

## 전체 회로 예산과 부족량

source/core/출력/tile RTL과 ARM 로드 image는267과 같지만, 이번에 보드 최상위에 남은 legacy E0/E1을 실제로 제거했다.
267의 `nes_sink_bridge165`는 새 queue 외에 옛 packet endpoint와 ACK 제어를 남겨두었다. 최상위 배타 SPI mux는 두 selected가
동시에 오면 MISO를 해제하므로 기능 결합에서도 제거해야 하는 중복이다(정적 연결 확인이며 전체 보드 실행 결과는 아니다).
`map_nes_cleanup268.py`는 legacy endpoint를 제거하고 `ROM_ONLY` bus로 기존 program ROM과 pad write만 유지한다.
12개 ROM/control/packet/release 읽기 검사, pad write/commit, E0/E1 비구동 검사를 통과했다.
이 adapter는 packet/ACK/status 주소를 새 flow에 넘긴다. 새 flow의 bus_valid는 fault/rst에서 닫히므로,
SNES의 `$6001` STOP/fault 읽기가 실제로 응답하는 전체 결합은 별도 보완·검증 대상이다. 이 비용도 아직 제품용 회로 여유로 승인하지 않았다.

한 번의 새 Quartus Lite whole-board MAP 결과는 다음과 같다.

|항목|267|268 legacy 제거|차이|
|---|---:|---:|---:|
|MAP LE|23714|22657|−1057|
|comb|18399|17679|−720|
|FF|9488|9045|−443|
|RAM bits|311904|303712|−8192|

legacy bridge의 hierarchy는746→44comb이며, 이 부모 차이를 전체 절감720과 합산하지 않는다. packet RAM1024×8은 없어지고
기존 program ROM4096×8/32768bits는 유지된다. source/tile의 외부 CHR ROM reader와 별개인 로컬 M9K ROM에서0 상수를 읽는다.
새 프로그램의 전체 link나 물리 IO 속도까지 검증한 것은 아니다. 한도15408 대비 comb2271이 초과하며,
최소12.85%의 현재 조합 논리를 더 줄여야 한다. 이는 배치·배선 여유를 포함하지 않는 초기 필요조건이다.
MAP LE를 FIT LE와 비교하지 않고, RAM bit 합계를 물리 M9K 여유로 바꾸지 않는다. 새 FIT/STA는 실행하지 않는다.
이 whole-board는267의 자원 검사 glue에서 legacy 경계를 수정한 것이며 제품 전체 기능·CDC·IO가 검증된 보드가 아니다.

서로 겹치지 않는 hierarchy 세 블록은 출력 queue571comb, 계획 endpoint446comb, plan transport410comb로 합1427comb다.
이 세 블록을 비용0으로 대체한다는 낙관적 장부에서도 `2271−1427=844comb`가 밖에 남는다.
새 공통 제어가R comb라면 밖에서 더 줄여야 할 양은 `844+R`이다. 기존 출력 queue를 그대로 두고 계획 경계856comb만
모두 없앤다는 장부에서는1415comb가 남는다. 이 계산은 합성 재매핑이나 부모 로직 변화를 예측한 실제 reclaim이 아니다.
작은 제어 통합만으로 whole-board 게이트가 통과된다고 계획하지 않는다.

wire 장부는 현재 E8 poll과 EA를 공통 상태/최종 ACK에 흡수하고 E9를16B 공통 envelope의 E1로 바꾸는 경우를 별도 표시한다.
count를 기존 header 필드에 둔다고 가정하면 E9 대비 packet당11B가 늘어난다. 실제88개 일반 plan batch와71개 END가 대상이다.
기존 plan generation을 공통 identity에서 가져오는 선택은 plan당2B, 총669개 기록의1338B를 추가로 줄일 여지가 있다.
이는 고정 transcript의 바이트 계산이며 새 decoder/ARM, credit 상태, polling 재실행 시간이나 회로 절감의 증거가 아니다.

## 목표 판정과 다음 단계

프레임 비용표는 `source_ms + output_schedule_ms` 직렬 진단을 같은16.666667ms 목표와 비교하고 프레임별 부족/잔여를 기록한다.
full RUN 입력·planner, hardware IRQ 선점·entry/exit, active VBlank, map/tile 실제65816 소비, live NES ROM 경쟁 비용은
모두 검증된 합계에 들어간 것이 아니다. `non_wire_elapsed_ms`는 직렬 진단에서 실제 SPI bit 시간을 뺀 경과 시간이며,
특정 CPU나 FSM의 독립 비용으로 귀속하지 않는다. 진단값이 목표 아래인 프레임의 잔여도 이 열린 비용들이 함께 사용해야 한다.
이 추가 여유를 임의로0으로 두거나 모든 source/output overlap을 공짜로 인정하지 않는다.

SNES 재사용의 시간 이득은 보존하되 P2는 선택하지 않는다. 다음 회로 후보는 source/core와 출력의 CRC·문맥·receipt 제어까지
교체 경계를 넓혀2271comb와 배치 여유의 회수 경로를 제시해야 한다. 공통 출력/plan frontend만의 isolated MAP나 FIT 반복은 하지 않는다.
동시에 제품의 모든 WRAM writer와 STOP에 bank-tail 유효성을 연결하고, 남은 OAM 반복 생성 및 실제 VBlank 소비를 같은 일정에 넣는다.
시간과 회로 두 게이트가 함께 열릴 때만 full-board 기능 결합과 FIT/STA로 진행한다.

## 재현과 보존

`probe_nes_ordinary268.py --mode dma|reuse --out <새 ASCII 경로>`로 각각522명령을 실행한다.
`--mode reuse --guards`는 별도33명령/전체 쓰기 영역 검사를 수행한다.
`probe_nes_refill267.py --last 975 --irq --cpu-trace <reuse CPU 결과> --plans <267 plans01> --out <새 경로>`가 통합 경로다.
`--last 907`로 DMA 비교, 여기에 `--rom-window 1`을 더해 재사용의 ROM stress를 실행한다.
`guard_nes_plan268.py --out <새 경로> --questa-bin <기존 Questa 경로>`는 두 head 수명 정책을 비교한다.
Questa 실행은 기존 승인된 FLOAT wrapper의 `-RunOnly -AfterSmokeScript`를 사용하고 한 seat에서 순서대로 수행한다.
`map_nes_cleanup268.py --guard --cpu <cpu-reuse05> --questa-bin <경로> --out <새 경로>`로 ROM/pad를 검사한다.
`map_nes_cleanup268.py --out <새 보드 경로>`는 Lite whole-board MAP 한 번을 실행한다.
완성된 증거를 비공개 `probes/nes-joint268/`에 보존한 뒤 `analyze_nes_joint268.py --base <archive> --out <새 analysis>`로 집계한다.

초기 CPU observer는 DMA 뒤 명령의 exec callback을 완료 시점으로 잘못 취급했다. Mesen이 실제 DMA 전 그 callback을
호출할 수 있으므로 실패한cpu-reuse02/cpu-dma02는 보존하고 폐기했다. 최종 observer는 실제 ACK에서 ROM/WRAM DMA count를 검사한다.
cpu-reuse03/04의 ROM·bus는 같지만, 이 단계의0 상수 `$00FF00`은165 보드 ROM decode의 hole에 있었다.
최종cpu-reuse05/DMA05는 상수를 kernel 바로 뒤 `$008235`/`$00822D`로 옮겼다. 실제CPU522명령과33guard를 다시 실행했고
ROM read count/값을 검사했다.04→05의 packet·timing·queue bus.csv가 바이트 일치하고03→05 reuse bus도 일치하므로,
이미 실행한71/3프레임 RTL retiming의 시각·주소·데이터는 최종kernel에도 그대로 적용된다. CPU ROM 자체가 같다고 하지 않는다.
`rompad-guard01`은 새 상수 주소의0과 원래FF00 hole의FF를 실제 보존한165 ROM decoder로 확인했다.
ROM·CHR·packet·ELF·원시 로그는 Git에 넣지 않는다. 라이선스·서버 로그도 증거 manifest에서 제외한다.
