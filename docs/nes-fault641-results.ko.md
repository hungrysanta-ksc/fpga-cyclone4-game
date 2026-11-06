# MMC639 세대 32 FINISH와 별도 부팅 시간 초과

**1차 실기는 세대 31까지 20화면을 표시했고, 세대 32의 E9 두 묶음 수락 뒤 FPGA fault로 중단됐다.** FINISH는 오류를 관측한 지점이다. 실제 보드 소스에서 원인이 다른 세 입력이 CRC를 포함해 같은 20 B로 귀결됐다. 세 경우 사이의 발생 가능성은 이 시험으로 순위를 매길 수 없다. [실기 로그 판정](../analysis/hardware640-mmc639.json) · [641 검증 기록](../analysis/fault641-verification.json)

| 대조 | 처음 거부한 회로 | 관측 결과 |
|---|---|---|
| 정상 | 세대 32 blank+BG, 이어서 같은 세대 END | 두 E9 수락, 32 B chunk 생성·읽기·토큰 소비, EA로 lease 반환 |
| END 배치의 CRC16만 변경, 바깥 CRC8은 다시 계산 | host의 `nes_plan_batch206.hf` | E9 수락 2, 35.712 ns 뒤 상위 host 취소 |
| CRC가 맞는 세대 31 END, 실제 lease는 32 | NES의 `nes_plan_batch206.nf` | E9 수락 2, 33.675 ns 뒤 상위 host 취소 |
| 올바른 두 E9 뒤 토큰 4바이트 준비 전 $6050에 A5 쓰기 | host의 `nes_bulk_control194.command_error` | E9 수락 2, 35.712 ns 뒤 상위 host 취소 |

세 거부 모두 `00d7048000020000000000000000000000000057`을 반환했다. E9 수락 수는 SPI 프레이밍 수락 시점에 증가한다. 이후 배치 검사나 소비가 실패하면 상위 취소가 bulk와 배치를 초기화하고 E8의 fault가 유지된다. MMC639 ARM ELF는 정상 예제의 두 E9를 실제 발행했다. 별도로 보드에서 얻은 fault E8을 같은 ELF의 FINISH 경로에 입력하자 phase 2·reason 4·빈 버퍼·수락 2를 보존하고 EA 발행을 차단했다. 시뮬레이션의 ns 값은 각 자극에서의 전파 시간이다.

실기에는 세대 32의 E9 payload, 취소 전 로컬 fault, 개별 SNES 쓰기가 기록되지 않았다. 재현에서는 세대·수락 횟수·ARM queue 카운터 216/214·응답을 맞췄다. 타일은 정상 예제이고 ROM 응답·SNES 읽기/쓰기는 시험 자극이다. 앞선 20화면, 실제 ROM 경쟁 및 PPU 타이밍은 이 재현의 범위 밖이다. 252번 선 DMA를 원인으로 지정할 근거도 없다.

**2차는 별도의 부팅 실패다.** 44,203회/500틱(5초), stage 0, native 전송 0회였다. MMC551 실패의 44,425회/500틱은 별도 표본이다. 두 표본 모두 SPI73의 누적 flags가 0x48에서 0x58로 변했고, reset 비활성·FPGA DONE·MCU_RDY는 진입/종료 조회에서 같았다. 하위 3비트는 자격 조건을 만족한 $FFFC·$FFFD·ROM 읽기를 나타내며 모두 0이다. 상위 핀 표본을 ARM이 누적하므로 0x58만으로 reset vector 실행이나 그 시각을 알 수 없다. 실제 관측 RTL에서 vector 읽기를 전혀 주지 않은 경우와 active 전에 두 읽기를 끝낸 경우 모두 이 서명이 나왔다. active 뒤 두 읽기를 준 대조군은 0x5F, 이어진 $7000 쓰기는 stage 3을 기록했다. 44,203개의 실기 SPI 거래 전체를 재생한 것은 아니다. [MMC551 독립 기록](../analysis/hardware552-mmc551.json)

**다음 실기 준비 순서**

1. Host와 NES 각각 최초 검출 시점에 원인 비트를 남긴다. SPI 자체 오류·상위 transport·배치 CRC/세대·bulk 소비/명령·lease/tile/core를 구분하고, 나중에 들어온 취소 에코가 덮어쓰지 않게 한다. 동시 원인은 함께 보존한다. 정상 E8 포맷과 예약 바이트 18을 유지하고, fault 때 유효하지 않은 descriptor 영역을 활용하면 기존 ARM의 20 B 원본 로그로 판독할 수 있다.
2. 부팅은 reset 해제 전부터 첫 vector 읽기와 관측기 active 진입, $7000 첫 쓰기를 구분한다. 2차와 MMC551은 각각 기록하며, 공통 원인은 독립적으로 입증될 때 연결한다.
3. 641의 세 자극·정상 소비·STOP 후 재시작과 기존 메뉴/base 복구를 통과한 뒤 보드 FIT·STA를 MMC639와 대조한다. MMC639는 57 LE 여유, M9K 56/56이므로 계측 비용도 포함한다. 이번 단계에서는 설치본을 발행하지 않았다. 두 실기 모두 기존 STOP·base 복구·MENU_PREPARED와 사용자 메뉴 복귀를 확인했다.

재현 도구는 [보드 RTL](../tools/check_nes_fault641.py)과 [MMC639 ARM](../tools/check_nes_fault641_arm.py)이다. 보드 도구는 선정된 SOF와 각 RTL의 SHA256을 검사하고 FLOAT 한 좌석으로 두 시험을 순차 실행한다. ARM 도구에는 동일 패키지의 src 경로와 보드 시험의 `fault641_tb.log`를 전달한다.
