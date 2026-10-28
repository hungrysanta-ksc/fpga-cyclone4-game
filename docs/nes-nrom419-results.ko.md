# NES419: 전체 loader 공동 실행과 대표 observer 조건

411 `full01`은 실제 227 FatFS/loader host C와 407 FPGA SPI 및 227 boot/loader/physical RTL, PSRAM 기능 모델을 연결해 393,216바이트 전송과 독립 readback, RTL verified START·STOP을 통과했다. 로그는 `probes/nes-nrom411/full01`에 보존한다. 실제 ARM 명령, observer/native 표시, base 프로그래밍·IRQ는 모델이다. 실기 복구·프레임 또는 418 메뉴 package의 완성 증거는 아니다.

대표 415 `observer01`은 실제 227 loader·programmer·run136 host C, 실제 boot/observer/screen RTL 및 기능 PSRAM을 연결하고 2.625MHz, 시작 위상 0ns에서 observer 초기 식별과 256B 전송을 수행했다. 의도적으로 전송을 중단해 fail-closed를 확인했다. Questa 0 errors/0 warnings. 설정 핀·native session·SNES bus는 모델이고 START 이후 screen·STOP·base는 실행하지 않았다. 단일 위상은 전체 위상·CDC/STA 증명이 아니다. 417의 5위상은 실패 또는 실기 불안정 시에만 진단한다.

418 메뉴 firmware와 위 FPGA 후보는 아직 paired 제품이 아니며 65816 전체 표시·의미 있는 입력/화면 ROM·실제 base/menu 복구를 연결해야 한다. 동일 FPGA 후보의 Lite FIT/STA는 별도 실행 중이거나 별도 결과로 기록한다. 실제 ARM·IRQ·ROM 전체 시간과 MMC4/5 비용은 측정하지 않았다.
