# NROM463: 실제 ARM 메뉴 전체 경로와 장치 모델

418 ELF의 메뉴 로더, 헤더·배치·CRC, SPI 프레임, readback·verified START 함수의 기계어가 같은 firmware.stm에 포함된 것을 확인하고 Cortex-M4 기계어를 실행했다. 428 자체 NROM16 fixture를 FatFS 모델에서 읽어 독립적으로 구성한 393,216바이트와 적재 내용을 비교했다.

한 번의 실행에서 실제 ARM은 393,216바이트를 전송하고 각각 readback·비교·ACK한 후 START, 모델 표시 세션, STOP, base 설정과 복구 분기를 수행했다. 종료 보고서는 전송 및 비교 각 393,216바이트, 검증·STOP·base 복구 성공을 나타냈다. 설정 경로는 `/sd2snes/fpga_nrom16.bi3`, `/sd2snes/fpga_base.bi3` 순서다. 호출 수와 해시는 `analysis/nrom463-menu.json`, 원본 결과와 로그는 `probes/nes-nrom463/arm463-03`에 보존한다.

FatFS, FPGA SPI·PSRAM, 프로그래머, 설정 완료, base token, GPIO와 표시 세션은 모델이다. 따라서 이는 실제 SD·FPGA·65816의 단일 실행, 물리적 복구, IRQ 경합 또는 실기 승인이나 60fps 측정이 아니다. 모델 표시가 실제 화면을 확인한 것은 아니다. 실제 ARM 검증과 FPGA의 오류·STOP 결합은 461의 별도 16바이트 시험 범위에서 확인했다. 457의 raw reset·CDC와 미제약 IO, 실제 설정과 복구는 여전히 실기 진입 전에 확인해야 한다.
