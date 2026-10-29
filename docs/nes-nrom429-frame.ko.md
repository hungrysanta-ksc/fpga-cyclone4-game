# NROM 실제 geometry 전체와 227 planner

428의 자체 ROM을 227 board/NES core RTL과 시드된 PSRAM·loader 검증 상태에 연결했다. 정상 프레임 generation 4의 geometry를 25개 SPI 블록으로 읽고 각 CRC16과 D2 token 완료를 확인했다. 마지막 END 이후 D3 accept는 시험기가 발행했고 COMMIT 블록을 받았다. 독립 227 수신 C는 기록된 블록 1,404개 레코드를 검증해 COMMITTED 상태에 도달했다. D3 status 응답은 host 재생에서 모델이다. 65816 표시 ACK와 이 COMMIT은 다르다.

같은 수신 객체를 byte-identical 227 planner·resident와 팔레트에 전달했다. 출력은 28그룹·BG 슬롯 2개·OBJ 0개·HDMA 11바이트였으며, ROM tile 1의 패턴과 계획의 tag/행, map 슬롯 1의 924개 위치를 확인했다. FPGA 타일 생성, sink transport, 실제 ARM/IRQ 시간과 실제 65816 DMA는 이 시험에 포함되지 않는다.

ROM SHA-256 `61cc6ae495fb34dd6aa28497db6f584fa308063a79ba9412bde50c0c9419fd2c`, 블록 SHA-256 `3cf10a8d97a636f46e55bb892ba973b860070971feea5044ff418ec3fb49cadd`, map SHA-256 `e825b114005f53ab1f06d08183403e4bc769301fc875587eb74a155e9908cdc6`. raw 결과는 probes/nes-nrom429/core01·receiver01 및 nes-nrom430/planner02. Questa Starter 단일 seat 순차 실행, 0 errors/84 기존 경고. 0x0A 표시 제약과 FIT/STA 제한은 유지된다. 다음은 이 실제 계획을 타일 생성과 227 sink/65816 소비·최종 ACK에 결합하는 것이다.
