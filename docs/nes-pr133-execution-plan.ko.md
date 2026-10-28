# PR133: 실기 진입과 60fps 작업 순서

## 방향 정정

긴 단위 시뮬레이션과 미완성 mapper 비용 예측을 반복해 실제 보드 진입을 늦추지 않는다. 단일 Questa Starter FLOAT seat로 필요한 시험을 **순차 실행**한다. 추가 라이선스 구매나 대기 중 중복 시뮬레이션을 요구하지 않는다. 411의 전체 쓰기·readback·START/STOP은 통과했으며 RUN·base는 모델이다. 411 결과만으로 새 NROM 실기를 승인하지 않는다.

observer 2.625MHz는 실제 firmware 설정과 이전 250kHz 명시 사이 차이가 있어 대표 위상에서 ID·MISO 중재·STOP 관련 기능 확인은 유지한다. 417의 5개 위상 전체를 초기 실기의 선행 조건으로 요구하지 않는다. 우선 대표 위상 1개와 합성된 동일 보드의 Lite timing/CDC 경계를 확인하고, 실기에서 반복 부팅·통신·STOP·복귀를 관찰한다. 실기 성공은 해당 보드·조건에서의 관찰이며 모든 위상·CDC/STA signoff는 아니다. 실패나 간헐 오류가 있으면 추가 위상·오류 주입을 수행한다. screen/표시·base를 초기 observer prefix PASS로 추정하지 않는다.

## 현황과 순서

| 순서 | 목표와 완료 조건 | 상태 |
|---|---|---|
| 0 | 기존 227 및 GBC164·SRAM 복구 자료 보존. 411 결과·범위 기록, 단일 seat 반환 | **완료**: 384KiB 쓰기·readback·RTL START/STOP 통과; 실제 run136·base는 모델 |
| 1 | 한정 NROM16 수평 profile의 실제 menu 경로·ID 78·ARM/FPGA/65816 짝과 재현 가능한 자체 테스트 ROM을 결합. header/CRC 실패는 START 차단 | **진행 중**: ARM·FPGA 진단 짝, 65816 ROM atom, 실행 중인 227 board/NES core RTL을 227 RUN C·FPGA queue/tile RTL·65816 에뮬레이터의 표시 ACK·lease retire·board STOP에 공동 연결; loader·PSRAM은 시드이고 실제 ARM 기계어·실기·복구는 미완료 |
| 2 | 같은 source로 Lite 전체 FIT/STA·핀/클록/CDC 확인, CRC·STOP·독립 검증 및 base token/menu 복원 절차 확인. observer 대표 조건을 단일 seat에서 순차 시험 | **진행 중**: Lite FIT 14,751LE, 관련 clock·observer 대표 조건 및 표시 후 RTL STOP 통과, 보존 base 파일의 실제 227 programmer 출력 일치; raw reset/CDC·미제약 IO와 실제 재설정·복구는 미해결 |
| 3 | 사용자의 제한 실기: paired build에서 부팅·화면·입력·해당 음성, STOP·메뉴 복귀·재시작·복원 기록. 실패 시 복원 자료 사용 | **대기**: 1·2 완료 후에만 실기 가능. 새 NROM 실기 성공 아님 |
| 4 | 같은 workload에서 capture/표시 ACK·누락·VBlank·ARM/SPI/IRQ/ROM 시간을 계측. 60fps의 16.667ms와 지속 프레임을 확인하고 병목을 정한다 | **미달/미측정**: 227 실기 465 ACK/60.06s, 402 fixture 최대 warm 34.048ms이며 서로 다른 경계. 실제 새 후보 시간 없음 |
| 5 | A 공동 실행기와 B ARM DMA job 중 **하나의 완결 경로**를 같은 일정·전체 Lite 비용으로 대조, 시간과 FIT 양쪽에 맞지 않으면 역할/장치 범위를 재결정 | **미완료**: 402 전체 MAP 20,199LE/16,508 조합, 914/915 VBlank 미달; B 동일 경계 부재 |
| 6 | MMC4 mapper10 live latch, MMC5 mapper5 고위 tag·ExRAM/split·IRQ/audio 지원 범위를 정하고 실제 PPU/ROM 경쟁과 보드 전체 비용을 각각 측정 | **미완료**: MMC4 실 latch 미연결; MMC5 13bit tag 및 128 split 예외 한도 반례. 비용 수치는 없음 |

1–3은 제한 NROM 실기 smoke를 위한 우선 경로다. 4–6은 60fps 및 mapper 확장 관문이며 순차적으로 진행한다. 예외적으로 실기 직전 새 변경에 연결된 기본 STOP·검증이나 Lite FIT/STA가 실패하면 이를 먼저 고친다. 측정하지 않은 ARM 시간, 새 하드웨어 동작이나 MMC4/5 비용은 null로 둔다. 411과 새 후보의 실행 경계 차이를 유지한다.

## 다음 작업 하나

**1의 연속 실제 NES 캡처·표시와 2의 base 재설정·복구 경계**를 진행한다. 440/443의 한 프레임 표시·STOP과 445의 실제 두 프레임 표시·STOP과 447의 실제 run136 verified START·표시 상태·STOP 및 observer 정지는 통과했다. 다음 캡처의 실제 마감·장시간 무누락은 미검증이다. 실행기 RPC는 실기 시간 측정이 아니다. 기존 227·GBC 복원물을 덮어쓰지 않고 파일·프로파일 identity를 유지하며, 2에서 확인된 raw reset/CDC·미제약 IO를 별도로 다룬다. 417 phase sweep은 대표 시험 실패 또는 실기 통신 불안정 시 진단용으로만 수행한다.
