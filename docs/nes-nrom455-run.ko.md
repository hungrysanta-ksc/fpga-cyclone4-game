# NROM455: loader RUN 진입 경로와 공동 보드 검증

454의 남은 동일 클록 setup 경로는 loader sticky fault에서 RUN 상태 레지스터까지였다. 기존 RUN destination에서 sticky fault 차단을 공통으로 묶고 나머지 명령 우선순위를 그대로 표현한 격리 후보를 만들었다. 452 SDC, 453 클록 감시, 454 같은 edge 길이 비교를 포함한다. 실제 제품 파일은 바꾸지 않았다.

실제 454·455 loader RTL의 294,912개 one-step 상태 조합, 1,056개 쓰기·중단 시퀀스, 524,288개 count 사례가 일치했다. fault 차단을 고의로 뺀 음성 대조는 오류를 검출했다. 455 loader를 포함한 SPI·boot·reader 회귀에서 13,200개 C0/C1 판정, 14,016 SPI bit, read 100·ACK 7·corruption 19·cancel 72·overlap 2 및 상위 비교 음성 대조가 통과했다. 전체 가능한 물리 동작이나 전체 ROM 업로드를 이 시험으로 주장하지 않는다.

실제 455 board RTL에서 기준 NES 클록과 메모리 클록을 각각 중단했을 때 PSRAM 핀 차단·core/RUN 정지·sticky fault 및 클록 복귀 후 자동 재무장 금지가 통과했다. 별도 455 board/NES core→227 RUN host C→FPGA queue/tile→65816 에뮬레이터 공동 시험에서 패킷 ACK 33, 타일 DMA 32B, VRAM 4,128B, 표시 최종 ACK·EA retire·실제 run136 STOP 및 46,592 체크무늬 픽셀이 통과했다. 두 시험의 PLL·PSRAM은 모델이고 loader verified/메모리는 시드다. Questa full-board 시험은 0 errors, 기존 초기화/포트 경고 84개다. ARM 명령·IRQ·공통 물리 시간은 실행하지 않았다.

누락 없는 452 fit02 대비 QSF 지정 입력 66개 중 `nes_live_joint.sv`, `nes_rom_spi.sv`, `nes_rom_loader.sv` 세 파일만 다르다. Quartus Lite 전체 FIT는 14,827/15,408 LE, 13,635 comb, 8,033 FF, 185,824 RAM bits다. 420과 같은 제한 관련 경로 분류의 최악 setup +0.213ns/hold +0.122ns, epoch reset 최소 +1.512ns, 45개 첫 단계 fanout, 조건부 PSRAM margin +4.854ns, SNES 82.425ns, SPI 167.229ns가 측정됐다. 제약을 고친 loader 경로는 강화 기준 +0.480ns다. 해당 IO 수치는 기존 전기적 가정에 조건부다.

전체 raw setup −6.429ns, recovery −9.022ns이며 미제약 IO와 reset/CDC가 남는다. 최악 recovery는 NES core reset에서 host tile bulk의 로컬 취소 reset 해제 체인으로 간다. 이러한 비동기 경로는 임의로 false path 처리하지 않았다. 정상적인 timing signoff, MTBF 또는 실기 승인으로 해석하면 안 된다. 455는 실기 전 검토 후보이며 base 재설정·DONE·token·menu 복구, paired 배포물·ARM 실행, 지속 capture와 60fps는 미검증이다.

원시 결과는 `probes/nes-nrom455`, 수치는 `analysis/nrom455-timing.json`이다.
