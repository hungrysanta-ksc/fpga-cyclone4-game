# H1 STM32 연결035 계약

SPDX-License-Identifier: MIT.

035는 034 H1 FPGA 프로토콜과 SNES 프로그램에 연결할 STM32 펌웨어다. NES 게임 코어는 포함하지 않는다.
[결과](../analysis/H1-FIRMWARE-RESULT.ko.md), [034 보드 계약](nes-h1-board-contract.md).

## 진입과 복귀

전용 .nh1 파일은 진단 실행 표식이다. 파일 내용은 ROM으로 적재하지 않는다.
파생 메뉴의 일반 선택·최근 항목·즐겨찾기 세 경로는 stock load_rom()과 최근 항목 추가보다 먼저 H1을 처리한다.
자동 부팅에서 .nh1은 기존 NACK 경로로 돌아가 반복 진입을 막는다. .sfc/.egbc/.gb/.gbc 분기는 원본이다.

nes_h1_run()은 USB OTG FS IRQ의 기존 enable 상태를 저장하고 이 IRQ만 막는다.
upstream CDC_BulkIn()은 IRQ 문맥에서 usbint_handler_dat()을 호출해 SRAM/SPI에 접근할 수 있으므로,
단순히 H1 폴링 루프에서 USB 핸들러 호출을 생략하는 것으로는 충분하지 않다.
SysTick·SD 인터럽트는 유지한다. H1 중 USB 전송은 중단되며, USB 통신 연속성은 보장하지 않는다.

034의 nes_h1_session.c/h는 그대로 사용한다.
실제 SNES RESET을 assert한 상태에서 /sd2snes/fpga_nh1.bi3를 설정하고 DONE·file_res·설정 이미지명을 확인한다.
SPI F0=A5, F1=34, idle F2=2, 세대 증가 및 ARM 후 F2=3 확인이 끝나야 RESET을 해제한다.
ARM 후 1ms 대기한 뒤 물리 RESET과 F2 상태를 약 1ms 간격으로 확인한다.
물리 RESET 또는 상태 이상 시 RESET assert→STOP→SPI/GPIO 복원→기본 FPGA 재설정/토큰 확인 순서다.
성공 반환도 RESET을 잡고 있으므로 호출자의 원래 메뉴 적재·초기화 순서를 거친 뒤 해제한다.
기본 FPGA 복구 실패 시 USB IRQ도 막은 상태를 유지하고 호출자가 led_panic으로 정지한다.

GPIO 모드의 SPI 소유 기간에는 기존 저장 RAM·게임 reset handler·고속 SPI를 사용하지 않는다.
원본 fpga_pgm()의 하드웨어 설정 실패는 기존 LED panic에 머무를 수 있다.
타이머/주변장치 자체 고장까지 모든 stock 하위 함수가 반환한다고 주장하지 않는다.

## SPI 핀과 시간

MK3 STM32의 기존 PB3=SCK, PB4=MISO, PB5=MOSI, PA4=SS를 사용한다.
84MHz SPI1의 최대 분주 256은 328.125kHz이므로 034의 250kHz 상한보다 빠르다.
H1 동안에만 PB3/PB5를 GPIO 출력, PB4를 입력으로 전환한다.
SPI1 BSY 해제는 1us 간격 1,000회로 제한한다.
기존 CR1, 관련 MODER 비트 및 출력 latch만 저장·복원하며 AF·속도·pull 설정을 바꾸지 않는다.
GPIO 쓰기는 기존 atomic SET_BIT/CLEAR_BIT를 사용한다.

mode0, MSB first, low/high 각각 최소 2us, 바이트 사이 추가 2us,
SS setup/hold 및 트랜잭션 사이 최소 2us다.
호스트 핀 모델은 SCK 주기 최소 4us·비트 순서·byte gap·SS/RESET 조건을 검사했다.
실물 STM32 파형 계측은 아직 없으며 인터럽트 지연은 이 간격을 늘릴 수 있다.

## 재현

기존 prepare_firmware.py와 build_firmware.ps1은 C44 재현용으로 보존한다.
035 도구는 원본 overlay를 수정하지 않고 새 출력 폴더에서만 세 메뉴 파일을 패치한다.

1. python -B tools/prepare_nes_h1_firmware.py --upstream <pinned-sd2snes-checkout> --out <fresh-output>
2. tools/build_nes_h1_firmware.ps1 -SourceRoot <fresh-output> -ArmBin <GNU-Arm-bin> -HostGcc <host-gcc.exe> -Make <make.exe> -UnixBin <Git-usr-bin> -MiniImage <verified-fpga_mini.bi3>
3. python -B tools/test_nes_h1_firmware.py --gcc <host-gcc.exe> --out <fresh-test-output>
4. 보존된 이번 실행 증거 검사: python -B tools/verify_nes_h1_firmware.py

최종 build는 obj-h1-035와 firmware-h1-035.stm을 생성한다.
genhdr의 시간 기반 4-byte version ID를 포함하므로 매번 같은 SHA를 요구하지 않는다.
기존 C44 sealing 검사/기준 해시를 이 바이너리에 맞춰 바꾸지 않는다.
build 임시 드라이브 W:/V:는 시작 전 빈 상태를 확인하고 종료 시 해제한다.

## 남은 실기 관문

034 fit 데이터베이스 사본에서 quartus_sta -t <absolute tools/audit_nes_h1_io.tcl>로 외부 지연을 읽었다.
SDC/배치 변경 없이 Slow 1200mV 85C 한 모델의 최장 지연 목록만 추출했다.
38개 입력·11개 출력 미제약은 그대로이며 실제 SNES/CPLD/레벨시프터 요구와 turnaround를 대조해야 한다.
일괄 false-path나 임의 input/output delay로 미제약 숫자를 없애지 않는다.

이 펌웨어는 빌드·호스트 모델 통과 단계다. 실제 MCU 메뉴 실행, GBC 런타임 회귀, USB 복구 연속성은 미검증이다.
034 FPGA의 ASM/RBF/BI3와 백업·복원 가능한 SD 설치 묶음은 아직 만들지 않았다.
다음 후보에서 외부 IO/CDC와 전환 복구를 검토한 후 같은 소스의 실기 묶음을 만든다.
