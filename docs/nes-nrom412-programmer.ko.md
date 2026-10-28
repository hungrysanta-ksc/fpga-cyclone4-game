# NES412: 실제 227 프로그래머와 loader의 FatFS 결합

227 `fpga.c`의 `nes_diag_byte`, pin wait 및 `nes_diag_fpga_pgm` 구현을 변경 없이 추출해 실제 227 FatFS 및 합성 FAT16 디스크에 연결했다. `programmer02`는 합성 설정 파일의 literal·짧은 run·escape·긴 run을 총 263바이트로 확장하는 정상 사례와 잘못된 run 길이, DONE 시간 초과, 파일 누락을 검사했다. 실제 FPGA GPIO·DONE·설정 장치가 아닌 핀 모델이며 실제 `.bi3` 구성과 FPGA 기능은 검증하지 않는다. `programmer01`의 시험 모델 변수 이름 충돌을 수정해 `programmer02`를 선택했다.

`loader01`은 407 생성 227 loader 전체와 위 실제 프로그래머를 같은 FatFS 시험에서 실행했다. NROM 파일과 `nrom.bi3`·`base`는 합성 FAT16에 있고 두 설정 파일의 데이터는 합성 RLE다. 정상 사례는 파일 세 pass CRC·SPI/PSRAM 모델 readback·모델 RUN/STOP 뒤 실제 프로그래머가 FatFS에서 base를 읽고 설정 핀 모델의 DONE을 검사하는 경로를 통과했다. 잘못된 header, ID, 파일 변경 2가지, 전송 실패, readback 손상, STOP 실패, base DONE 실패 등 기존 9개 사례를 함께 통과했다. base 실패는 실제 프로그래머의 DONE timeout으로 주입했다. loader의 IRQ·토큰, SPI·PSRAM·RUN은 모델이다.

411의 실제 FPGA RTL 공동 실행은 별도로 계속 진행 중이며, 412의 실제 프로그래머가 그 실행에 연결된 것은 아니다. 412의 PASS는 실제 ARM/FPGA/SD/PSRAM 하드웨어, 실제 run136·base 이미지·메뉴 복구를 증명하지 않는다. `programmer02`와 `loader01`의 raw 로그는 `probes/nes-nrom412`에 있고 source fingerprint는 `analysis/nrom412-programmer.json`에 있다.

ARM·IRQ·ROM 경쟁을 포함한 새로운 연속 프레임 계측과 MMC4/5 전체 Lite 비용은 여전히 없다. 기존 비교와 한계는 405 및 411 문서를 유지한다. 다음에는 412 프로그래머를 411의 공동 실행에 결합하고 실제 run136·observer·display 및 base 장치를 연결해야 한다. STOP·final ACK, 캡처·VBlank와 mapper별 ROM 요청을 같은 일정에서 검증하기 전에는 실기나 60fps를 승인하지 않는다.
