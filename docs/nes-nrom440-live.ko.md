# 실행 중인 NES board → 227 RUN → FPGA queue/tile → 65816

428 자체 NROM을 227 전체 board/NES core RTL에서 실행했다. PSRAM 내용, loader 완료·verified 및 content epoch는 테스트가 시드한 상태이며, 실제 SPI START 이후의 NES core·geometry capture·native D0/D1/D2/D3·plan SPI·E0/E1 sink queue·타일·lease는 board RTL이다. 기존 227 RUN C는 host에서 실행했고, 동일 227 65816 프로그램은 Mesen에서 실행했다. FPGA와 65816은 검사된 transaction RPC로 연결돼 공통 물리 시간을 갖지 않는다.

NES가 실행 중 생성한 D1 25블록 5,764B를 실제 SPI로 받아 각각 CRC16을 독립 재검사했다. 실제 수신 바이트 SHA-256은 `eaae16835aece4b0785a0a759e8522bddc6f3f62db86ed11cc89dc874f2b0136`이며 별도 429 캡처와 같다. RUN은 1,483 step·SPI 1,804회, FPGA 큐는 33 패킷 ACK를 수행했다. 65816이 실제 RTL 타일 32B를 소비하고 VRAM 4,128B를 기록해 VBlank에서 표시·최종 ACK한 뒤 RUN이 EA로 lease를 반환했다. 체크무늬 46,592픽셀 SHA는 `f400720c8e089754ce7a68aba00a24a4556b1c85cd2c11669b81c7a3b13bf0f9`다. Questa 0 errors, 기존 초기화/포트 경고 84개를 보존했다.

01·02는 동기 RPC 연결기의 중복 ACK, 03·04는 연결기 재진입/대기 교착으로 실패하거나 의도 중단했다. 442의 지연 ACK 시험에서 검증한 비동기 연결기를 적용한 05만 선택한다. 이 성공은 실제 loader CRC·전체 384KiB 적재, ARM 기계어/IRQ, 공통 일정, STOP 후 base/menu 복구, 실기 또는 60fps를 증명하지 않는다. 입력 ROM은 지원 mask 0x1E 한정이며 0x0A 제약은 남는다. 원본 로그·전송 증거는 probes/nes-nrom440/live01..05, 독립 검사는 analysis/nrom440-live.json. 다음은 표시 완료 뒤 실제 board STOP·base 복구 및 장시간 캡처/입력, timing/IO 조건이다.
