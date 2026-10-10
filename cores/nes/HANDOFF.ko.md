# NES 현재 인계 —134 물리 RUN 결선과 관측

[134 결과](../../analysis/BOARD134-RESULT.ko.md) · [검증 메타](../../analysis/board134-verification.json) · [133 계약](../../analysis/RUN133-RESULT.ko.md)

## 다음 작업

134fit02의 diagnostic_release -> SPI pending_body_error[2] 같은 클록 -0.330ns 경로를 상세 보고서로 수정한다. 변경 경계 시험과 새 배치의 reader/guard/reset/외부IO만 확인한 뒤 MCU70/D4 관측·유한 RUN·STOP·진행TXT·메뉴/044복원을 연결해 최소 실기 패키지로 간다. 전체 화면 소비자·MMC3는 별도이며 무변경 전체 적재/부품/저장/131배치를 반복하지 않는다.

실기 우선 원칙을 유지한다. 최소 안정성은 현재 **아직 미충족**이다. 실기 배포 전 같은 클록 실패 수정, 영향받는 새 CDC/reset/외부IO 계약, MCU 유한 RUN·진행TXT·STOP·base/menu/044복원을 연결한다. 화면 렌더링 전체를 기다리며 동일 저장/clock/부품/ROM 전체 적재 시험을 반복하지 않는다. 실제 장치는 외부 SD 실행→TXT 전달 방식이며 PC 직접 연결·LED·재분해를 요구하지 않는다.

## 선택된 구현과 정확한 실패

`probes/nes-board134/evidence/test02`와`fit02`가 최종이다. 보드 top은`src/nes/diagnostic/fxpak_nes_run134_top.sv`, 관측은`nes_run_observer134.sv`. materializer가 고정131fit05에서 core를 복사해 선언4개 이동 및 관측 출력3개만 추가한다. 기존131/132/133 원본은 수정하지 않았다. 134 셸은SNES 소비자를 끄므로 합성 결과는 전체131 회로와 다르다.

12,001LE/893LAB/4,087reg/12M9K/1PLL, 실제95핀/가상0핀. 같은 클록 setup NES+7.445ns/memory168 **−0.330ns**, hold최소+.179ns. 실패는`diagnostic_release.release_reset[1] -> loader_boot.control.pending_body_error[2]`. 상세`fit02/same134-8_slow_1200mv_85c-setup-2.rpt`, 전체24행`timing134.tsv`. 새로운 물리 핀 배치에131+.041ns/132371쌍 승인을 상속하지 않는다. raw−6.173ns/IO입력19출력44/reset/MTBF도 미승인이다. 무작위 seed/전체 배치를 반복하지 말고 실제 상세 경로를 고친다.

## 관측과 MCU 계약

70번 읽기 명령 뒤7바이트: D4/flags/first ROM error/count32BE. flags bit0 core reset,bit1 sticky ROM fault. command 첫 수신 바이트는 버린다. SPI mode0≤250kHz, CS setup/hold≥1µs. 모든56비트를 명령 수신 때 캡처한다. CPU ROM sample(캐시 hit 포함) 누적이며 명령/프레임/PSRAM 읽기 횟수가 아니다. STOP 뒤 유지, count포화, FPGA 재구성으로 초기화한다. 다른 SPI slave60..6A와 겹치면 MISO를 띄운다.

MCU_RDY는 memory guard/startup 가능 여부이지 RUN·오류 없음이 아니다. boot/SPI 오류는 기존65, ROM 서비스 오류만70에서 읽는다. 소스 clock이 멈추면70 응답도 멈추므로 기존 shared-fault/RDY/예산을 bit마다 확인해야 한다. 오류 뒤 SD/UART 회복을 시도하지 않는 기존 fail-stop 원칙을 유지한다. MCU70 통합과 로그·실기 패키지는 **아직 없다**. MCU는 실제 SNES RESET을 계속 잡아야 하며 SNES bus는고임피던스다.

H1 보드소비자는24KiB programROM/LoROM/00600B-C epoch/NCR1 중재가 필요하다. 현재 live top에 programROM이 없으므로 단순 배선만으로 화면이 나오지 않는다.134의작은 자원은 host84/transport 등이 제거된 최소RUN용이다. 전체video/input/audio/MMC3는 별도 구현한다.

## 검증 범위/보존

두 위상에서실제CPU sample6,712/관측14, 포화주입8별도, coherent snapshot 부정대조 검출. 이상PLL/70nsRAM/합성JMP8000/loadedcount+verified초기값; BEGIN/END/START/STOP만실제SPI. ROMfault주입은 관측보존 검증이다. 전체적재/전체CHECK/ARM/실기를 다시 통과한 결과가 아니다.

초기test01/fit01과 최종test02/fit02 보존. test02 뒤 unused-pin QSF만 추가;회로해시동일. 최종Quartus 실제unused pin은weakpullup 포함inputtri-state며 nooutputground. 라이선스오류/승인거부없음.124archive불일치격리유지. 동결873 manifest`304db3427a50dbcf59dd7d3975d27dc0e37427b1a993c72024af4c05038469a8`. 완료finalizer/archive044–134 수정금지.

## 유지할 실기 기준과 목표

119에서 동일 ARM116/097 CF86의 전체80KiB 적재·비교·STOP·기본FPGA·메뉴복귀·사용자044복원이 통과했다. 메뉴준비491.34초는 펌웨어 시각이며 독립 화면 시각이 아니다. 해당 시험의 GBC 플레이는 미보고다.113 정지 원인은 미확정이며 로그 추가의 타이밍 영향 가능성을 남긴다. 외부E1/E2·8µs·양클록정지 lockedHIGH CE9µs 반례는 미해결이다. 제한 진단6완료/5부분/1미완료는 게임 완성률과 구분한다.

첫 게임 목표: Super Mario Bros 3 (J),mapper4,PRG256KiB+CHR128KiB,393232bytes,SHA `dbb1cb5e18b091ca9101b1c2f5a5d6bdbeaa4a30ae1a504251310f6765cabb49`. 현재 진단 크기를384KiB 지원으로 확대 해석하지 않는다. 이후 맵퍼·호환성을 넓힌다.


## 게시

PR79 병합 확인. 한국어 제목과 작업 목표/작업 내용/작업 결과/작업 의미 네 항목. 사용자 병합. GBC152/원래NES334/과거 공개 해시 유지. ROM/바이너리/미디어/라이선스/개인경로Git제외.
