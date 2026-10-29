# NROM459: 실제 418 ARM 코드의 제한 NROM 검사

418에서 링크한 Cortex-M4 ELF의 `nes_nrom406_header`, `nes_nrom406_layout`, `load_crc`, `nes_rom_spi_frame` 실제 기계어를 Unicorn에서 실행했다. 네 함수의 코드 바이트 각각이 같은 418 `firmware.stm`에 유일하게 존재함도 확인했다. 에뮬레이터의 특정 함수 호출 시험이며 전체 firmware 부팅은 아니다.

428 자체 NROM16 fixture에 대해 헤더를 승인하고 잘못된 magic·mapper·NES2·trainer·CHR RAM·PRG 개수·파일 길이·예약 필드 8종을 거부했다. 실제 ARM 배치 함수를 호출해 고정 384KiB의 393,216개 주소를 전부 독립 계산과 비교했다. 24,576바이트는 ROM에서, 368,640바이트는 0으로 채워지며 독립적으로 배열을 구성한 SHA-256 `e5e7118e0bd96621911b6beaf052ba9d10d2f8af351ee571984cb437ffc76ae9`와 일치했다. 파일 CRC32 `6ce6835a`는 독립 zlib와 일치했고 실제 SPI frame 함수의 120개 명령·주소·데이터 사례를 독립 CRC8 구현과 비교했다.

첫 실행은 테스트 드라이버가 Unicorn에 bytearray를 전달한 타입 오류로 중단됐고, 이를 수정한 재실행과 독립 전체 배열 검사를 추가한 최종 arm04가 통과했다. `analysis/nrom459-arm.json`에 각 기계어·ELF·STM·ROM 해시, `probes/nes-nrom459`에 결과를 보존한다.

이 시험은 함수의 실제 ARM 기계어를 실행하지만 FatFS·SPI 주변장치·IRQ·전체 loader나 FPGA RTL과의 한 실행은 아니다. 호스트 실행 시간은 MCU 사이클이나 frame 시간으로 사용하지 않는다. 물리 보드·base/menu 복구 및 지속 60fps는 여전히 미검증이다.
