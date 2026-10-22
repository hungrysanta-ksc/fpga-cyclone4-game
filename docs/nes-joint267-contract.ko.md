# NES267 — ARM refill·ROM 경쟁·일반65816을 포함한 비용 게이트

PR130 / `codex/nes-wholepath-boundary-256`. 생산 기준227, GBC164와 saveSRAM은 그대로다.
266의 부분 회로 절감은 제품 선택의 근거가 되지 않는다. 실제 ARM refill과 tile 계획 전송을 같은 SPI에 붙이고,
일반65816 명령의 실행 추적을 연결한 뒤, 기존 보드에서 실제로 제거할 수 있는 제어만 제거해 비교한다.

## 최종 비교 결과

|같은 whole-board MAP 경계|공유 전265|H2 공유266|
|---|---:|---:|
|LE|23816|23714|
|comb|18301|18399|
|FF|9657|9488|
|RAM_bits|311904|311904|

240 whole-board MAP은19809LE/14966comb/8577FF/311904bits였다. 새 구조는 comb 2991개가 칩 한도를 넘는다. MAP 실행 성공은 자원 적합 판정이 아니다. 기존240 FIT의490LE/40LAB 부족이 해결됐다고 하지 않는다.

|frame|공유 전 출력 ms|H2 공유 출력 ms|차이 µs|qualified-window 출력 ms|
|---|---:|---:|---:|---:|
|905|44.561556|44.561556|+0.000|85.295022|
|906|47.790608|47.790608|+0.000|112.455741|
|907|10.372694|10.372694|+0.000|16.949160|

71프레임의 warm 출력 최대는15.484178ms, source+출력 직렬 진단 최대는20.909704ms(frame954)다. warm69 중25개가16.667ms를 넘는다. 이 일정에 이미 포함된 ARM/SPI/IRQ 본체 시간을 다시 더하지 않는다.

## 이번에 연결한 경계

- ARM: 실제 Cortex-M4 serializer264 + 신규 E8/E9 계획 refill/EA retire 코드267을 Unicorn에서 실행한다.
  E0 credit 응답과 E8 plan-ready 응답은 실행 중인 RTL에서 받는다. 임의의 성공 응답이나 패킷당 poll 1회로 대체하지 않는다.
  네 패킷 credit, tile barrier, token/sequence, manifest 순서, final display 후 EA retire를 유지한다.
- 계획: 실제2472 C planner/sorter를 다시 실행하고, 기존1039 요청과71 bank 결과의 바이트 일치를 검사했다.
  598 tile 계획의 encoded batch를 사용한다. 이 planner의 전체 ARM 실행 시간은 아직 포함하지 않았다.
- FPGA: 실제 E8/E9 endpoint, plan batch RAM/decoder, tile205, CHR cache, core-priority arbiter,
  READ16 physical ROM reader를 연결했다. 검증 ROM에서 읽은 tile 결과를 기존 변환 결과와 매 바이트 비교한다.
- IRQ: 기존233 ELF의 SysTick/TIM2 함수 본체를 변경 없이 실행한다. 통합 일정에는 10ms 주기의 SysTick 본체를
  SPI 호출 경계에서 서비스한다. NVIC 선점, 진입/복귀, 우선순위·중첩, 하드웨어 wait state는 모델링하지 않았다.
- SNES: 374B의 실제65816 프로그램이 일반 명령522개를 처리한다. packet→WRAM DMA, literal/pattern MVN,
  반복 채우기 MVN, CGRAM/OAM DMA와 ordered ACK를 실행해128,041B의 결과를 검사했다.
  실제 버스의 주소·데이터·master-clock 간격을 RTL에 재생하며, live ARM이 보낸 패킷과 모두 일치해야 한다.

따라서 이번 실행은 **실제 ARM 코드 + 실제 ROM RTL + 실제65816 일반 명령 버스 추적**이다.
동시에 실행되는 전체 ARM RUN/실제 NES CPU/전체65816 표시 프로그램의 검증은 아니다.
65816 일반 명령은 forced blank에서 측정했다. map/tile DMA 소비와 마지막 표시 ACK는 기존 native bus 모델이며,
266의 실제 표시/HDMA/VBlank/ACK 검증은 별도 선행 증거다. 이 둘을 무조건 합쳐 실기 전체 프레임 시간으로 부르지 않는다.

## 시간 계산 규칙

ARM instruction당1cycle,84MHz는 명시적인 CPI1 민감도다. 실제 instruction 수와 RTL의 SPI/ROM/consumer 대기는 관측값이다.
SPI 2.625MHz와8µs SS 간격, 실제 credit 응답을 사용했다. 파일 rendezvous의 호스트 대기 시간은 RTL 시간을 진행시키지 않는다.
ARM 시간·E0/E8 polling·SPI 전송·일반 소비가 출력 일정 안에서 겹치므로 이미 포함한 항목을 다시 더하지 않는다.

실행된71프레임의 출력 SPI224118B 중 E0는5380회/129120B(57.6%)다. source 측 제어까지 포함한 실제 SPI는99345B이며,
공유 버스 합계는323463B다. 현재 polling 정책의954프레임은5559B/순수 wire16.941714ms,
970은5477B/16.691810ms로, SS 간격이나 나머지 비용을 더하기 전에도16.667ms를 넘는다.
이는 현재 실행된 일정의 실패다. polling이나 소비 순서가 다른 모든 구조의 불가능성으로 일반화하지 않는다.

`diagnostic_serial_ms = source 관측시간 + 통합 출력 일정`이다. source 수신기는 기존 SV fixture이며 실제 ARM 입력 decoder와
전체 planner 시간, active-display VBlank, 전체IRQ 비용이 빠져 있다. 이 합은 실기 WCET도60fps 승인도 아니다.

71프레임의 ROM_WINDOW0는 모든 fill slot을 허용하면서 주기적인 core 요청을 넣는 낙관적 일정이다.
ROM_WINDOW1은 기존 qualified-slot 창과 주기적인 core 요청을 적용하는 명시적 stress 입력이다.
둘 모두 실제 NES CPU workload에서 발생한 요청 시각이 아니다. 좁은 창의 결과는 해당 stress 조건의 결과로만 판단한다.

window02는 같은 회로의905프레임에 관측만 추가했다. cache 앞 tile 대기957650cycle 중957491cycle은 비허용 슬롯,
159회는 허용 슬롯에서 core 요청이 우선권을 차지한 경우였다. 이159회는 실제 core 주소 선택과 fill 미승인도 검사했다.
완료 시간85.295021902ms는 window01과 정확히 같다. 기존 `arb_request && !arb_ready` 카운터는 cache가 ready에 따라
요청을 제한하므로0이 나와도 경쟁이 없다는 뜻이 아니다. 이 값은 경쟁량 판단에 사용하지 않는다.

## 보드 교체 경계와 비용

기존240 whole-board 프로젝트를 복사해 source240, 이전 tile bulk206와 소비 control194를 제거한다.
새 source/core/출력 queue/parser/staging/receipt/display 경계를 넣는다. 원래 capture lease, fault/reset shell,
E8/E9 endpoint, plan decoder/RAM, tile/cache/arbiter, loader와 공유하는 physical ROM reader는 유지한다.
중복 capture lease나 두 번째 physical reader를 추가하지 않는다. source input commit과 final display ACK는 별개이며,
최종 표시가 끝나고 EA가 승인돼야 원래 capture lease를 retire한다.

이 보드 glue는 **자원 검사용 통합**이며 실제 보드 기능·CDC·STA 승인이 아니다. Quartus Lite MAP의 조합 논리 수가
칩 한도를 이미 넘으면 FIT를 반복하지 않는다. MAP의 LE와 FIT의 packed LE는 서로 다른 수치다.
부모/자식 hierarchy 합계도 중복해서 더하지 않는다. RAM bits가 같아도 물리 M9K 배치 여유를 뜻하지 않는다.

최종 수치는 [검증 JSON](../analysis/joint267-verification.json)과 [프레임 비용표](../analysis/joint267-costs.csv)를 따른다.

board02의 hierarchy에서는 새 source/core가2913comb/976FF, 출력 경계가3171comb/1661FF다.
기존240의 source는2092comb/974FF, 제거 대상 tile bulk와 control은 각각465comb/512FF와100comb/174FF였다.
이는 비용이 커진 위치를 찾는 단서다. 부모 합계·최적화 이동·공유 제어 때문에 이 숫자를 더하거나 빼서 보드 절감량으로 사용하지 않는다.
보드 전체 비교를 따로 수행하며, 유지되는 plan/ROM 경계만도1825comb/900FF/8192RAMbits다.

## 증거와 제한

비공개 원본은 `probes/nes-joint267/`에 보존한다. ROM/CHR/패킷·실행 추적·ELF는 Git에 올리지 않는다.
공개 도구는 기존 단계의 고정된 fixture와 도구 경로를 사용하는 재현 도구다. 라이선스 원본/서버 로그는 증거 묶음에서 제외한다.

- 선택: joint04(71), joint03(3), compare01(265 비교), window01(qualified ROM), window02(core 우선 관측), cpu05, plans01, irq01,
  board02(266), board26501, analysis02. analysis01도 보존한다. 각 결과와 SHA는 최종 검증 파일에 기록한다.
- cpu04→cpu05는 DMA 중 실행 callback이 먼저 호출되는 계측 문제를 수정했다. ROM와 bus.csv는 바이트가 같다.
  음수 read_clocks가 있던 cpu04의 분할 시간은 사용하지 않는다. 통합 실행의 실제 bus timestamp는 동일하다.
- board01은 SPI 출력 mux 누락으로 출력 undriven 경고가 발생해 폐기했다. board02의 유지 mux와 출력 연결을 검사했다.
- 이전 컴파일 실패, DLL export, 일시적인 파일 lock, timestamp 포맷 문제와 중간 결과를 모두 보존한다.
  이들은 새 Questa 라이선스 문제로 분류하지 않는다.
- IRQ 본체 관측 stack32B는 기존 전체IRQ reserve508B를 대체하지 않는다. serializer/refill의 text3104B,
  bss604B, 관측 stack192B도 전체 RUN 메모리 여유가 아니다. emulator fixture 영역은 target SRAM 예산으로 승인하지 않았다.
  264 standalone 대비 text+632B, bss+292B, 관측 stack+48B다. 이 차이를233의 full RUN 여유에서 단순히 빼서 승인하지 않는다.
- 266의38오류 검사는 선행 증거다. 신규 ARM/ROM/board glue의 STOP·abort·IRQ 선점 조합을 이번 정상 replay로 검증했다고 하지 않는다.

재현 순서는 `prepare_nes_tiles267.py --out <plans> --rom <검증된 사용자 ROM>`,
`probe_nes_ordinary267.py --out <cpu>`, `probe_nes_irq267.py --out <irq>`,
`probe_nes_refill267.py --out <joint> --last 975 --irq --plans <plans> --cpu-trace <cpu> --questa-bin <기존 Questa 경로>`다.
Questa 명령은 승인된 FLOAT wrapper의 `-RunOnly -AfterSmokeScript <절대 job 경로>`로 실행한다.
265 비교에는 `--last 907 --baseline265`, ROM 창 stress에는 `--last 907 --rom-window 1`을 사용한다.
한 seat이므로 시뮬레이션은 순서대로 실행한다. `map_nes_board267.py --test <통과한 joint> --out <board>`는 Lite만 호출한다.
출력 디렉터리는 새 ASCII 경로여야 하며, 기존 결과를 덮어쓰지 않는다. 완성된 원시 증거를 archive한 후
`analyze_nes_joint267.py --base <archive> --out <새 analysis> --contention window02`로 시간·면적과 입력 해시를 검증한다.

## 다음 판단

P2를 선택하지 않는다. H2/phase RAM 공유의 국소 이득과 전체 자원 게이트 실패를 함께 보존한다.
실제 일반 명령에서는 매 프레임 `op5 / section5 / offset21 / count1100 / pattern0000`이 남아 있다.
71회 각각 약2.887–2.890ms가 걸린다. OAM의 `00f00000` 반복 명령도71회, 각각1.328–1.560ms다.
전송 payload는 작아도 SNES의 반복 생성 비용은 작지 않다. 고정 source DMA 또는 bank별 유효 범위의 재사용은
후보로 비교할 가치가 있지만 아직 새 구현/절감 실측이 아니다. 비활성 범위라고 무조건 쓰기를 생략하지 않으며,
잔존 OAM sprite, HDMA 종료 byte, receipt 요구 범위와 abort 후 bank 무효화를 먼저 증명해야 한다.
SNES 처리가 빨라지면 E0 대기 polling도 함께 바뀐다. CPU 절감 시간과 줄어든 polling wire 시간을 독립적으로 더하지 않고,
변경한 실제 명령 추적과 live credit 응답을 다시 같은 일정으로 실행해야 한다.

다음 후보는 E0 출력 queue와 E8/E9 tile 계획의 별도 admission/identity/retire 제어를 함께 대체하거나,
source 변환·검증 역할을 다시 배분하는 구조여야 한다. 계획 생산/입력 수신의 실제 ARM 비용, polling·SPI량,
동시 RAM 수명, mapper 여유까지 같은 경계에서 비교한 뒤 최소 구현을 정한다.
SNES 채우기만 빨라져도 이번 whole-board 회로 부족이 자동으로 해결되지는 않는다.
독립 FSM·opcode·seed 수정이나 FIT 반복으로 넘어가지 않는다.
