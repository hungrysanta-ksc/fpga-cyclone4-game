# NES409: 전체 loader의 시작 시 SPI 호출 계측

408의 실제 227 FatFS와 생성 loader C, 합성 FAT16, SPI·PSRAM 및 RUN/base 모델을 그대로 사용하고 SPI 호출 카운터만 추가했다. 정상 사례는 8바이트 전송 1,966,095회이며 DATA 393,216회, 일반 STATUS 393,225회, 독립 읽기 READ·CHECK_STATUS·ACK 각 393,216회, BEGIN·END·OPEN·FINISH·START·STOP 각 1회다. 나머지 8개 오류 사례도 기존 assertion을 통과했다. 자세한 명령별 수치는 `analysis/nrom409-traffic.json`과 로컬 `probes/nes-nrom409/traffic03`의 로그에 있다.

2.625MHz 일정 클록과 프레임당 정확히 64비트를 가정하면 이 호출의 순수 wire 시간은 47.935269초다. 407에 기재한 19.174초는 DATA와 그 직후 STATUS만 포함한 부분 하한이다. 이번 수치는 loader가 START 후 호출하는 **모델 run136**의 트래픽만 포함하며 실제 run136의 추가 전송, CS 간격, MCU 지연, IRQ, 파일 접근, FPGA/PSRAM 대기와 재시도를 포함하지 않는다. 실제 ARM이나 FPGA에서 측정한 시간은 아니며 시작 시 로딩 비용이지 게임 중 프레임 시간이 아니다.

408의 FPGA 시험은 READY/count/verified를 넣은 별도 실행이다. 전체 227 loader/FatFS와 실제 RTL 및 동작 PSRAM 모델을 한 실행에 연결한 증거, 실제 base FPGA 복구, 연속 프레임 시간, MMC4/5 실제 비용은 이번에 새로 확보하지 못했다. 376의 MMC4 resolved fetch 재생은 live latch 구현이 아니며 MMC5는 13비트 tag 한도와 split 스트레스 초과가 남아 있다. 두 mapper의 실제 추가 시간과 전체 회로 비용은 여전히 미측정이다. 407의 Lite MAP과 402의 60fps 후보는 경계가 달라 산술 결합하지 않는다. 다음 관문은 408 문서의 통합 실행과 동일한 ROM 위상·실제 ARM/IRQ/SPI/ROM 일정이다.
