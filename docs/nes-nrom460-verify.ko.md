# NROM460: 실제 ARM readback·verified START 함수

418 firmware의 실제 ELF `nes_rom_verify`·`nes_rom_verified_start`·SPI framing 기계어를 Cortex-M4 Unicorn에서 실행했다. 각 함수가 `firmware.stm`의 해당 주소에 같은 바이트로 들어 있음을 확인했다. SPI 교환 및 PSRAM은 모델이며, 승인된 소스 callback은 ROM 파일과 zero-padding을 별도 주소 계산으로 제공한다. FPGA RTL과 ARM이 동시 실행되는 시험은 아니다.

정상 사례에서 실제 검증 코드는 393,216바이트 각각에 대해 CHECK READ·STATUS·ACK를 수행하고 FINISH 및 verified START를 실행했다. 모델 장치는 각 프레임의 명령·CRC8·주소·읽은 데이터와 ACK 내용을 확인했다. 393,216바이트 전체 비교 후에만 START가 발생했다. 256번째 데이터 변조, 64번째 주소 태그 오류, 33번째 소스 실패는 각각 오류로 종료하고 실제 ARM 코드의 STOP 후 상태 확인을 통과했다. 이 오류 주입은 START 전에 발생했다.

첫 arm01은 테스트 드라이버가 `nes_verify_report`의 enum을 4바이트로 잘못 해석해 결과 검사에서 중단했다. ELF DWARF로 실제 enum 1B와 `compared/error/stop_ok` 위치 0/4/5를 확인한 뒤 드라이버를 수정했다. `arm02`부터 통과했고, 독립 소스 주소 계산과 정확한 STM 주소의 코드 일치를 추가한 최종 arm04를 선택했다. `analysis/nrom460-verify.json`, `probes/nes-nrom460`에 범위와 결과를 보존한다.

실제 주변장치 GPIO, FPGA·PSRAM 핀, SD FatFS, IRQ, MCU 속도와 실기에서의 재구성·menu 복구는 모델 밖이다. Unicorn host 실행 시간을 MCU 처리 시간이나 60fps 수치로 사용하지 않는다. 457 raw reset·미제약 IO도 그대로 남는다.
