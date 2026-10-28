# NROM geometry → 실제 plan RTL → 65816 표시·retire 공동 실행

429에서 실제 227 board/NES RTL이 생성한 전체 geometry 25블록을 기존 227 receiver·planner에 재생하고 실제 227 plan service/sink를 실행했다. 2.625MHz plan SPI는 227 direct206·plan decoder·tile source·bulk·lease RTL에 연결했다. 동시에 실제 227 65816 프로그램을 Mesen에서 실행해 RTL의 32바이트 descriptor·타일을 SNES 버스로 읽고 token 소비, DMA, VBlank 표시와 최종 ACK를 확인했다. 그 ACK가 돌아온 뒤 실제 plan service가 EA를 보내 lease retire를 완료했다. 33개 패킷 ACK, VRAM 4,128B, 표시 1회, 최종 체크무늬 46,592픽셀 확인; Questa 0 errors/0 warnings.

실행기들은 파일 기반 transaction RPC로 동기화된다. NES geometry는 429의 기록을 재생했고 ROM·loader·capture lease와 E0/E1 큐는 fixture이며 ARM C는 host에서 실행했다. 현재 실제 NES 코어·ARM CPU·FPGA 전체·65816이 하나의 공통 물리 시간으로 동작한 것은 아니다. 이 실행에서 STOP/base 복구 및 60fps를 증명하지 않는다. 433은 별도 수동 버스로 STOP을 확인했으며 이전 431 모델 타일의 결과와 pixel SHA가 같았다.

ROM `61cc6ae495fb34dd6aa28497db6f584fa308063a79ba9412bde50c0c9419fd2c`, geometry `3cf10a8d97a636f46e55bb892ba973b860070971feea5044ff418ec3fb49cadd`, 화면 `f400720c8e089754ce7a68aba00a24a4556b1c85cd2c11669b81c7a3b13bf0f9`. raw evidence probes/nes-nrom434/join01. 다음은 실제 227 RUN·IRQ/queue를 이 경로에 연결하고 STOP·base 복구 및 board STA 조건을 검증하는 것이다.
