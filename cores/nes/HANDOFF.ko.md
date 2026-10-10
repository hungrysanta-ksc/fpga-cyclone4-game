# NES 현재 인계 —135 최소 RUN 타이밍 통과

[135 결과](../../analysis/COMMAND135-RESULT.ko.md) · [검증 메타](../../analysis/command135-verification.json) · [134 결선/관측 계약](../../analysis/BOARD134-RESULT.ko.md)

## 다음 작업

선택135fit03를 재사용해 새 hierarchy의 reader held-data/guard/reset/관측 reset과 외부IO 계약을 확인한다. 무변경 MAP/FIT/전체 적재를 반복하지 않는다. 이어 최소 RUN 전용 MCU 식별59+D4, bit별 shared-fault/RDY/예산, 유한 RUN/STOP·진행TXT·base/menu·044복원을 연결한다. ARM116의 CF86 식별86을 그대로 쓰거나 여러 ID를 무조건 허용하지 않는다. 전체 화면/MMC3는 별도다.

최소 보호를 갖춘 유한 RUN 후보가 준비되면 SD 패키지→사용자 실행→TXT로 관측한다. 전체 화면/맵퍼 완성을 기다리지 않는다. PC 직접 연결·LED·부품 재확인·재분해는 요구하지 않는다. 현재 패키지는 없다. 미완료 새 CDC/reset/IO와 MCU 경로를 이전 승인으로 대체하지 않는다.

## 재사용할 구현과 배치

probes/nes-command135/evidence/test02와fit03가 최종이다. nes_command135.py는134 shell을 생성한 다음135 SPI/boot/loader 세 파일만 바꾼다.134 top/observer/core/PLL/QSF/SDC/95개핀은 유지한다. loader loaded_bytes 선언 속성 하나를 제거하면 test02와134 loader가 정확히 같아 기능 시험을 재사용한다. 실행 materializer와 공개 설명문 차이, 마지막 출력 two→three 차이를 verifier가 엄격히 확인한다.

SPI 원인5비트는 기존 SS 상승 edge에서 잡고 다음 memory edge에서 실행한다. load_ready 조기 표본화/지연 추가 없음. hard fault가 pending START보다 우선. bootsticky는check_ready를 전개한 동등식이다. loaded_bytes ENA 제거는 합성 속성뿐이며 기존 state/address 속성을 유지한다.

최종12,026LE/885LAB/4,088reg/12M9K/1PLL/95physical/0virtual. 같은 클록 setup NES+8.217/memory168+0.152/hold최소+0.180ns. 대상 pending_causes+.355/check_failed+1.201/loaded_bytes+.190. fit03/timing134.tsv24행은 이름만134이며135 결과다. targeted135.tsv9행/registers135.tsv17개D 확인. 실패fit01−.183/fit02−.318 보존. 기존134−.330을 현재 실패로 다시 고치지 않는다.

raw setup −6.767ns는reader data_hold→CPU 경로를 포함한다. hierarchy는nes_live_joint:core|...이고 화면 host84/transport가 제거됐다.132의371쌍/16체인 개수나 승인을 복사하지 않는다. **선택135fit03 DB**에서 실제 남은 reader held-data→CPU/PPU, control/reset/observer reset을 추출하고 기능 계약과 대조한다. raw 음수를 무조건false path로 지우지 않는다. IO19입력/44출력, MTBF/전기범위는 미승인이다.885LAB는 전체 영상/MMC3 여유가 아니다.

## MCU 전용 연결 — 중요

기존116은CF86 단축식별86을 기대한다(nes_cf86_session094.py,nes_cf68_mcu.py). 새 회로는65 로더 응답59,70 관측 응답D4이고 기존 단축 helper가 없다. 오래된 portable nes_rom_spi.c의54 기대와 flags86도 별개다. **116 ARM을 그대로 묶거나86/59/D4를 임의 혼용하지 않는다.** 최종 materialized116 소스/guard를 확인하고 후보명/식별/명령을 엄격히 구분한 새 통합을 만든다. 역사적 portable C를 guard가 적용된116 코드로 오해하지 않는다.

70 mode0≤250kHz,CS setup/hold≥1µs. 첫 수신 byte를 버리고7byte D4/flags/error/count32BE. bit0coreRESET,bit1stickyROMfault. count는캐시hit포함CPU ROM sample이지명령/프레임수가아니다. STOP후유지/포화/재구성초기화.65는boot/SPI오류. observer는NESclock이멈추면응답도멈춘다. 기존bit별 sharedfault/RDY/예산, CSS/NMI fail-stop, SD 전이보호를 유지한다. fault뒤SD/UART복구금지;정지/로그없음도시험결과다.

MCU는SNES 실제RESET을 유지한다. 짧은유한RUN→count증가/오류확인→STOP→base/menu→044복원으로 제한한다. 진행TXT는정상소유권 경계에서쓰기/닫기하고 blockedfault뒤로그하지 않는다. elapsed시간은WCET보장이아니다. 로더PRG64KiB/CHR16·32KiB는SMB3384KiB/MMC3지원이아니다. H1소비자는24KiBprogramROM/LoROM/00600B-C/NCR1중재가필요하며현재셸에없다.

## 검증 범위와 보존

원인2-state4194304/boot모델clocked4096/실제SPI2x166/세부정대조/CPU sample6712+별도주입8/관측14 PASS. PLL이상/70nsRAM/합성JMP8000/loadedcount·verified초기값. 전체적재/CHECK·게이트등가·MCU실기검증아님. 변경없는전체쓰기/배치는반복하지않는다.

초기속성개수·Quartus degree문자인코딩검사를수정했다. RTL실패아님. test01/02·fit01/02/03·warnings유지. 새ARM/ASM/package/hardware없음. FLOAT종료/서버정지. 동결1359 manifest92cbf82a7a19750c8fb6803fb6b569af989fce6bcf4b00576164f36ca9d365a5. 완료finalizer/archive044–135수정금지/124격리유지.

## 유지할 실기 기준과 목표

119에서 동일 ARM116/097 CF86의 전체80KiB 적재·비교·STOP·기본FPGA·메뉴복귀·사용자044복원이 통과했다. 메뉴준비491.34초는 펌웨어 시각이며 독립 화면 시각이 아니다. 해당 시험의 GBC 플레이는 미보고다.113 정지 원인은 미확정이며 로그 추가의 타이밍 영향 가능성을 남긴다. 외부E1/E2·8µs·양클록정지 lockedHIGH CE9µs 반례는 미해결이다. 제한 진단6완료/5부분/1미완료는 게임 완성률과 구분한다.

첫 게임 목표: Super Mario Bros 3 (J),mapper4,PRG256KiB+CHR128KiB,393232bytes,SHA `dbb1cb5e18b091ca9101b1c2f5a5d6bdbeaa4a30ae1a504251310f6765cabb49`. 현재 진단 크기를384KiB 지원으로 확대 해석하지 않는다. 이후 맵퍼·호환성을 넓힌다.



## 게시

PR80 병합 확인. 한국어 제목과 작업 목표/작업 내용/작업 결과/작업 의미 네 항목. 사용자 병합. GBC152/원래NES334/과거 공개 해시 유지. ROM/바이너리/미디어/라이선스/개인경로Git제외.
