# NES286 — 증분 planner·선행 H2와 공동 admission 문맥

NES286: 실제 N5→native 확장·BG group별 planner·로컬 선행 H2를 구현하고, host와 독립 validator의 admission 문맥을 공유했다. 71프레임 plan·metadata8570B·H2 일치, ARM15/RTL23 guards, 정상71·제한3 일정 PASS. warm postdecode 비용 9.409262..10.735060ms(CPI1/84MHz). 일반 최대 26.497495ms, 제한907 18.727270ms. 전체 Lite17746comb(-19)/9031FF(-55), 부족2338. 시간·회로가 모두 줄었지만 목표 미달이며 full RUN/60fps는 입증하지 않았다.

## 실제 교체 범위

기존 N5-v2 decoder를 같은 Cortex-M4 ELF에서 실행하고 canonical4910B를 native planner 의미로 확장한다. geometry 검사를 먼저 하고 로컬 H2를 만든 뒤, 최종 입력 검사 성공 후 raw를 COMMITTED 상태에 넣는다. planner는 raw admission/dirty 계산 이후 BG group 하나씩 진행하고 마지막 단계에서 OBJ/CGRAM/raw를 만든다. 모든 호출 사이 native geometry와 resident/dirty 소유권을 caller가 유지해야 한다. 현재 probe는 이 소유권을 직렬 실행으로 지키며 full firmware scheduler 계약은 아직 연결하지 않았다.

반복 group의 초기 plan 템플릿을 재사용하고 같은 row index 비교를 생략했다. BG/OBJ scratch는 해당 단계에서 쓰고 읽는 실제 수명에 따라 초기화하며 최종 출력 초기화는 유지했다. raw pixel의 6개 가변 bitplane을 함께 변환하고 상수 plane6/7을 유지했다. 만료 scratch에 poison을 채운 별도 guard도 전체 plan/metadata 일치를 검사했다. 임의 메모리를 무료로 가정하거나 기존 출력 포맷을 바꾸지 않았다.

현재도 매 프레임 모든 BG group을 순회한다. 이번 증분 경계는 group 단위로 상태를 유지하고 다음 호출에서 이어가는 방식이다. 변경된 row/workset만 재계획하는 최적화와 실제 E9 전송 중단·재개는 다음 통합 과제다.

[교체·유지 owner 계약](nes-boundary286-owners.json)에 이번 admission 구현과 아직 남은 descriptor/receipt/CRC/plan/final display 교체 경계를 구분했다.

RTL에서는 host가 수락한 84bit admission을 한 번 보관하고 epoch/raw/serial/generation을 validator에 제공한다. validator의 중복 context와 이미 검사한 bank/raw 복사본을 제거했다. incoming H2/BEGIN은 여전히 원본 admission과 독립 비교한다. H2 자신이 비교 기준을 덮어쓸 수 없다. mailbox 입력이 바뀌어도 수락한 context는 최종 ACK까지 고정된다. serial/token history는 별도 유지하며 STOP과 최종 ACK 역할도 동일하다. host 실행기와 validator FSM 전체를 통합한 구현은 아니다.

## geometry 우선 전송과 H2 비교

N5 형식은 이미 geometry를 raw보다 먼저 보낸다. 현재 block packing에서는 68/71프레임의 geometry CRC가 최종 SPI block에 들어간다. geometry CRC 직후 block을 강제로 닫는 ARM/packing 실험 arm04도 71프레임을 통과했지만 68개 block, SPI 1,020B가 추가된다. 추가 block당 wire+기존 CS8µs allocation은 0.053714ms이며 새 packetizer/IRQ/ROM 지연을 포함한 상한이 아니다. warm raw tail은17..37B로, 남은 wire+CS allocation은 약0.106..0.166ms다. geometry 정리와 H2 비용을 숨길 큰 공간으로 보기 어렵다.

선행 H2 32B는 기존 출력 ARM prelude와 71프레임 모두 일치했다. 그러나 이번 live output 경로는 기존 terminal SEAL prepass와 H2 producer를 유지했다. 로컬 선행 H2와 기존 H2 비용을 둘 다 과금했으며 아직 생산 경로 교체로 얻는 절감은 계산하지 않는다. arm04의 Python block 경계 변경은 FPGA source packetizer나 조기 ROM lease 구현이 아니다. input COMMITTED 전에 E9를 발행하지 않는다.

## 실제 ARM 비용

| 항목 | 907 | 954 |
|---|---:|---:|
| NES285 begin+planner | 12.544310ms | 13.779964ms |
| NES286 확장+geometry+H2+raw commit+증분 planner | 9.485905ms | 10.735060ms |
| 변화 | -3.058405ms | -3.044905ms |
| canonical 확장 | 0.838179ms | 0.848393ms |
| 로컬 선행 H2 | 0.143571ms | 0.143571ms |
| 확장·begin·geometry·H2 선행 합계 | 1.499036ms | 1.556107ms |
| BG group steps 합계 | 5.714440ms | 6.262893ms |
| 마지막 OBJ/CGRAM/raw step | 0.589512ms | 1.237940ms |

실제 M4 명령 수를 CPI1/84MHz로 환산한 값이다. 명시한 byte-loop memory helper와 libgcc를 포함하지만 하드웨어 WCET는 아니다. NES286은 NES285에 없던 canonical 의미 확장과 로컬 H2도 포함하므로 두 열의 작업 범위가 넓어졌음을 명시한다. 최종 ACK 후 resident/dirty commit 1,187명령은 전체 일정에서 별도 과금했다.

context124B와 로컬 H2 32B가 필요하다. probe text13,700B/BSS45,652B/관측 stack472B이며 이전 BSS40,552B보다5,100B 크다. 이 증가는 history4910B+context124B+H2 32B+decoder28B+error4B+alignment2B다. source280에서 이미 쓰던 history/decoder와 진단 buffer를 포함하므로 full target RAM 증분으로 합산하지 않는다. 반대로 context와 H2가 무료라고 주장하지도 않는다. 최대 관측 group step48,212명령, 마지막 step114,990명령은 cooperative 경계의 관측치이며 IRQ preemption/WCET 보장이 아니다.

## ARM·IRQ·ROM 경쟁을 포함한 재일정

| 항목 | NES285 | NES286 | 변화 |
|---|---:|---:|---:|
| 일반 warm 최대(frame954) | 29.542368ms | 26.497495ms | -3.044873ms |
| 제한 ROM907 | 34.971257ms | 18.727270ms | -16.243987ms |
| 제한907의60fps까지 부족 | 18.304590ms | 2.060603ms | |

일반 warm 한도 초과69/69. 원래 E1/E9 압축 전송, input COMMITTED 장벽, 실제 output ARM·EXTI/WFI와 FPGA ROM arbiter, SNES279 bus trace를 유지했다. 새 postdecode 전체 비용을 COMMITTED 뒤 직렬 재생하며 source decoder/control 비용은 기존280 replay다. planner 자체 IRQ 중단·full STM32 NVIC·전체 RUN은 실행하지 않았다. EXTI 진입/복귀24cycle은 기존 allocation이다. ROM 경쟁 시점 변화는 비용표의 `retimed_minus_frozen_ms`로 단순 명령 차감과 분리했다. 이번 결과는 source+output 진단 일정이며 activeVBlank/전체 program ROM/물리60fps 상한이 아니다.

제한907의 변화 -16.243987ms 중 명령 비용 변화는 -3.058405ms, 재일정 차이는 -13.185582ms다. ROM_WINDOW1은357368cycle 주기 중330088..354639 구간과12cycle slot 조건을 사용하는 기존 제한 fixture다. planner가 빨라져 이전에 놓친 ROM 허용 구간 안에 들어간 효과가 크다. 일반적인 phase-independent WCET나 지속60fps의 증거로 확대하지 않는다. cold905/906은 같은 허용 구간에 기다려 종료 시간이 그대로다. warm 일반 최대에는 아직 9.830828ms, 제한907에는 2.060603ms가 더 필요하다.

## 같은 경계의 Quartus Lite 전체 비용

| 항목 | NES284/285 | NES286 | 변화 |
|---|---:|---:|---:|
| LE |22,714|22,644|−70|
| 조합 논리 |17,765|17,746|−19|
| FF |9,086|9,031|−55|
| RAM bits |307,808|307,808|0|
| 장치 조합 논리 부족 |2,357|2,338|−19|

전체 Lite MAP을 한 번 실행했다. host2410/validator1029/queue128/plan571/commonSPI660=공동 경계4798comb, 이전4809보다11개 감소다. 범위 밖12948comb는 이전보다8개 감소했으며 이 합성 변화까지 구조적으로 제거한 제어의 효과라고 계산하지 않는다. 장치15408comb 기준 공동 범위 허용량2460,128여유 목표2332다. 현재 경계의48.73% 이상을 더 줄여야 한다. 회로 목표에 대한 큰 구조 교체는 여전히 미완료다.

기존 MAP 경고704건은 파일 위치·라인 번호만 정규화해 내용이 동일함을 확인했다. 경고가 없다는 뜻이 아니다. board와 simulation은 tile_closed267 출력 포트·assign 두 줄의 기존 glue 차이만 정규화해 exact source를 비교했다. 그 외 변경 RTL은 host/validator 두 파일이며 나머지는285 hash와 일치한다. FIT/STA는 수행하지 않았다.

## 검증과 보존

SELECT arm03(original packing71), arm04(forced geometry boundary71), armguards02(15), guards01(17), guards02(6), test01(normal71), window01(restricted3), board01, analysis02. 원본 plan과 metadata8570B/frame, 로컬 H2 32B가 일치한다. late stream CRC를 올바른 outer block CRC로 감싼 오류, geometry field/raw/phase/STOP/poison scratch를 실제 M4에서 거부했다. RTL은 독립 receipt/CRC/orderedACK/final coverage·STOP/RAM freeze와 H2 epoch/serial/generation/raw/bank 변조를 검사했다. 후자는 certificate CRC와 SPI CRC를 재계산해 단순 CRC 오류 검출로 대신하지 않았다. 수락하지 않은 mailbox mutation으로 원본 reference가 바뀌지 않는 것도 검사했다.

arm01/02 중간 PASS와 patch01 generator assertion 실패를 보존했다. patch01은 identity 부분 문자열을 잘못 잡아 실제 RTL 수정 전 중단했으며 patch02에서 exact anchor로 수정했다. armguards01/02는 설명 주석만 다르고 같은15검사다. Questa는 기존 Starter FLOAT, 합성은 Quartus Lite를 사용했다. production227/GBC164/saveSRAM은 변경하지 않았다.

analysis01은 강제 geometry 경계의 모든 비용이 같다고 가정해 실패했다. 실제로68프레임의 expand286 안에서 geometry_ready286이 phase2를 먼저 확인해 completed/valid 분기보다3명령 짧다. analysis02는 해당 차이만 명시적으로 허용하고 다른 모든 component와 group step의 일치를 검사한다. 두 ELF의 로드 대상 section은 동일하며 전체 ELF hash 차이는.strtab에만 있다. 원본 packing arm03을 선택한 전체 일정 비용에는 이 분리 실험의3명령 절감을 적용하지 않았다. directed RTL guards의 기존 progress_mode284/progress_irq284 미연결 경고3건은 동일하며, 실제 ARM/IRQ 일정에서는 연결된 경로를 검사했다.

geometry/raw의 단순 block 분리보다 첫 출력에 필요한 row/workset과 H2의 생산 의존성을 먼저 고정한다. 증분 planner callback을 실제 bounded E9 공급과 output 생산에 연결하고 immutable native view·credit·speculative lease·STOP의 소유권을 증명한다. 현재 source 입력 COMMITTED 장벽과 독립 CRC/coverage/H2/ordered ACK/12B 최종 ACK는 유지한다. host 실행기·validator·queue·plan·common SPI 공동 범위4798comb를 실제 제거 목록과 함께 <=2460(128여유2332)으로 줄이는 구조가 필요하다. 단순 raw-tail 분리나 identity FF 감소만으로 목표를 충족하지 못한다. planner/source 실제 IRQ preemption·full RUN과 matched whole Lite 비용을 검증한 뒤 FIT/STA/실물 gate를 검토한다. 단독 opcode/seed/FIT 반복이나 자동 merge는 하지 않는다.
