# 실제 227 RUN과 FPGA·65816 공동 실행

434의 수동 순서 조립을 byte-identical 227 `nes_runtime165_begin/step`, native receiver, resident planner, plan service, sink window와 sink C로 교체했다. 429의 실제 보드 RTL geometry 25블록은 D0/D1/D2/D3 통신 모델로 재생한다. ROM·loader·capture 및 E0/E1 queue도 모델이다. plan SPI는 227 direct/tile/lease RTL, 65816 버스는 같은 RTL과 Mesen의 실제 65816 프로그램에 파일 transaction RPC로 연결했다.

RUN이 26회 step, SPI 249회와 화면 패킷 33개를 실행해 화면 1회, 실제 65816 최종 ACK 1회 후 EA retire 1회를 완료했다. 65816이 실제 RTL descriptor 한 개의 32바이트를 DMA로 소비했고 VRAM 4,128B를 기록했다. 화면의 46,592 체크무늬 픽셀은 431 및 434와 동일하다. Questa는 0 errors/0 warnings. RPC는 각 실행기를 논리적으로 연결하지만 공통 시간 모델이 아니며 ARM 기계어·IRQ·실기·base 복구·60fps는 검증하지 않는다.

ROM `61cc6ae495fb34dd6aa28497db6f584fa308063a79ba9412bde50c0c9419fd2c`, geometry `3cf10a8d97a636f46e55bb892ba973b860070971feea5044ff418ec3fb49cadd`, 화면 `f400720c8e089754ce7a68aba00a24a4556b1c85cd2c11669b81c7a3b13bf0f9`. raw evidence probes/nes-nrom435/run01. 다음은 중간 취소·STOP과 base 복구, 실제 E0/E1 queue 및 loader/전체 보드 경로 결합이다.
