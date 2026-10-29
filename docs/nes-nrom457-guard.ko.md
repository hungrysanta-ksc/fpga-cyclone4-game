# NROM457: 클록 감시기의 도메인별 reset 해제 후보

456이 분류한 guard 상태에 대해 공통 reset은 계속 비동기로 assertion하고, NES 기준 클록과 memory 클록 각각의 `nes_domain_reset124` 체인을 통해 자신의 상태를 동기 해제하는 격리 후보를 만들었다. 기존 sticky fault·비동기 메모리 차단·startup 대기와 455의 다른 세 RTL 변경은 유지한다. 실제 제품 파일이나 SDC를 변경하지 않았다.

독립 guard RTL은 단일 클록 중단·sticky fault·startup 및 두 클록 동시 정지의 기존 반례를 통과했다. 전체 457 board RTL에서는 기준·memory 클록을 각각 끊어 PSRAM CE/OE/WE·RUN/core 차단과 클록 복귀 시 자동 재무장 금지를 확인했다. 별도의 NES core→227 RUN host C→실제 FPGA queue/tile→65816 에뮬레이터 공동 실행도 패킷 ACK 33회, 타일 DMA 32B, VRAM 4,128B, 체크무늬 46,592픽셀, 최종 ACK·EA retire·실제 run136 STOP 및 관찰값 유지로 통과했다. loader verified/PSRAM은 시드, PLL·호스트 C·RPC 물리 시간은 모델이다. 전체 보드 Questa 0 errors, 기존 포트/초기화 warnings 84개다.

455 대비 QSF 지정 66개 입력 중 guard RTL 한 개만 다르고 같은 Quartus Lite·장치·seed로 FIT는 14,827→14,770 LE, comb 13,635→13,637, FF 8,033→8,037, RAM 185,824bit 동일이다. Quartus의 첫 배선 시도는 충돌을 보고했지만 동일 실행의 최종 FIT는 성공했다. 420 방식의 제한 관련 경로 최악 setup +0.226ns/hold +0.151ns, epoch reset 최소 +1.647ns, 조건부 PSRAM margin +3.144ns/SNES 89.140ns/SPI 164.848ns다. 이 IO 수치는 기존의 미측정 전기적 가정에 의존한다.

456의 NES↔PLL 음수 recovery top-N 표본은 576행·62종단에서 525행·45종단으로 바뀌었다. 기존 guard 직접 상태 19개 대신 기준 도메인 reset release 2개가 표본에 나타난다. 새 NES/memory reset 각 첫 단계는 배선 DB fanout이 두 번째 단계 하나뿐이며, 첫→둘째 setup 최솟값은 NES +44.286ns, memory +4.992ns다. 첫 topology 추출은 경로 패턴/collection 사용 오류로 실패했고 올바른 collection을 사용하는 최종 결과와 함께 보존했다. 표본은 전체 reset 경로가 아니며 MTBF의 보증도 아니다.

전체 raw setup −7.040ns/recovery −9.659ns, 미제약 input 54·output 56과 나머지 reset/CDC 검토가 남는다. 따라서 457은 **실기 전 검토 후보**이며, 전체 timing·전기적 signoff, 실제 재설정·base token/menu 복구, ARM/IRQ 및 지속 60fps는 미검증이다. 결과는 `analysis/nrom457-timing.json`, 원시 자료는 `probes/nes-nrom457`에 있다.
