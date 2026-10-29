# NES419: 전체 loader 공동 실행과 대표 observer 조건

## Lite 배치·타이밍 결과: 실기 진입 보류

407 전체 보드 MAP 입력을 그대로 사용한 Quartus Lite `fit01`은 EP4CE15F17C8에서 **14,751/15,408 LE**로 배치·배선에 성공했다. 그러나 STA 프로세스의 정상 종료는 타이밍 통과가 아니다. slow 85C setup 최악 **−6.970ns**, recovery 최악 **−8.824ns**이며 setup/hold 일부는 미제약이다. `board.sdc`의 `loader|state*` 집합이 일치하지 않아 max-delay 하나도 무시됐다. 따라서 실기용 타이밍 승인과 새 package는 보류한다.

최악 setup은 NES 클록의 `core_release|release_reset[1]`에서 host PLL 클록의 `native_prepared|held`로 이어진 경로다. 다른 위반에는 memory→NES 클록의 source epoch gray→epoch_meta 경로가 있다. 비동기 reset/CDC의 실제 소유권과 기존 224의 확인된 경로·제약을 먼저 대조한다. 이 숫자를 무조건 실제 동기 데이터 경로 실패라고 단정하거나, false path를 추가해 임의로 숨기지 않는다. 원본 FIT/STA summary와 전체 STA report는 `probes/nes-nrom419/fit01`에 보존했다. 후속 정확한 경로·제약 감사와 검증된 회로/제약 수정이 필요하다.

411 `full01`은 실제 227 FatFS/loader host C와 407 FPGA SPI 및 227 boot/loader/physical RTL, PSRAM 기능 모델을 연결해 393,216바이트 전송과 독립 readback, RTL verified START·STOP을 통과했다. 로그는 `probes/nes-nrom411/full01`에 보존한다. 실제 ARM 명령, observer/native 표시, base 프로그래밍·IRQ는 모델이다. 실기 복구·프레임 또는 418 메뉴 package의 완성 증거는 아니다.

대표 415 `observer01`은 실제 227 loader·programmer·run136 host C, 실제 boot/observer/screen RTL 및 기능 PSRAM을 연결하고 2.625MHz, 시작 위상 0ns에서 observer 초기 식별과 256B 전송을 수행했다. 의도적으로 전송을 중단해 fail-closed를 확인했다. Questa 0 errors/0 warnings. 설정 핀·native session·SNES bus는 모델이고 START 이후 screen·STOP·base는 실행하지 않았다. 단일 위상은 전체 위상·CDC/STA 증명이 아니다. 417의 5위상은 실패 또는 실기 불안정 시에만 진단한다.

418 메뉴 firmware와 위 FPGA 후보는 아직 paired 제품이 아니며 65816 전체 표시·의미 있는 입력/화면 ROM·실제 base/menu 복구를 연결해야 한다. 동일 FPGA 후보의 Lite FIT/STA는 별도 실행 중이거나 별도 결과로 기록한다. 실제 ARM·IRQ·ROM 전체 시간과 MMC4/5 비용은 측정하지 않았다.
