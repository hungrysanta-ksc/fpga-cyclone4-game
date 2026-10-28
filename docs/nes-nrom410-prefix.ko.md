# NES410: loader와 실제 FPGA RTL의 짧은 공동 실행

408의 227 FatFS·생성 loader 함수와 원본 SPI framing C를 host thread에서 실행하고, SPI 요청·응답을 DPI와 세마포어로 직렬화해 407 SPI RTL 및 227 boot·loader·physical RTL에 연결했다. FPGA의 쓰기 핀에는 2개 16비트 PSRAM 기능 모델을 연결했다. FatFS 아래 디스크, FPGA 프로그래밍·ID 확인 helper와 run/base 장치는 여전히 시험 모델이며 ARM 명령어를 실행하는 시험이 아니다.

`prefix03`은 실제 첫 file CRC pass 이후 BEGIN과 DATA/STATUS 256바이트를 전송했다. FPGA 내부 READY/count/verified를 강제로 설정하지 않았다. PSRAM 칩·상위/하위 바이트 순서에 따라 쓴 256바이트를 파일 내용과 대조했다. 다음 DATA 직전에 전송 실패를 의도적으로 넣어 loader가 실패를 반환하고 sticky fault를 기록하며 verified·IRQ 복귀가 되지 않는지 확인했다. FPGA는 수신 256바이트 상태에서 RUN·loaded·fault가 없었다. 시뮬레이션 시각 15.648178ms, 호스트 경과 약 6초는 해당 fixture의 값이며 실제 ARM 시간이나 프레임 시간은 아니다. `prefix01`(16B)과 `prefix02`(256B)는 timeout 검사 추가 전 보존했고 `prefix03`이 최종이다.

쓰기는 PSRAM WE 하강에 값을 저장하는 기능 모델이다. 전기적 setup/hold·보드 타이밍 또는 실제 외부 메모리 증명은 아니다. 의도적 오류 후 loader는 fail-closed 경로에서 멈추므로 STOP 또는 base 재프로그래밍은 이 시험에서 실행되지 않는다. 실제 전체 384KiB, 두 번째·세 번째 CRC 완료, RTL readback/FINISH/START, RUN 중 STOP·late DONE·base 복구는 미검증이다. 별도 408 RTL 경계 시험을 이 공동 실행의 완료 결과로 합치지 않는다.

기존 `run136`과 보드 구성 helper, 실제 ARM 실행/IRQ, gameplay ROM 경쟁, 연속 표시 일정 및 MMC4/5 mapper 구현은 아직 결합되지 않았다. 409의 47.935초 wire 계산은 모델 명령 수와 2.625MHz 가정에 따른 시작 시 하한일 뿐이다. 407의 227 NROM 전체 Lite MAP은 18,178LE/13,557조합 논리로 고정 profile의 결과이며, 60fps 후보 및 MMC4/5의 추가 비용은 같은 경계에서 계측되지 않았다. FIT·STA와 실기 동작도 미확인이다.

다음에는 16,384바이트 이후 padding과 CHR을 포함한 전체 전송, PSRAM의 읽기 및 독립 비교를 연결하고 전체 길이 완료 후 START·STOP·base 복구를 실제 helper로 이어야 한다. 장시간 직렬 시뮬레이션의 속도를 개선한다면 RTL 동작과 전송 조건을 보존한 기능 시험과 물리 시간 계측을 분리한다.
