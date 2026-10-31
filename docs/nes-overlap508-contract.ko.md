# NES508 — bulk 완료 추적과 END 뒤 일반 packet 공급

실기 기준 **MMC502/489 SNES,10.59fps**를 유지한다.508은506 ARM에 실제로 연결한 후보이며 새 전달본·실기 FPS·메뉴 시험 결과가 아니다. PR140 동일 브랜치다. [검증 집계](../analysis/overlap508-verification.json), [507 보드](nes-fault507-contract.ko.md), [계획](nes-budget504-plan.json)을 함께 읽는다.

## 교체한 제어와 소유권

기존 `nes_plan200_finish`의 END 발행과 전체 소비 대기를 나눴다. END 수락 뒤 `nes_sink212_seal`의 기존 직렬화 함수를 실행하고, **packet sequence와 BUSY 상태를 잡기 전에** plan 진행을 서비스한다. 준비된 bulk는 소비 완료까지 우선 처리한다. producer가 ROM을 기다리며 head가 없는 순간에만 일반 packet 하나를 공급한다. 기존 4credit·2bulk bank·압축·serializer를 그대로 사용하고 payload의 임시 포인터를 저장하지 않는다. 전송 중 callback 재진입은 없다.

`complete485`의 `window.last[0]==7` 의존성을 삭제했다. bulk 발행 직후의16bit sent counter를 `bulk_until`로 저장하고 검증된 retired counter가 그 지점까지 도달했는지 확인한다. sent−target≤4와 기존 accepted/pending/delta/used/CRC/flag 검사를 유지한다. queue가 모두 비면 최신 packet의 전체 ACK identity도 다시 검사한다. 중간 watermark는 FPGA가 **각 packet의12B ACK를 검사한 뒤에만** retired를 올린다는 기존 경계를 이용한다. 최종 표시 ACK를 대신하지 않는다.

현재 정책은 ready bulk를 기다리는 동안 ordinary를 추가하지 않는 보수적인 우선순위다. 부분 watermark 자체는 직접 검사하고, 실제 연속 경로는 END 뒤 ROM 대기 중 일반 공급에 사용한다. 이를 모든 bulk 대기를 숨겼다고 해석하지 않는다. END 뒤 새 plan/중복 END를 거부하고, SEAL 전에는 모든 tile 소비를 완료한다. 기존 barrier가 ordinary를 모두 drain한 뒤 SEAL을 보내고, 최종 ACK→resident commit→EA 순서를 지킨다. STOP/deadline/IO 실패는 기존 guard·first error·abort 경로로 간다.

## 실제 코드 검증

`tools/nes_overlap508.py`로506의7개 파일을 교체하여 실제 M4 firmware를 빌드했다. linked M4 검사34개가 통과했다.

- plan 정상/CRC/세대/같은 token 변조/old token/ACK/accepted/중간 STOP/모호한 E1 결과10개.
- 실제 bulk와 ordinary를 섞는 정상/STOP2개. sequence를 bulk 서비스 이후에 잡고 STOP 뒤 새 packet·EA가 없는지 확인했다.
- 일반 counter와65534→0 wrap에서 partial/full 완료, future/stale target, future retire, identity/accepted/CRC/FPGA fault18개.
- 실제 native runtime guard·SEAL·window·resident 경로의 정상/guard deadline/post-transfer deadline/IO 실패4개. 실패 뒤 displayed/resident commit을 공개하지 않고 재호출도 전송하지 않았다.

독립 ACK checker는507 보드의 `nes_sink_spi165.sv`에 그대로 남는다. actual48965816은 각 packet identity·token·순차 read·CRC/coverage·DMA·VBlank·최종 ACK를 실행했다. menu/SD/실제 입력 종료 하드웨어는 이번 시험 범위 밖이다. 런타임 STOP/base/menu 구현은 변경하지 않았다.

## 같은 시작 시각·ROM 위상의12개 연속 비교

기준은506/507의 `nes-raw506-joint11`, 후보는 `nes-overlap508-joint01`이다. 실제 linked M4 runtime/planner/serializer/native service/SysTick과 실제48965816을 연결하고 같은 입력905..916·시작3000000masterclocks·ROM phase0/stride48·CPI2·실기503 SPI 평균을 사용했다. ROM safe-slot 밀도·일부 peripheral은 모형이며 실제 NES/PSRAM RTL 전체 경합 실행은 아니다. 미래 ACK/원자적 DMA overshoot를 ARM 진행에 잘못 반영하지 않는 기존 교정을 유지했다.

| 항목 | 506/507 기준 | 508 후보 | 차이 |
|---|---:|---:|---:|
| 첫 표시 뒤11개 표시 간격 합계 | 1230.609ms | 1147.400ms | −83.209ms/6.76% |
| 두 초기 표시 뒤10개 간격 합계 | 981.019ms | 931.110ms | −49.909ms/5.09% |
| 전체 SPI | 145247B | 140055B | −5192B/3.57% |
| 실행 M4 명령 | 34236341 | 31939257 | −2297084 |
| SysTick 호출 | 146 | 138 | 일정 길이에 따라 감소 |

12개 최종 RGB가 byte 단위로 같고 VRAM DMA36144B/ROM read 배정3280회가 같다. bulk bank 최대2, queue4 제한을 유지했다. 첫905는0.019835ms 느리다.906·907·908·909·914·915에서 마지막 bulk보다 각각35/17/12/10/12/12개의 일반 packet을 먼저 공급했다. 첫 두 frame 이후 추가 개선은909·914·915에서 각각 VBlank 약1주기 단축으로 나타난다. 다른 frame에 누적된 절대 ACK 선행을 그 frame 자체의 개선으로 중복 계산하지 않는다.

이는12개 고정 capture의 조건부 비교다. 장시간 실기 FPS·capture 거부율·전체60Hz·모든 장면의 개선을 증명하지 않는다. 506의 이전 이득과508의 비율을 단순 합산하지 않는다.

## Flash·RAM·전체 보드 비용

| 항목 | 506/507 기준 | 508 후보 |
|---|---:|---:|
| firmware | 212852B | 212992B (+140B) |
| Flash 잔여 | 140B | **0B** |
| BSS | 18572B | 18576B (+4B) |
| runtime struct | 440B | 444B |
| sink struct | 32B | 36B |
| plan / window struct | 300B /40B | 동일 |
| 관측 ARM SP 최저 | 0x2000f970 | 0x2000f860 |

sink의 plan 포인터4B가 실제 BSS 증가다. 별도 전역 객체가 없더라도 BSS0 증가라고 쓰지 않는다. 이전 runtime≤8B 예산에는 들지만 추가 static RAM0B 가정은 충족하지 않는다. 관측 호출 stack은272B 더 깊고, 이 fixture의 workspace 끝0x2000eec0과 SP 사이2464B를 유지했다. 전체 런타임 stack WCET/실기 RAM 여유의 증명은 아니다.

첫 ARM01은 링크는 성공했지만212996B로 제품 Flash 한도를4B 넘었다. 실제로 연속 호출되던 service 검사를 poll의 기존 검사로 합쳐 ARM02에서212992B가 됐다. 검사를 삭제하지 않았고 실패 산출물은 보존한다. 준비 metadata03은 ARM02와 patch bytes가 같으며 새 전역 객체0과 BSS+4를 구분한다.

FPGA/SNES는 변경하지 않았다.507 보드의 전체 source SHA를 다시 확인했다. 따라서 Lite15164LE/14172comb/8394FF/264816bits/51M9K,관련 setup+0.078ns/hold+0.139ns를 재사용하며 **새 Quartus 실행 결과로 표기하지 않는다**. 전체 reset/CDC/IO 승인은 여전히 미완료다.

## 선택·재현·후속 순서

508의 기능/조건부 일정 이득은 채택 가능한 개발 근거다. **Flash 여유0B와 실제 arbiter trace 미연결 때문에 새 실기 전달본으로 승격하지 않는다.** MMC502와 기존 ZIP은 불변이며 RESTORE 폴더는 새로 만들지 않는다.

1. 실제 ROM arbiter의 요청/허용/반환 trace를 같은 ARM·65816 일정에 연결해 일반 공급이 만든 이득과 ROM 허용 밀도 가정을 분리한다. 독립 검사·STOP·ACK/VBlank·유한 queue/bank를 유지한다.
2. 기존 진행·완료 실행의 중복을 함께 삭제해 Flash 여유를 회복한다. 후보의 runtime+4B/stack+272B를 포함해 비용을 비교한다. 작은 opcode·seed·위상만 바꾸는 반복은 하지 않는다.
3. 같은 조건의 초기/연속 구간을 다시 통과한 후보만 전체 source hash/보드 gate와 고유 파일명 전달 절차로 진행한다. 새 실기 로그 전에는 MMC502/10.59fps를 바꾸지 않는다.

선택 근거: `probes/nes-overlap508/candidate03`(ARM02와동일코드),`ARM02`,`arm-test02`,`analysis01`,Temp `nes-overlap508-joint01`. 최초 ARM01/arm-test01도 보존한다. Temp 원본은 `probes/nes-overlap508/archive01/evidence.zip`과 SHA inventory로 별도 보관한다. 상용 ROM/raw·firmware·license는 Git에 넣지 않는다.

재현 entry는 `tools/nes_overlap508.py`,기존 `tools/build_nes_mmc479_arm.ps1`,`tools/test_nes_overlap508_arm.py`,`tools/test_nes_raw506_joint.py`,`tools/analyze_nes_overlap508.py`다.506 ARM을 base로 준비/빌드하고, joint 실행은 위 동일 인자와489 소비기·506 plans·geometry230 fixture를 사용한다. 전용 Questa 추가 실행이나 새 라이선스는 필요하지 않았다.
