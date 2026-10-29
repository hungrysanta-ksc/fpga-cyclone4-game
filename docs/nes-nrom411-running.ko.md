# NES411: 전체 길이 공동 실행 진행

410의 DPI 경계에서 조기 DATA 실패를 없애고, 393,216바이트 쓰기와 실제 FPGA SPI·boot·loader·physical RTL의 독립 readback을 거쳐 verified START 및 STOP을 호출하도록 구성했다. 전체 loader·FatFS C는 host에서 실행하며 FPGA는 실제 RTL, PSRAM은 기능 모델이다. identify136과 run136, FPGA 프로그래밍·base/token 및 IRQ 장치는 408의 모델이다. 따라서 이 시험이 통과하더라도 실제 ARM 명령·IRQ, 실제 run136/표시나 물리 base 복구를 증명하지 않는다.

`tools/test_nes_nrom411_full.py`는 410 시험 생성기를 확장한다. 성공 조건에는 모든 DATA, loader CRC 및 독립 readback, 실제 RTL START/STOP 응답과 모델 base 복구, verified/IRQ 상태가 포함된다. 4096 DATA 또는 read ACK마다 진행 지점을 출력하고 12시간 한도를 둔다. 실제 직렬 타이밍과 FPGA 클록을 사용하므로 긴 시뮬레이션이다. 실행 중 실패나 미완료를 PASS로 간주하지 않는다.

`full01`은 임시 Questa Starter FLOAT로 실행을 시작했다. 작업 당시 아직 최종 result가 없으므로 **전체 경로 PASS는 없다**. 시험 종료 후 원시 compile/vlog/simulation 로그와 result를 `probes/nes-nrom411/full01`에 보관하도록 실행했다. 이 파일이 없거나 PASS 조건이 충족되지 않으면 재현 및 실패 분석이 필요하다. 기존 410의 256바이트 PASS와 408 별도 시험을 전체 결과로 합산하지 않는다.

현재 ARM·SPI·IRQ·ROM 경쟁을 포함한 새 연속 프레임 측정과 MMC4/5의 같은 경계 Lite 전체 비용은 없다. 비교 가능한 기존 근거는 405의 227 실기 60.06초/465 표시 ACK, 402 후보의 914·915 VBlank 미달 및 20,199LE/16,508조합 논리 전체 MAP, 376의 미구현 MMC4 live latch와 MMC5 tag/split 제한이다. workload와 구현이 달라 407 NROM MAP의 절감을 해당 후보·mapper에 산술 적용하지 않는다. 60fps, 새 NROM 실기, MMC4/5 지원과 FIT/STA는 미입증이다.
