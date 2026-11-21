# MMC893 · 일반 실행의 첫 화면과 ARM 스택

MMC892의 BOOT 실기는 stage 3에서 STOP·메뉴 복귀를 마쳤다. 일반 실행 실기는 START 직전의 DISPLAY_NEXT 이후 기록이 없고 검은 화면에서 본체 리셋으로 복귀하지 못했다. 두 실행의 로그는 [MMC892 실기 기록](nes-reset892-results.ko.md)에 있다.

## 재현 결과

모험도 4 오프닝의 첫 cold 입력(재생 세대 905)을 사용했다. 모델이 공급한 입력·타일과 MMC892의 실제 ARM ELF, Mesen에서 실행한 기존 65816으로 첫 최종 ACK, EA, E8 재준비까지 SPI 1,008건을 채취했다. 실기 ROM CRC `A58FE808`을 세션 identity로 썼다. 각 ARM의 메뉴 호출 깊이에서 run136을 시작해 실제 프레임 함수·SPI DMA 드라이버에서 모든 송신 바이트가 일치하는지 검사했다. GPIO·타이머·DMA 완료 레지스터와 부팅 응답은 모델로 공급했다. 프레임이 끝난 다음 step에서 시험용으로 시간 제한을 만료시켰다.

| 첫 화면 측정값 | MMC892 | MMC893 |
|---|---:|---:|
| 게임 실행 중 남아 있는 로더 스택 | 960B | 56B |
| SPI DMA 드라이버를 포함한 최저 SP와 정적 RAM 끝 사이 거리 | −604B | +300B |
| 그 위치에서 104B 예외 프레임 예약 후 SysTick 핸들러를 실행한 경우 | −740B | +164B |
| 첫 화면 최종 ACK·EA 뒤 E8 확인·STOP | 통과 | 통과 |
| 첫 D1 CRC 손상 시 표시 없이 STOP | 통과 | 통과 |

MMC892에서는 65번째 SPI 거래 뒤 E1 출력 패킷을 조립하는 `send`에서 PC `0x08021B34`가 `0x2000794C`에 실제로 1B를 썼다. 정적 RAM 끝은 `0x20007954`이고 이 위치는 C 라이브러리의 `__sf` 영역 안이다. BOOT 진단은 이 함수를 호출하지 않는다. 모델에서 RAM 침범이 있어도 첫 화면 ACK까지 진행했으므로, 실기 암전의 정확한 정지 명령은 여전히 미확정이다.

## 수정과 적용 범위

파일 객체·256B 버퍼·원본 대조 문맥을 적재 전용 함수에 두고 검증이 끝나면 반환한다. 일반 실행과 부팅 진단은 기존 RESET·START·CRC 검사와 STOP 순서를 사용한다. SRAM 고정 영역 끝은 같다. Flash 예산은 같은 형식의 두 SD 로그 쓰기를 공통 함수로 모으고 이미 출력되는 RESET 보류 메시지의 중복 문구를 제거해 맞췄다. 최종 이미지는 212,988B로 4B가 남는다.

FPGA와 65816은 MMC892 설치본의 바이트를 재사용한다. 164B는 시험한 첫 화면과 SysTick 조건에서 관측한 여유다. 장면별 최대 스택이나 실기 FPS는 아직 측정하지 않았다. 다음 실기는 [MMC893 일반 실행](nes-mmc893-trial.ko.md)으로 첫 표시와 60초 종료를 확인한다.

## 재현

1. `prepare_nes_stack893.py probes/nes-first893/patchC`를 실행하고 기존 `build_nes_mmc479_arm.ps1`로 MMC892 link를 바탕으로 linkC에 빌드한다.
2. `capture_nes_first893.py TEMP probes/nes-first893/adventure893.json`으로 MMC892 송수신을 기록한다. `check_nes_first893.py TRACE OUT SRC`를 892·893에 각각 실행해 final892.json·final893.json을 만든다.
3. MMC893 최종 링크로 `package_nes_trial855.loader`, `check_nes_menu533.py`와 `check_nes_transfer512_recovery.py`를 실행한다. 후자는 base `none/program/done/busy/token`과 `--game` 원본 ROM의 전체 적재를 검사한다.
4. `package_nes_stack893.py`가 두 시험 결과, 실제 호출 SP, 원본·손상 ROM 판정, 진단 파일 선택, 기존 보드 해시와 ZIP 내용을 확인한다. [최종 링크와 실험 수치](../analysis/trial893-package.json)
