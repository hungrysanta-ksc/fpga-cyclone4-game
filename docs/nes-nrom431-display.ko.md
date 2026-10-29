# NROM geometry에서 227 sink와 65816 표시까지

429에서 실제 board/NES core RTL이 생성한 25개 geometry 블록을 227 receiver·resident planner·sink C에 재생해 34개 화면 패킷을 만들고, 기존 227 65816 프로그램을 Mesen SNES에서 실행했다. 패킷과 타일 aperture는 파일 기반 모델이며 타일 bytes는 같은 자체 ROM의 CHR에서 재구성했다. D3 응답, loader/PSRAM 시드와 이종 시스템 간 시간 또한 모델이다.

65816이 DMA를 실행하고 토큰을 확인해 타일 2개를 소비했으며 VRAM 4,128B와 최종 표시 ACK 1회를 확인했다. 표시 후 224×208 체크무늬 영역의 46,592개 픽셀이 기대한 흑/비흑 교대 패턴과 일치했다. 최종 ACK는 실제 65816 코드가 VBlank에서 표시를 연 뒤 생성했고 기존 Lua 검사가 버스의 token·순차 읽기와 staging·VBlank 조건을 확인했다. 실제 컨트롤러, 라이브 FPGA/ARM 타이밍, 실기 및 base 복구는 검증하지 않았다. cold 프레임의 단일 VBlank 완료는 주장하지 않는다.

fixture SHA `61cc6ae495fb34dd6aa28497db6f584fa308063a79ba9412bde50c0c9419fd2c`, geometry SHA `3cf10a8d97a636f46e55bb892ba973b860070971feea5044ff418ec3fb49cadd`, 화면 RGB SHA `f400720c8e089754ce7a68aba00a24a4556b1c85cd2c11669b81c7a3b13bf0f9`. raw 로그·화면은 probes/nes-nrom431/snes03. 427의 mask 제약과 419 FIT/STA의 미해결 항목은 그대로다. 다음은 모델 타일·패킷 버스를 실제 FPGA 및 실제 ARM session과 결합하고 STOP·base 복구를 확인하는 것이다.
