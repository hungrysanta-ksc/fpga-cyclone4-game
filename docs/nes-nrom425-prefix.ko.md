# NES425: 같은 화면 fixture의 실제 FPGA 전송 prefix

424에서 Mesen의 NES 화면 및 주입 입력 비트 반응을 확인한 같은 `edd81f...` ROM으로 415 공동 실행을 진행했다. 실제 227 loader/FatFS/programmer/run136 host C, 407 boot SPI와 227 observer·screen RTL 및 PSRAM 핀 기능 모델을 연결하고 초기 observer 식별·첫 256B DATA/STATUS와 PSRAM 내용을 정확한 해당 ROM의 PRG byte와 대조했다. 바로 다음 DATA는 의도적으로 실패시켜 verified/IRQ 복귀 차단을 확인했다. `prefix01`은 2.625MHz 대표 위상에서 Questa errors 0이고 소스·bench hash를 포함한다.

GPIO/DONE과 native session은 모델이며, 의도적인 조기 중단 때문에 START 후 observer/screen, 전체 ROM readback, RUN·STOP·base 복구 및 실제 SNES 표시·controller는 이 시험에서 실행하지 않았다. 411 전체 loader RTL 시험은 다른 시험 데이터이고 424 Mesen 화면 시험은 FPGA가 아니므로 하나의 동일 전체 경로 PASS로 합치지 않는다. 다음 단계는 같은 ROM을 실제 NROM cart·NES core에서 실행하고, SNES 버스와 pad 전달, 실제 65816 display/ACK를 순차 검증하는 것이다.
