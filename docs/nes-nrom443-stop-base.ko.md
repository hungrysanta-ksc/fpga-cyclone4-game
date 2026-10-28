# 실제 표시 뒤 board STOP과 보존된 base 파일

440 전체 공동 실행에 실제 board SPI STOP 명령을 추가했다. 실행 중 NES 코어 → 227 RUN host C → 실제 FPGA queue/tile → 65816 에뮬레이터의 33개 packet ACK·VBlank 표시 및 EA lease 반환 뒤 STOP을 전송했다. 보드 RTL의 core reset, RUN 비활성, lease 해제 및 SNES bus 비활성을 확인했다. 화면은 체크무늬 46,592픽셀과 일치했고 Questa 0 errors, 기존 초기화/포트 경고 84개다. loader 완료·PSRAM은 시드, RUN은 host C, 실행기 간 시간은 RPC 모델이다. STOP은 시험기가 보낸다. raw evidence probes/nes-nrom443/stop01.

보존된 사용자의 044 base `fpga_base.bi3` SHA-256 `eff3f675c93a0209caf4987d72e0f277492c3dddc2b4c2aff334a667b4dbfbc7`를 실제 227 FPGA programmer와 FatFS host C로 합성 FAT16에서 읽었다. 모델 GPIO 핀의 214,981바이트는 이전 075 독립 복원본 SHA-256 `9c35d1b8bd081dd2c3b22763b68ead2b8340f4062b2a0792f8d8c76b7071e547`와 완전히 일치했다. 168,440바이트 원본과 사용자 SD는 수정하지 않았다. raw evidence probes/nes-nrom444/base01.

두 결과는 실제 FPGA 재설정·DONE·base token·menu 표시 또는 현재 SD 내용이 보존본과 같은지 검증하지 않는다. 443 STOP, base programming의 host 모델 및 이전 414 복구 orchestration을 하나의 실기 성공으로 합산하지 않는다. 실제 227 ARM 기계어/IRQ·전원·배선·reset/IO STA, 장시간 capture와 60fps도 남는다.
