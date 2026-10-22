# NES287 — row planner의 실제 전송과 descriptor·receipt 공동 실행

NES287: checked row planner를 같은 ARM ELF의 실제 E9/credit/refill·IRQ에 연결하고 H2의 metadata8570B 복사를 native view로 대체했다. host receipt 진행을 validator의 단일 descriptor RAM walk로 옮겼다. 71프레임 plan·metadata·실제 E1/E9 일치, STOP/최종ACK25·범위315·ARM/H2/IRQ 검증 PASS. 일반 warm 최대 26.375411ms, 제한907 18.727048ms. 전체 Lite 17671comb(-75), 부족2263; 기존5블록은 +8, 연결 논리 포함 교체 범위는 -36comb다. 전체60fps·회로 목표는 미달이다.

## 실제로 연결·교체한 부분

ARM은 기존 map의 slot을 힌트로 삼아 ordinary row의 33개 cell을 먼저 검사한다. retained tag, 현재 프레임 exact key, map 속성, generation과 target bank 유효성이 모두 맞아야 재사용한다. target bank에 없는 타일은 재사용 row에서도 실제 tile callback을 발행한다. row 하나라도 일치하지 않거나 예외가 있으면 기존 allocator와 full group 계산으로 돌아간다. 새로운 영구 row-cache RAM은 없다. 71프레임의 2,059개 row 중 1,280개가 이 경로를 사용하고 779개가 기존 계산을 사용했다.

같은 Cortex-M4 ELF에서 원본 N5 decoder·canonical 확장, geometry/H2, row planner, E9 serializer/refill, 출력 실행기와 EXTI handler를 실행한다. 완성된 배치만 기존 2개 plan bank의 checked credit에 맞춰 최대 두 개 공급한다. 두 bank가 바쁘면 선행 공급은 WFI로 기다리지 않고 다음 row 계산으로 돌아간다. 일반 출력 단계에서는 기존 progress IRQ/WFI를 사용한다. 각 group 경계의 비SPI checkpoint가 실제 ARM 명령 비용만큼 RTL 시간을 진행시킨다. 입력 COMMITTED 전 실행이나 새 speculative ROM lease는 도입하지 않았다.

새 planner가 만든 E9를 실제 SPI pin과 plan RAM·tile ROM·staging·DMA receipt까지 전달한다. 전체8570B metadata는 실제 native view에서 읽어 독립 oracle와 비교한다. H2도 이 native view를 읽는다. 기존 일반 명령·map·manifest의 command template는 기록된 입력을 유지하고, live ARM serializer/credit/token/queue가 실제 전송한다. 따라서 ordinary command 생산까지 모두 새 planner에서 스트리밍 생성하는 full firmware 구현이라는 주장은 하지 않는다. E1/E9 전송 바이트는 NES286과 프레임별 exact 비교했다.

처음 연결한 test03은 metadata8570B를 평탄화해 H2에 전달했다. 이 복사와 END 연결에42,938명령이 들었다. 최종 test05/test06은 H2가 원본 scroll·raw table·length를 직접 읽고 END만 연결해25명령을 쓴다. native raw 구조에는 length 앞에1B padding이 있으므로 CRC의249B 의미열은243B table와6B length로 명시적으로 읽는다. padding poison, 잘못된 scroll/mode/bank repeat/base/length 검사와 raw0에서 만료 raw table poison을 무시한 정확한 H2도 실행했다. 이는 raw0 전체 전송/표시 전환 검증은 아니다. 원본 H2 의미검사는 유지하고 로컬 선행 H2 비용과 출력 H2 비용을 모두 계산한다.

FPGA host의 반복 receipt subrange 진행을 제거하고 original descriptor를 ACK 후 한 번 변환해 validator에 맡긴다. validator의 기존 exclusive end와 RAM byte cursor가 CHR→HDMA 경계까지 진행한다. host는 완료를 기다린 다음 queue를 retire한다. CRC 완료16bit mask도 validator로 이동해 provisional hash와 receipt write 권한을 같은 소유자가 관리한다. raw receipt의 해당 CRC bit가 빠졌으면 RAM write를 억제하고 fault7을 낸다. manifest 전용 opos/oend만9bit로 유지하며 일반 receipt cursor로 쓰지 않는다.

독립 검사, 원본 payload의 정확한 SNES read/ordered ACK, map 범위 순서·중복 검사, CRC/H2/coverage, STOP/RAM freeze, token과 최종12B display read/ACK는 유지한다. resident/dirty commit은 checked EA plan retirement 뒤에 실행한다. 실제 plan 경로의 retire_permitted가 flow_retired에 묶여 있어 frame259의 queue drain만으로 최종 표시 ACK를 대신하지 않는다. host 실행기와 validator의 모든 FSM을 하나로 대체한 것은 아니다. [교체 범위와 예산](nes-boundary287-owners.json)에 제거한 제어와 남은 제어를 구분했다.

## 시간 비교

| 항목 | NES286 | NES287 | 변화 |
|---|---:|---:|---:|
| standalone ARM907 postdecode |9.485905ms|5.713560ms|-3.772345ms|
| standalone ARM954 postdecode |10.735060ms|10.503679ms|-0.231381ms|
| 일반907 전체 진단 일정 |18.233867ms|14.521280ms|-3.712587ms|
| 일반 warm 최대 |26.497495ms|26.375411ms|-0.122084ms|
| 제한 ROM907 |18.727270ms|18.727048ms|-0.000222ms|
| cold905 |76.764392ms|78.174698ms|+1.410307ms|
| cold906 |57.642167ms|54.874978ms|-2.767189ms|

일반 warm 최대는 frame954이다. 16.666667ms까지 9.708744ms를 더 줄여야 한다. 제한907의 잔여 부족은 2.060381ms이며 여유는 -2.060381ms다. warm69 중 한도 초과는47개다. 1µs 이상 회귀한 warm 프레임은 960, 963이며 최대 회귀는 136.640µs다. 최악값의 소폭 개선을 모든 프레임의 개선으로 해석하지 않는다. 시작 두 프레임은 별도로 보고하고 warm60fps 주장에 섞지 않는다. [71프레임 비용표](../analysis/joint287-costs.csv), [제한 ROM 비용표](../analysis/joint287-restricted.csv)에 source·live planner/output·E2/E9·IRQ 대기·ROM 경쟁을 함께 기록했다.

row 재사용은907에서29/29지만954는5/29,963은5/29,970은4/29에 그친다. heavy 프레임의 대부분 row가 full fallback하므로 대표907의 개선을 전체 최악 비용으로 일반화하면 안 된다. 이번 선행 공급은 E9/tile ROM에 한정된다. H2/BEGIN·ordinary DMA는 아직 전체 planner 뒤에 시작하므로 heavy planner와 모든 출력 실행을 겹친 것은 아니다. 선행 E9가 시작됐다는 이유로 해당10ms 안팎의 planner 비용을 무료 처리하지 않는다. 정상/제한 일정은 실제 ARM 실행으로 재측정했으며 standalone planner 절감을 단순히 이전 일정에서 빼지 않았다. source clock counter와 live output elapsed time을 같은 이전 정의로 합산했다.

비용은 CPI1/84MHz와 EXTI entry/exit24cycle allocation이며 하드웨어 WCET가 아니다. source SPI/decoder/control은 기존280의 측정 명령 재생을 유지한다. 새 ELF의 decoder는 material을 만들기 위해 실제 실행하지만 그 명령은 output 시간에서 제외해 source 비용과 중복 계산하지 않는다. material 재구성용 block286 wrapper는 원본 block280보다 block당5명령, 프레임당10..130명령(0.119..1.548µs)이 더 든다. 이 probe 전용 wrapper는 제외한 material 실행에 속하며 비용표에 별도의 비재일정 민감도로 명시했다. 이를 실제 source firmware 비용으로 검증한 것처럼 합치지 않는다. full source firmware/RUN과 임의 시점 IRQ preemption의 상한은 아직 없다. 실제 IRQ를 row touch 진입 중 주입한 directed test는8word frame 복구와29row plan 일치를 확인했으나 모든 명령·우선순위 조합의 증명은 아니다.

CPU279의 실제 ordinary65816 bus trace를 재사용한다. tile/map DMA와 최종 display는 기존 bus model이며 새 live65816·active VBlank·전체 program ROM·실물 지속60fps는 입증하지 않았다. 제한 ROM은 기존357368cycle 주기 중330088..354639와12cycle slot을 그대로 사용한다. 일정 위상에 따라 기다리는 구간이 바뀔 수 있다.

일반907의3.712587ms 절감과 달리 제한907은0.222µs만 줄었다. 제한907의 slot wait는21,160→110,230cycle(+89,070), core priority 차단은14회로 같다. 먼저 끝난 planner가 같은 좁은 ROM 공급 창을 기다리면서 절감이 완료 시간으로 이어지지 않는 위상 의존을 보여준다. slot wait는 다른 실행과 겹칠 수 있으므로 이 counter를 전체 시간에 다시 더하지 않는다. 선행 프레임의 완료 시점도 달라진 연속 일정 비교이며 단독907의 모든 위상에 대한 최악 상한은 아니다.

## 같은 보드 경계의 Quartus Lite

| 항목 | NES286 | NES287 | 변화 |
|---|---:|---:|---:|
| LE |22,644|22,569|-75|
| 조합 논리 |17,746|17,671|-75|
| FF |9,031|9,025|-6|
| RAM bits |307,808|307,808|+0|
| 조합 논리 초과 |2,338|2,263|-75|

host 2361comb(−49), validator 1090(+61), queue 129(+1), plan 568(−3), common SPI 658(−2)다. 공동 범위는4798→4806(+8)로 **오히려 늘었다**. 범위 밖은12948→12865(-83)이며 전체−75를 공동 실행기 구조 절감으로 귀속하지 않는다. 현재 outside 비용을 유지하면 공동 범위 예산은2543,128여유 목표는2415다. 현재 공동 범위의47.09%를 더 줄여야 장치 comb 한도15408 안에 들어간다. 이는 필요한 최소 comb 감소량이며 실제 LE/LAB 배치·배선·타이밍까지 통과한다는 뜻은 아니다.

두 연결 wrapper own logic도 같은 old/new 기준으로 추가하면 native_joint267은72→26, joint257 core glue는19→21이다. wrapper 합계91→47(−44)을 더한 확장 경계는4889→4853(-36), 범위 밖 변화는-39comb다. 이 확장 경계의 예산은2590,128여유 목표2462다. 기존5블록 수치를 없애거나 parent inclusive 비용을 중복 합산하지 않았다. 전체−75 중 연결 제어를 포함한−36과 나머지−39를 구분한다.

한 번의 matched whole Lite MAP이며 FIT/STA는 실행하지 않았다. 704→706 경고는 새 unused hoff/boff2개와 descriptor endpoint16/17→12bit 절단2개, 기존32→12bit 절단2개 제거로 설명된다. hoff/boff는 제거한 subrange 실행기의 dead wire로 합성에서 제거된다. endpoint는 기존 domain/alignment admission 검사를 통과한 범위만 receipt 상태에 들어간다. 유효 end의 상한은 BG1024/OBJ1152/CGRAM1184/CHR·HDMA1328이므로12bit 안에 들어가며,315개 unit 경계 검사와 실제 payload 경로를 함께 검사했다. undriven 신호 경고는 없다. 기존 다른 경고를 해결했다고 주장하지 않는다.

## 재현 진입점

repository-nes-milestone에서 기존 private probe fixture와 compiler를 사용한다. 새 실행마다 다른 ASCII 출력 폴더를 지정한다. ARM 단독은 `tools/probe_nes_planner287.py --out <arm-dir> --last 975`, live 일정은 `tools/probe_nes_live287.py --out <run-dir> --last 975 --irq --plans ../probes/nes-joint284/test04 --cpu-trace ../probes/nes-joint279/cpu01 --questa-bin <Questa-bin>`이다. 제한 조건은 같은 live script의 `--last 907 --rom-window 1`이다.

Questa 명령은 AGENTS.md에 지정된 기존 `probe_float.ps1 -RunOnly -AfterSmokeScript <absolute-job.ps1>` 안에서 순차 실행한다. whole 합성은 `tools/map_nes_joint287.py --out <board-dir>`로 설치된 Quartus Lite를 사용한다. range315는 `guard_nes_range287.py`, 통합 오류 검사는 `guard_nes_joint287.py --cases 3,23,24,39-52,56-63`, ARM은 planner286/rows287/irq287/h2287 guard 진입점으로 재현한다. 이 저장소는 private fixture/ROM/license 원본을 새로 공개하지 않는다. 분석 JSON의 input hash와 private archive가 실행 입력·생성 RTL·ELF를 연결한다.

## ARM 저장 공간과 검증 경계

최종 통합 ELF는 text22,214B/BSS46,292B, 관측 stack472B다. 단독 row planner는 text14,356/BSS45,660이고 row 통계8B가 추가됐다. 처음 통합 후보 text22,298/BSS54,862에서 native H2 view로 text84B와 BSS8570B를 제거했다. 이 수치는 source history, planner scratch, 진단용 output8192B를 포함한 probe의 총량이며 실제 firmware RAM 증분이 아니다. 두 FPGA plan bank의 credit은 bounded이지만 ARM 진단 buffer를 bounded streaming memory로 교체한 상태는 아니다. 이 corpus의 최대 plan은671B, END 포함677B이며8192B 안에 들어감을 검사했다. pack287은 이 검증된 진단 corpus를 호출 전제로 하며 일반 target producer의 용량 정책을 완성한 구현이 아니다.

SELECT arm02(71), armguard01(15), rowguard03(5), irqguard02(8 IRQ cases/33 wake exceptions+row touch1), h2guard03(8), guards01의선행23PASS+guards02(62/63), range03(315), test06(71), window01(3), board01, analysis01. actual E1/E9, 전체 metadata8570B, H2, receipt754B, CRC64B를 기존 독립 기준과 비교한다. malformed geometry/raw/late CRC, stale slot/attribute, wrong exact key, 중간 STOP, ordered ACK, H2 field변조, receipt CRC누락과 최종 ACK를 유지했다.

test01은 generator anchor assertion, test02는 무제한 MMIO hook의 Unicorn IT-state 실패다. 같은 ELF는 기본 ARM 실행기와 MMIO주소로 제한한 어댑터에서 통과했으며 decoder 바이트를 바꾸지 않았다. rowguard01 문법 오류와 rowguard02의 비활성 map영역까지 poison한 잘못된 oracle도 보존했다. guards01 case62는 map range를 raw CRC range로 잘못 선택한 테스트 실패로, nonmap 조건을 추가한 guards02에서62/63을 통과했다. 그 전23PASS는 로그·RTL hash를 별도로 검증한다. range01은 구형 bank register deposit, range02는 serial0→bank1을 bank0으로 가정한 fixture 오류이고 range03은 admission serial1에 연결했다. h2guard01의 bank repeat mutation은 원래 값127과 같았으므로 guard02는 실제 byte 변경을 먼저 확인한다.

test03은 복사형 live3 PASS, test04는 같은 복사형71 실행을 native view 교체를 위해 명시적으로 중단한 기록이다. test05는 최종 view형3 PASS다. 실패·중간 PASS·중단 기록은 삭제하지 않는다. Questa는 승인된 Starter FLOAT, 합성은 Quartus Lite를 사용했다. production227/GBC164/saveSRAM은 변경하지 않았다.

## 다음 교체 범위

row 전체 fallback이 많은954/963/970의 실제 변경 cell·workset을 기준으로 planner 비용을 줄인다. input COMMITTED·raw 검사 후의 로컬 H2/BEGIN과 준비된 row 출력 생산을 연결해 전체 planner 완료 뒤에만 ordinary DMA가 시작되는 직렬 장벽을 검토한다. 원본 ordinary command/manifest 생산도 native view와 bounded batch 소비에 연결한다. 진단용8192B plan buffer 제거와 source live ARM/IRQ까지 소유권을 명시한다. host/validator/queue/plan/SPI와 두 연결 wrapper의 own logic을 합친4853comb를 실제 descriptor 저장·물리 읽기·receipt 완료 제어와 함께 <= 2590(128여유 2462)로 줄이는 교체가 필요하다. 기존5블록 경계4806와 예산2543도 비교용으로 유지한다. 독립 CRC/H2/coverage, input COMMITTED, token/credit, STOP와 최종12B ACK를 유지한다. 정상·제한 ROM phase 전체 시간과 같은 whole Lite 경계를 함께 검증하며 단독 opcode/seed/FIT 반복이나 자동 merge는 하지 않는다.
