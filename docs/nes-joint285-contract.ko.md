# NES285 — 조기 plan의 입력 의존성과 누락 ARM 비용

NES285: source 중 조기 plan 공급은 현재 ARM COMMITTED/raw 의존성과 FPGA lease 검사에 막힌다. 실제 M4 planner71의 원본 plan·전체 metadata8570B 일치, prefix71·늦은 CRC3·early ARM12·lease/STOP8을 검증했다. geometry68/71은 마지막 SPI block에서 확정된다. 기존 진단 일정 밖의 planner 준비·계획은 warm 12.467155..13.779964ms(CPI1/84MHz·명시 helper). 이를 직렬 재생한 정상71/제한3 일정의 warm 최대 29.542368ms, 제한907 34.971257ms이며 fullRUN은 아니다. 동일 RTL의 기존 Lite17765comb/2357부족 유지, 새 RTL/MAP/절감0; 공동 목표 미달.

이번 검토에서는 조기 공급 후보를 채택하지 않았다. 기존 2.059700ms 부족은 planner가 사전에 완성된 입력을 사용한 NES284 진단 일정의 값이다. 이번에는 그 밖에 있던 실제 planner/resident/dirty/plan 인코딩 명령을 계수했다. 아래 수치도 source 의미 확장·full RUN·하드웨어 WCET를 완성한 값은 아니다.

## 조기 공급을 막는 실제 조건

기존 Cortex-M4 planner를 그대로 컴파일하여 71프레임의 E9 plan 바이트와 map/CGRAM/OAM/HDMA/raw를 포함한 metadata 8,570B 전체를 기존 독립 fixture와 대조했다. input의 RECEIVING/COMPLETE/PREPARED/FAILED 네 상태를 905/907/954에서 호출한 12개 시험은 모두 plan 발행 0개로 거부했다. 원본 코드의 COMMITTED 조건과 raw pixel API를 완화하지 않았다.

N5 원본을 기존 실제 ARM decoder로 다시 실행했다. geometry CRC가 포함된 SPI block까지 검사를 끝내야 geometry를 사용할 수 있다. 71개 중 68개는 이 block이 최종 block이며, 제한907과 heavy952/954/955/962/963/968/970도 모두 같다. 나머지 tail: `[(905, 3, 517), (937, 1, 6), (972, 1, 6)]`. block CRC를 올바르게 다시 계산하고 stream 마지막 CRC만 손상한 3개 시험도 거부했다. 입력 마지막 검사를 생략한 조기 계획은 허용하지 않는다.

같은 planner ELF의 메모리 읽기 관찰은 905..907 모두 첫 plan 이전에 raw 512B 전체를 읽음을 확인했다. ARM compiler의 offsetof와 실제 raw fixture로 주소를 결합했다. 이 관찰 계수는 비관찰 실행과 -167/-272/-260명령 차이가 있어 시간 산정에서 제외했다(원인은 미확정). byte-exact plan 결과와 데이터 읽기 의존성만 사용한다. reads01/02의 계수 일치 실패도 보존한다.

변경하지 않은 실제 FPGA plan_batch206은 lease 없이 봉인된 plan을 fault 처리했다. 유효 plan, lease 없는 봉인, CRC 오류, generation 불일치, pending 두 bank, partial/held STOP, lease 상실의 8개 검사를 통과했다. 이미 레지스터로 디코드한 한 plan과 RAM에 대기 중인 두 packet은 구분한다. lease01은 디코드된 첫 plan도 RAM bank를 계속 점유한다는 시험 가정이 틀려 실패했고 lease02에서 바로잡았다. RAM/RTL은 바꾸지 않았다.

## 실제 ARM 비용과 전체 일정

| 항목 | 907 | 954 |
|---|---:|---:|
| planner begin+plan 명령 | 1,053,722 | 1,157,517 |
| CPI1/84MHz 환산 | 12.544310ms | 13.779964ms |
| 첫 callback까지 plan 명령 | 320,408 | 320,325 |
| 첫 묶음까지 plan 명령 | 1,046,140 | 1,016,375 |

첫 callback은 zero tile이며 ROM 요청 plan과 같지 않다. 준비(begin) 비용은 첫 callback/묶음 열에 별도로 더해야 한다. 907은 8개 plan만 있어 첫 묶음이 planner 마지막 flush까지 나오지 않는다. 최종 visible ACK에 대응하는 resident/dirty commit은 1,187명령을 별도로 과금했다. 시험의 성공 commit 호출은 물리 ACK 구현이 아니며, 재일정에서는 기존 RTL 최종 ACK 이후 비용을 넣었다.

planner probe는 -Os 실제 M4 코드와 libgcc를 실행한다. memcpy/memset/memmove/memcmp는 명시한 byte-loop helper이며 전체 펌웨어 libc가 아니다. 907에서 helper 270,006명령을 전부 무료로 둔 낙관적 민감도도 9.329952ms다. 이 값은 실측 최적화 결과가 아니다. probe text10,676B/BSS40,552B/관측 stack680B에는 진단 출력 buffer와 caller 소유 fixture가 포함되므로 target RAM 추가량으로 합산하지 않는다. canonical input 로딩은 N5→실제 planner 의미 확장의 처리 시간을 증명하지 않는다.

| 일정 | NES284(planner 제외) | NES285 직렬 planner 포함 재일정 | 변화 |
|---|---:|---:|---:|
| 일반 warm 최대(frame954) | 15.748447ms | 29.542368ms | +13.793920ms |
| 제한 ROM907 | 18.726366ms | 34.971257ms | +16.244891ms |
| 제한907의 60fps까지 부족 | 2.059700ms | 18.304590ms | |

일반 warm 한도 초과 69/69. 원래 plan/출력 압축 E1/E9 바이트, source RTL, 실제 output ARM·EXTI/WFI, SNES279 bus trace, ROM slot/priority 경쟁을 유지하고 input COMMITTED 뒤 planner 명령 비용을 재생했다. 단순 덧셈과 재일정의 차이는 비용표 `retimed_minus_frozen_ms`에 기록한다. 제한907의 재일정은 단순 합산보다 3.686450ms 길다. planner 지연으로 ROM window 위상이 달라진 결과이므로 단순 합산값 31.284807ms를 새 일정으로 채택하지 않는다. ROM 대기·SPI·ARM 비용을 다시 중복 가감하지 않는다. planner 자체와 source는 비용 replay이고 output ARM은 live다. planner 중 IRQ preemption·full STM32 NVIC는 검증하지 않았다. EXTI 진입/복귀24cycle은 기존 allocation이다.

## host·validator 공동 교체 예산

최종 NES284 board02의 Quartus Lite 전체 MAP 22,714LE/17,765comb/9,086FF/307,808 RAM bits를 사용한다. 이번 일정 RTL의 host/validator/queue/plan/SPI는 기존 최종 소스와 exact hash로 결합했다. 보드의 기존 tile_closed267 출력 포트·assign 두 줄만 시뮬레이션의 계층 참조와 달라 exact delta로 검증했다. analysis01의 직접 byte 비교 실패를 보존하고 analysis02에서 이 연결을 명시했다. 새 RTL이 없어 동일 MAP을 반복 실행하지 않았고, 입증된 회로 절감은 **0개**, 부족은 **2,357개** 그대로다. proposed 교체 회로의 비용은 null이며 기존 MAP을 새 후보 결과로 부르지 않는다.

| own 경계 | comb |
|---|---:|
| host + validator | 3,448 |
| queue + plan + common SPI | 1,361 |
| 공동 교체 범위 | 4,809 |
| 범위 밖 유지 비용 | 12,956 |
| 허용 범위 예산 | 2,452 |
| 128 여유 포함 목표 | 2,324 |

queue/plan/SPI를 그대로 두면 host+validator는 3,448→1,091 이하, 여유 포함963 이하가 필요하다. host+validator의 68.36% 이상을 줄여야 하는 규모다. 반대로 queue/plan/SPI를 전부 무료로 가정해도 996개가 부족하다. 이 산술은 FIT 결과나 달성 가능한 회로 추정이 아니다.

교체 목록은 [owner 계약](nes-boundary285-owners.json)에 고정했다. admission identity 공유, 원본 descriptor 실행 문맥, receipt/manifest RAM 진행, CRC byte service, plan/tile 수명, 최종 표시 owner를 함께 다룬다. 이미 공유된 manifest cursor와 NES283 range end는 다시 절감으로 계산하지 않는다. host의 provisional CRC mask와 ACK 후 receipt는 다른 시점의 증거이므로 제거할 중복이 아니다. SPI enqueue와 실제 SNES read tap이 함께 올 수 있어 단일 cursor/CRC accumulator도 무료로 공유할 수 없다. 원본 바이트·독립 범위/중복/map 순서·H2 검사와 ordered ACK·12B 최종 표시 ACK는 유지한다.

현재 형식의 E9 시점 이동은 ARM/RTL에서 거부된다. lease 전 보관만 허용하는 후보는 ROM 실행을 앞당기지 못하고 추가 admission/STOP 제어가 필요하다. geometry 우선 전송·speculative plan/ROM prefetch 후보는 source 순서, raw-dirty scratch 수명, epoch/lease, staging, 공유 SPI/ROM의 새 검증이 필요해 아직 시간·회로 값을 부여하지 않았다.

현재 output ARM은 terminal SEAL 사전 순회와 완성된 material에서 H2를 만든 뒤 BEGIN을 보낸다. 따라서 E9 callback만 planner 도중 보내고 bank credit에서 기다리면, 그 credit을 풀 tile 소비가 아직 만들어지지 않은 H2/BEGIN과 출력 명령을 요구할 수 있다. H2 생산을 먼저 확정하고 bounded plan 공급·출력 소비를 함께 실행해야 한다. 이는 코드의 통합 제약이며 새 RTL에서 deadlock을 관측했다는 주장은 아니다.

## 재현 범위와 다음 검토

SELECT arm04(71 비용), arm05(helper 분리3), arm06(전체 metadata 및 helper71), prefix01(71), reads03(raw 의존성3), lease02(8), test01(71), window01(3), analysis02. 새 independent host validator/STOP17 구현 변경은 없고 기존 검증을 RTL hash로 유지한다. 새 일정은 metadata/receipt/hash·token/credit·최종 ACK를 기존 oracle와 검사했다. full firmware error→STOP 발행, 새 live65816/activeVBlank, 전체 program ROM, 실제 source/planner 연결, FIT/STA와 실물60fps는 미완료다.

arm01은 sandbox DLL 시작 실패, arm02는 libgcc 자동 경로 사용 시 linker 실패 기록이다. libgcc를 동일 바이트의 ASCII private 경로로 복사한 arm03/04 이후 성공했다. 라이선스 문제는 없었다. production227/GBC164/saveSRAM은 보존했다.

실제 source N5→planner 의미 확장과 증분 plan 생성 경계를 먼저 고정한다. 68/71은 geometry가 마지막 SPI block에서 확정되므로 현 형식에서 조기 E9를 단순 이동하지 않는다. geometry 우선 전송/검증과 raw-dirty 선행 작업 분리를 비교하고 첫 유효 plan·묶음·최종 입력 COMMITTED 시점을 실제 ARM으로 계수한다. 독립 CRC/coverage·STOP·최종 ACK를 유지한 pending plan과 ROM prefetch는 epoch/lease/두 bank 수명과 공유 SPI/ROM 비용까지 포함해야 한다. 동시에 host/validator/queue/plan/commonSPI 4809comb 경계의 제거 목록을 실제 RTL로 교체해 <=2452(128 여유 목표2324)를 증명한다. queue/plan/SPI를 유지하면 host+validator3448→<=1091(여유목표963)이 필요하다. 새 matched whole Lite MAP과 planner/IRQ/ROM을 포함한 일정이 모두 통과하기 전 P2/FITSTA/실물60fps를 승인하지 않는다. 단독 FSM/FF/CRC/opcode/seed 튜닝, 자동 merge는 하지 않는다.
