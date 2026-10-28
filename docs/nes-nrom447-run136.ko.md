# 실제 run136 START·표시·STOP 공동 검증

227의 verified START, run136 조정 코드 및 STOP·상태 조회를 실행 중인 227 board/NES RTL과 결합했다. 실제 227 RUN C와 FPGA queue·tile·lease, 65816 에뮬레이터가 한 프레임을 처리하고 packet ACK 33회, DMA 32B, 표시 최종 ACK와 EA lease retire를 완료했다. 46,592개 체크무늬 픽셀이 일치했고 화면 SHA256은 `f400720c8e089754ce7a68aba00a24a4556b1c85cd2c11669b81c7a3b13bf0f9`이다.

65816 표시 단계 기록을 실제 board screen RTL에 전달해 run136이 유효한 상태를 확인했다. observer 카운터는 START 뒤 42에서 표시 뒤 372,809로 증가했고 STOP 후 373,018에서 유지됐다. board core reset, RUN 비활성, lease 반환, SNES 버스 해제도 확인했다. Questa 0 errors, 초기화·포트 관련 기존 84 warnings. 원본 실행과 RPC 자료는 `probes/nes-nrom447/run01`, 결과는 `analysis/nrom447-run136.json`이다.

이 시험은 PSRAM 내용과 loader verified 상태를 시드하고 native board session 준비와 console reset을 모델링한다. 227 C는 host에서 실행되며 ARM 명령어·IRQ와 실행기 사이 실제 공통 시간은 검증하지 않았다. 444의 실제 base 프로그래머 바이트 비교와도 별도 실행이다. 따라서 물리 FPGA 재구성·DONE, 실제 SD 파일 identity, 메뉴 복귀와 장시간 무누락·60fps는 아직 확인되지 않았다.
