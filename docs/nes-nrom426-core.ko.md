# NES426: 실제 NROM cart·NES core 및 SNES 버스 경계

`core04`는 407/419의 실제 227 보드 RTL·NES core와 NROM16 수평 cart, vendor RAM simulation model을 사용한다. 424 자체 화면 ROM의 PRG/CHR를 PSRAM 핀 모델에 미리 넣고 loader의 길이·READY·verified도 직접 설정한 뒤 실제 SPI START를 보냈다. NES core의 실제 pixel에서 배경 색 `0x21`을 확인하고, SNES 버스를 시험기가 구동해 65816 프로그램의 첫 byte `0x78`을 읽었다. 이어서 실제 SNES sink bus의 pad register에 A를 전송하자 `nes_game_pad150`·NES core·PPU를 거친 색 `0x16`이 나타났다. 총 159,744개의 조건부 core pixel을 관찰했고 실제 SPI STOP 뒤 core reset을 확인했다. errors 0이다.

컴파일 로그는 0 warnings지만 최적화·시뮬레이션에는 기존 포트 폭/미연결, vendor RAM 동작, 시작시 VHDL metavalue 등 **84 warnings**가 있다. 이를 숨기거나 실기 signoff에 사용하지 않는다. ROM을 미리 설정했으므로 411 전체 loader와 같은 실행이 아니고, SNES 버스는 시험기가 수동 구동했다. 실제 65816 CPU의 소비·DMA·최종 ACK, 실제 controller, ARM·IRQ·ROM 경쟁과 물리 화면은 미검증이다. PLL·PSRAM도 기능 모델이며 전기·STA 승인이 아니다.

`core01`은 vendor RAM/CIRAM simulation 의존성 누락으로 실패했다. `core02`는 같은 PPU dot이 여러 clock 동안 유지되는 것을 frame으로 잘못 세어 fixture가 실패했다. 변화 edge를 세도록 고친 `core03`은 NES core pixel/STOP만, 최종 `core04`는 SNES 프로그램 읽기·pad·색 변경까지 통과했다. 실패 로그와 선택 증거는 `probes/nes-nrom426`에 보존한다.

다음은 실제 227 ARM native session과 실제 65816 CPU/출력 receipt·최종 ACK를 이 NROM source에 연결하고 base/menu 복구를 같은 실행 또는 제한 실기에서 확인하는 것이다. 이전 227의 같은 65816 프로그램 시험은 다른 source packet으로 실행됐으므로 이를 424 NROM 화면의 end-to-end PASS로 합치지 않는다. 419 raw timing 및 421 reset/I/O 한계는 그대로다.
