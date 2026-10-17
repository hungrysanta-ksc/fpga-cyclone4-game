# NES214: 실제 ROM 응답 대조와 시작 원인 보존

## 작업 의미

213 성능 경로를 실기에서 시작시키기 위한 최소 원인 분리다. 60fps를 위한 resident/dirty 구현을 바꾸지 않는다. 정상210과 실패213의 부팅을 비교한 뒤에도 실기 실패를 재현하지 못했으므로, 이번 실기판은 **원인 확인판**이며 수정 완료라고 주장하지 않는다.

## 비교 결과와 한계

선택207의 실제 sink bridge/ROM/status RTL과 top의6개 버스 assign을 사용했다. RUN은 fixture, 다른 소비자 버스는 비활성이다.100ns 읽기/150ns 쓰기 창에서 실제 ROM 버스가 내준32768바이트로 Mesen ROM을 구성하고 실제65816 부팅을 실행했다. 부팅 중 관찰된 ROM 읽기와7000/7001 쓰기를 같은 RTL에 재생하고 SPI73 응답을 검사했다.

- 정상210: ROM읽기7870, 상태쓰기4, replay7879 checks. stage1→2→3, SPC A9.
- 실패213: ROM읽기7104, 상태쓰기4, replay7113 checks. stage1→2→3, SPC A9.
- 비활성RUN은 ROM을 구동하지 않고 상태0, SPI가 idle이 되기 전 bridge admission 차단, STOP 이후 상태3/flags7 유지 확인.
- 4KiB compact 주소 매핑과 ROM 바깥FF, 리셋 벡터8000 확인.

**이것은 실시간 클록 결합 co-simulation이나 실제 ARM의 리셋 핀 구동·실물 전기 타이밍 검증이 아니다.** Mesen read callback이 수집한 트래픽을 사용하며 RTL에서 reset-vector 읽기는 별도로 명시 재생했다. 물리 버스 파형과 활성 peer/core/클록 조건이 빠져 있다. 따라서 통과로213 실기 결과를 부정하거나 부팅 경계를 모두 닫았다고 주장하지 않는다.

## 최소 펌웨어 변경

기존 `native_boot172`의 순서와 제한을 유지하며24바이트 scalar 기록만 추가한다. 성공을 포함한 반환 사유는 READY1/SERVICE2/STATUS3/COPY4/TIMEOUT5/POLL_LIMIT6이다. 오류6과nativeSERVICE2 기존 전파는 유지한다.5초/65536poll 제한, 자동 재시도 없음,SD쓰기 없음,CF86/STOP/base/menu 보호 경로 그대로다.

기존 budget TXT에 `boot_schema=214`, `boot_reason`, `boot_polls`, `boot_ticks`, `boot_first_hex`, `boot_last_hex`, `boot_signals_hex`를 추가한다. 상태word는 `[31:24]valid,[23:16]read flags,[15:8]error,[7:0]stage`. signals는 하위byte가 진입/다음byte가 종료 시 RESET asserted(bit0), FPGA DONE(bit1), MCU_RDY(bit2)이다. first는 첫 성공한 loop0의 상태, last는 마지막 보존 상태다. 서비스·SPI 실패 시 last는 앞선 표본일 수 있다. 보호 실패에서는 기존 안전 저장 gate 때문에 TXT 자체가 없을 수 있다.

메뉴에서 기존 카운터를 지우고 부팅 진입에서 기록을 초기화한다. `nes_runtime165_begin`의budget reset은 이 독립 기록을 지우지 않는다. 이전실행의기록을새시작결과로오인하지않도록budget는실행식별214와함께읽는다. 조기부팅진입전에실패한경로의기록은이번판분석대상외이며reason0/미기록을성공으로해석금지.

## 검증과 다음 판정

실제gate/formatter11가지:즉시/지연READY, tickwrap, COPY오류, service/status오류, 멈춘tick/poll상한, stage1/2/flags7대기, 이전valid후통신실패. 반환값/기존첫오류유지/기록retention/문자열경계검사 통과. budget 최대2571/4096. 전체ARM207084B/static27836/RUN32088/IRQ508/여유4992B. 플랫폼·라이브러리정규화명령검사 유지. 게임본문 로그형식은동일길이식별자교체뿐으로기존4047상한유지. 실행중renderer/plan/sink파일바이트동일. FPGA는213바이트그대로로새ASM/FIT없음.

다음 실기는214 한 번으로 판정한다. TIMEOUT+stage0/flags0이면 실제SNESreset/bus관찰경로, flags7+stage1이면ROMcopy, stage2이면WRAM/SPC, SERVICE/STATUS면통신·보호조건으로좁힌다. 이는조사방향이지각조건의원인확정이아니다. READY로게임이실행되면일시적시작실패가능성을남기고첫레벨스크롤측정을재개한다. 원인미재현상태에서timeout확대/무조건retry/cache설계폐기/반복FIT를하지않는다.

카트리지저장SRAM/GBC164/기존ROM/배포/완료archive보존.60fps→긴플레이/오류·리셋로그→입력품질순서유지.
