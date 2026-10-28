# 실제 227 RUN·FPGA 출력 큐·타일·65816 공동 실행

435의 E0/E1 queue 모델을 419 보드의 실제 sink_bridge165·sink_spi165·sink_bus165 RTL로 교체했다. 실제 227 RUN C의 E0/E1 전송과 65816 packet/ACK bus를 같은 RTL에 연결하고, E9 plan/direct206 타일·lease RTL과 함께 단일 Questa + Mesen transaction RPC로 실행했다. SNES packet 바이트와 control 상태는 RTL 버스에서 읽어 확인하고, 12B ACK와 publish를 RTL 버스에 실제로 썼다. Mesen callback은 검사한 packet을 캐시해 CPU에 제공한다.

기록된 429 geometry 25블록으로 RUN이 26 step·SPI 191회, 화면 패킷 33개를 처리했다. 65816이 RTL tile 32B를 소비하고 VRAM 4,128B·VBlank 최종 표시 ACK를 실행한 뒤 227 RUN이 EA로 lease를 반환했다. 46,592 체크무늬 픽셀 확인, RTL bus read 4,985·write 434, Questa 0 errors/0 warnings. baseline 435와 같은 화면 SHA `f400720c8e089754ce7a68aba00a24a4556b1c85cd2c11669b81c7a3b13bf0f9`.

입력 geometry는 별도 실제 RTL 실행의 기록이며 ROM·loader·capture lease와 시뮬레이터 간 시간은 모델이고 C는 host에서 실행했다. 실제 NES core·ARM/IRQ·FPGA 전체 및 65816의 공통 일정, STOP/base 복구, 실기와 60fps를 증명하지 않는다. raw 결과 probes/nes-nrom437/queue01. 다음은 실제 queue를 포함한 중간 STOP과 loader/전체 board 결합이다.
