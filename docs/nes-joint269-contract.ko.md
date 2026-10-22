# NES269 — bank STOP 소유권과 source·receipt 전체 교체 예산

PR130의 R1 조사다. production227, GBC164, saveSRAM은 유지한다.
P2와 제품용60fps는 승인하지 않는다. 실제 구현은 STOP 무효화 경계이며,
source·receipt의 큰 제어 교체는 비용을 비교한 설계 후보다. 후보의 회로 절감을 구현 결과로 기록하지 않는다.

## 실제 일정 재실행 결과

|항목|268 재사용|269 STOP 결합|
|---|---:|---:|
|warm 직렬 진단 최대|18.294508ms|18.391188ms|
|16.666667ms까지 부족|1.627841ms|1.724522ms|
|warm69 중 초과|6|6|
|E0 polling 합계|3465|3547|
|전체 공유SPI B|277503|279471|

최대 frame954: source6.254970+출력12.136218ms다. CPU 상태 검사 비용과 그로 바뀐 polling을 함께 반영했다. 이 결과에는 아래 fullRUN/VBlank 등 미검증 비용이 추가로 필요하다.

|ROM 제한 frame|268 직렬 진단 ms|269 직렬 진단 ms|차이 ms|
|---|---:|---:|---:|
|905 (cold)|103.610348|103.609711|-0.000636|
|906 (cold)|116.285332|116.382149|+0.096817|
|907 (warm)|19.291450|19.291450|+0.000000|

269의954 transcript에서는 E0 조회56회와 추가full조회3회를 고정하면 short9 안의 wire 여지가768B/2.340571ms다. 추가 transfer setup을 빼면2.316571ms이며, 새 ARM/refill/poll/ROM 일정은 아직 없다.

같은 ROM/cache/priority RTL을 다시 실행했으며 CPU 시간만 기존 ROM 대기에서 빼지 않았다. 위3개 fixture는 전체 최악 상한이 아니다.


## STOP과 bank 유효성

268의 flow는 fault/reset에서 버스 전체를 닫아 `$6001`의 fault 값도 읽을 수 없었다.
269는 이 상태 주소를 별도로 열고, bit7에 STOP/fault, bit6에 양쪽 bank 재사용 표식의 무효화 요구를 둔다.
host clock의 `invalidate_banks`는 common reset/STOP에서 비동기로 세워지며 짧은 STOP이 끝나도 남는다.
fault 중에는 매 clock 다시 세워진다. SNES는 양쪽 WRAM 표식 `$50/$51`을0으로 지운 뒤
동기화된 기존 write observer를 통해 `$6006=A5`를 쓴다. STOP/fault가 남아 있으면 이 쓰기로 해제되지 않는다.
이 handshake는 기존 fault를 복구하거나 새 epoch/serial을 승인하는 명령이 아니다.

무효화가 남은 동안 일반 packet/표시/staging 읽기와 SNES ACK·consume·최종 ACK는 차단한다.
기존 source 입력, 내부 CRC·manifest·receipt 처리는 별도의 소유권을 유지한다.
일반 명령 커널은 packet DMA 전·후, 복사 후, zero DMA 후 유효 표식 발행 전, ACK 전에 상태를 읽는다.
STOP을 보면 두 표식을 지우고 현재 명령을 버린다. 외부 common STOP 복구 후 무효화 응답을 보내고 수신을 재개한다.
최종 상태 읽기와 ACK 사이에 STOP이 와도 RTL이 오래된 ACK를 무시하며 CPU는 다음 poll에서 무효화를 확인한다.

1100B zero tail `[21,1121)`의 유효 표식은 실제 DMA가 끝난 뒤에만 세운다.
일반 HDMA 쓰기가 이 구간과 겹치면 첫 쓰기 전에 해당 bank의 표식을 지운다.
prefix `[0,21)`와 raw tail `[1121,...)`은 겹치지 않는다. packet 수신과 FPGA CRC·receipt를 생략하는 최적화가 아니다.
CPU 코드565→653B, ROM zero 상수1B, 기존 추가 WRAM4B(표식2B+bank index scratch2B)는 유지한다.
상수 주소는 `$00828D`이며 기존 local program ROM decoder 안에 있다. full program link는 별도다.

실제65816 검증은522일반명령/128041논리출력B/39648PPU DMA B, cold2회2200B zero DMA와69회 재사용을 유지한다.
33범위·다른 bank 검증은28607B/10fill이다. STOP은 packet DMA 중·직후, zero DMA 중,
새 유효 표식 발행 후, 일반 MVN 쓰기 중, 부분 ACK 중, CPU가 상태를 읽기 전에 끝난 짧은 pulse의7지점이다.
10개 명령이 재시도 후 완료되고8회 무효화 응답, 오래된 ACK1회 무시,11회 zero DMA가 관측됐다.
CPU STOP 주입의 상태 장치는 test model이다. 별도 실제 RTL 상태/취소 검사가 같은6001/6006 계약을 확인한다.
CPU와 FPGA가 한 시뮬레이터에서 실시간으로 STOP을 주고받았다고 하지 않는다.
CPU의 재시도 fixture는 전체 RUN의 새 serial/token 배정·재시작 증명이 아니다.

기존 source·receipt·H2·표시 문맥의38개 오류/STOP 검사에 fault 상태 읽기, STOP 중 무효화 응답 거절,
일반 버스 차단, 오래된 ACK 무시, 이후 phase RAM 쓰기 정지를 함께 검사한다.
source COMMITTED와 최종 display ACK, capture lease retire는 여전히 서로 다른 경계다.
보드의 RUN reset이 프로그램 ROM과 최상위 버스까지 닫는 문제도 수정했다.
NES FPGA configuration의 로컬 program ROM 읽기와6001 상태 읽기는 RUN STOP 중에도 유지한다.
ROM 주소 동기화는 RUN reset과 분리하고, pad·packet·ACK는 기존 RUN/STOP 소유권을 따른다.
power reset 또는 host clock lock 손실은 여전히 최상위 IO를 닫는다.
실제 ROM/flow 모듈과 보드에서 가져온 동일 배타 mux 식을 함께 검사하며, 전체 PLL/NES 보드 시뮬레이션은 아니다.
모든 제품 WRAM writer, active VBlank, 전체 보드 reset/IO/CDC는 아직 제품 수준으로 검증하지 않았다.

## 같은 전체 보드에서의 회로 비용

268이 제거한 legacy E0/E1을 되살리지 않고, 같은 보드에서 STOP 경계만 바꿨다.
Quartus Lite의 완성된 MAP은 두 번이다. board02는 flow STOP만 추가했고,
ROM까지 RUN reset에서 철회되는 새 문제를 고친 board03을 최종 선택한다. FIT/STA는 하지 않았다.

|항목|268|269|차이|
|---|---:|---:|---:|
|MAP LE|22657|22670|+13|
|comb|17679|17692|+13|
|FF|9045|9046|+1|
|RAM bits|303712|303712|0|

flow 부모는3174→3196comb, 그 자체 로직은2184→2204comb다. 중간 board02의 전체−5를 STOP 제어 자체의 절감으로 귀속하지 않는다.
최종 ROM 소유권까지 포함한 전체+13에는 전체 재매핑과 다른 hierarchy 변화가 포함된다. 조합 논리 한도15408보다2284개 많다.
이 수치는 FIT의 packed LE 부족량이나 물리 배치 여유가 아니다. 기존240의490LE/40LAB 부족도 해결한 것이 아니다.

## source·receipt까지 넓힌 교체 범위

다음 표는 부모·자식 중복을 제외한 기존268 비용이다. output은 queue/tiles/aperture/mailbox를 제외한 부모 자체 값이다.
이 영역에는 제어뿐 아니라 source datapath·CRC·비교 연산도 포함된다. 합계를 모두 제거 가능한 중복 논리로 해석하지 않는다.

|교체 검토 영역|comb|소유권과 유지 조건|
|---|---:|---|
|source/query+receipt/H2 core|2445|NES clock query 선행 읽기, source codec, persistent validity·CRC·display lease|
|source 전송|438|2개 immutable block, D2 POP와 입력 COMMIT 분리, src/host CDC|
|output parser·완료 관리 자체|2184|일반/typed packet 해석, 실제 소비 증명, H2·manifest 순서와 final ACK|
|output queue|571|4credit, packet CRC, immutable head|
|plan SPI endpoint|446|계획 수신·CRC·상태|
|plan transport|410|계획 RAM 복사 완료와 tile 완료 분리|
|합계|6494|새 제어·포트 중재·CDC를 포함한 순절감 필요|

268 부족량2271을 이 영역만으로 회수하려면 새 영역이4223comb 이하, 약34.97% 감소해야 한다.
269의 같은 영역은 core2445+source 전송437+output 자체2204+queue571+plan446+409=6512comb다.
부족2284에 대한 장부 한도는4228comb이며, 배치/mapper 여유는 이 밖에 더 필요하다.
source core2445를 유지하고 나머지4049만 바꾸는 기존268 장부라면1778 이하, 약56.09% 감소가 필요하다.
단순 SPI endpoint 통합만으로 충분하다고 전제하지 않는다.

이미 공유한 자원도 다시 절감으로 세지 않는다.

- source512..1023과 output receipt의 phase RAM은 이미1024×8 하나다.
- persistent validity0..331와 양 bank의 raw-tail CRC64B332..395는 source 준비 중에도 보존해야 한다.
- output received396..561/map562..817, H2 832..863, display offset864..867은 표시 완료까지 수명이 있다.
- source packet CRC와 output certificate/digest의 NES-clock CRC16 계산기는 이미 공유한다.
- query 선행 읽기, source checksum와 ACK 수명, host-clock output packet CRC는 단순히 같은 레지스터로 합칠 수 없다.

source block RAM512B와 output queue1024B는 프레임 단계가 달라도 현재 포트 클록이 다르다.
클록을 선택하는 RAM mux를 공짜로 추가하지 않는다. host-clock 저장소로 옮기려면 source byte CDC/FIFO와 backpressure를,
NES-clock 저장소로 옮기려면 SPI 쓰기/읽기 CDC를 포함한다. 새 동기화 비용과 query 선행 읽기 감소를 반드시 계산한다.
plan RAM은 retained206 decoder/staging에서 증명한 early-copy 정책 때문에 유지한다.
queue head를 tile 완료까지 붙잡거나 plan copy credit을 일반4credit과 섞으면268의 교착 반례가 다시 성립한다.

후속 구현 후보는 **공통 host SPI admission/CRC·상태 생성과 RAM에 저장한 transaction 문맥**이다.
source/plan/output opcode별 포트와 중복 header·ACK 상태를 함께 대체하되,
NES query/source·receipt 메모리 연산의 권한, 각 단계의 credit/retire, 실제 SNES 소비 증명을 남긴다.
공유할 수 있는 byte 연산·문맥과 계속 필요한 CDC/카운터를 구분한 뒤 같은 전체 보드로 게이트한다.
새 source/receipt controller RTL이나 순절감량은 이번에 입증하지 않았다. `net_reclaim_proven=0`이다.

## 시간 후보를 전송·polling·ROM 경쟁까지 비교

268 최악954의 source6.254970ms 중1969SPI B의 bit 시간은6.000762ms다.
같은 source 바이트와 직렬 진단 경계에서 나머지를 전부0으로 만들어도0.254208ms밖에 줄지 않는다.
그보다 큰1.627841ms를 source FSM 속도만으로 회수한다고 계획하지 않는다.

71개 실제 source record를 다시 decode하고, row shift를 없앤 mask-only 표현도 같은348610B를 복원하는지 검사했다.
954는 source payload1758→2199B(+441), 같은 output polling 기록의 전체 wire floor는14.966857→16.310857ms다.
목표까지0.355810ms만 남아 ARM·SNES·transfer setup·ROM 대기에 쓸 여유가 크게 줄어든다.
이는 새 RTL 실행 시간이 아니며 mask-only 전체 구현이 불가능하다는 증명도 아니다. 현재 목표의 우선 후보로 선택하지 않는다.

압축 자체를 없애4398canonical B+RAW를 매 프레임 보내는 source-only 단순화는 제외한다.
954에서 기존 output transcript까지 남기면 wire만23.929905ms다.
모든 상태 poll·plan 전송을0으로 해도 같은 일반 output E1만 더한 최소18.678857ms로 초과한다.
69warm 모두 이 E1-only 하한을 넘는다. 입출력 표현 전체를 함께 바꾸는 다른 아키텍처까지 배제하는 결론은 아니다.

줄일 수 있는 전송 후보는 credit 상태와 전체 소비 문맥을 분리하는 것이다.
9B short 상태는 dummy/marker/flags/accepted16/retired16/phase/CRC8이며, token·bank·generation·tile 범위는
필요할 때 기존24B 전체 snapshot으로 조회해야 한다. 이 문맥을 삭제하거나 CRC/identity 검사를 생략하지 않는다.
954의55poll을 그대로 두고 full 조회3회를 추가하면753B/2.294857ms의 고정 transcript 여지가 있다.
추가3회 전송의 기존8µs setup을 반영하면2.270857ms다. 새 ARM 실행과 E8 refill·재poll 비용은 여기에 더 필요하다.
queue/plan 공통 envelope의 별도174B/0.530286ms 장부와도 중복을 제거한 새 일정으로 검증해야 한다.
짧은 poll은 더 자주 실행될 수 있고, 추가 조회는 ARM refill의 E8 방문과 ROM/tile 위상을 바꾼다.
따라서 이 값을 실제 절감량으로 빼거나 FPGA 면적 절감에 더하지 않는다.

## 재현과 증거 한계

`probe_nes_ordinary269.py`는 실제65816 정상522명령 및 `--guards`33범위를 실행한다.
`guard_nes_stop269.py`는7개 CPU STOP 지점을 실행한다.
`guard_nes_status269.py`는 실제 flow에서 초기 reset, 짧은 STOP, 해제 전 ACK/consume 차단과 재무장을 검사한다.
`guard_nes_joint269.py`는 기존38개 source/receipt/manifest/display fault 검증을 유지한다.
`probe_nes_refill269.py`는 실제 ARM instruction·SPI·ROM RTL과 새 CPU trace를 사용한다.
`--last 975 --irq`가71프레임, `--last 907 --rom-window 1`이 제한 ROM 창3프레임이다.
Questa는 승인된 temporary Starter FLOAT wrapper, 회로는 Lite만 사용한다.
`map_nes_joint269.py`는268 legacy 정리 이후 전체 보드 경계에 동일 flow patch를 적용한다.
`analyze_nes_boundary269.py`와 `analyze_nes_joint269.py`가 독립 표현 검사와 전체 비용표를 만든다.

실제 ARM은 serializer/refill과 service-boundary IRQ 본체이며 CPI1은 하드웨어 cycle bound가 아니다.
입력/planner/full RUN/NVIC/IRQ 진입·복귀, active VBlank, map/tile/final display의 전체65816 실행은 합계 밖이다.
ROM cache/arbiter/physical reader는 실제 RTL이지만 경쟁 core는 합성된 요청 fixture다.
제한 창3프레임은 worst-case나 물리 FPS 보장이 아니다.
전체 보드 기능/CDC/IO/STA, 모든 WRAM writer, full firmware link와 SRAM margin도 남는다.

실패한 joint01 선언 순서, board01 보드 전용 tile 종료 포트 누락, cpu-stop01 검사 개수 불일치, status01 TB wire 선언과 guards01 TB 지역 변수 오류는 보존한다.
joint02부터 RTL 선언 순서가 수정됐고, board02는 보드 port를 보존한 flow patch다. 최종 board03은 STOP 중 ROM/상태 실행을 유지한다.
cpu-stop02/03의 성공 검사를 유지하되 새 표식 발행과 STOP 후 packet/ROM 데이터를 고의로 손상시킨 cpu-stop04를 선택한다.
joint02 이후 소스 생성 함수의 refactor는 같은 flow RTL을 생성함을 최종 분석에서 바이트 단위로 확인한다.
ROM/CHR/packet/ELF/원시 로그는 비공개 증거에 보존하고 Git에 넣지 않는다.
