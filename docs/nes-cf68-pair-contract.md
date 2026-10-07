# NES071 CF68·069 파일 쌍과 복원 검증 계약

범위는 **동일068 fit03의 Standard ASM/CPF, 정확한 압축·실제069 C 복원, 고정069 ARM과의 오프라인 쌍 및 읽기 전용 백업/복원 계획**이다. [결과](../analysis/CF68-PAIR-RESULT.ko.md), [고정 입력](../analysis/cf68-pair-inputs.json), [검증 요약](../analysis/cf68-pair-verification.json), [다음 인계](../cores/nes/HANDOFF.ko.md)를 함께 읽는다. 설치·복원 실행과 새 ARM/map/fit/STA/Questa는 없다.

## 같은 후보를 묶는 규칙

| 구성 | 고정값 |
| --- | --- |
| 준비 도구 | NES-CF68-PAIR-071 |
| MCU | NES-CF68-MCU-069;179336바이트;SHA256 `268bc38df477516cbcee19f17b192151b79c6e011dc801756d1ad02fc0262499` |
| FPGA | NES-DIAG-SAFETY-068;CF68/protocol59;RBF510856바이트;SHA256 `45dcb3f3908b427b66f3fe52f14e56c80efae58d422af95b322580bd57f0a572` |
| SD의 FPGA 경로 | `sd2snes/fpga_nl8.bi3`;212523바이트 |
| 수동 표식 | `NES VERIFY 069 80.nh1`, `NES VERIFY 069 96.nh1`;각0바이트 |
| 승인 진단 파일 | `sd2snes/nes/fine_x.nes`81936바이트, `banks32.nes`98320바이트;payload80/96KiB |
| 결과 로그 | `/sd2snes/nes-verify-last-069.txt` |
| 쌍 manifest 독립 SHA256 | `5d5623c53a2a935c95d8648f65a30def715ff71531f90c51f23d46c39a0dfd02` |

표식 번호를071로 바꾸지 않는다. MCU069가 인식하는 이름을 유지한다. `reference/board.rbf`는 오프라인 대조용이며 SD 변경 대상이 아니다. manifest는 독립 digest와 고정된 ARM/RBF/ROM 해시, 모든 파일 크기·해시, ID/로그/START 계약을 함께 검사한다. CF ID와 DONE만으로 파일 동일성을 승인하지 않는다. `installable`, `hardware_execution`, `clock_halt_safe`, `start_enabled`는 모두false다. 066/CF61·065 쌍과 도구를 보존하고 새 전용 실행기로 분리했다.

## 조립·압축·실제 C의 근거

068의850파일 동결 manifest와 IO 조회 전 inventory가 기록한 `db/`114개, QPF/QSF/SDC·15개 SV·PLL·초기화 HEX를 포함한21입력,10개 report를 대조했다. IO inventory는 `incremental_db/`를 복사하지 않았다. 원본에 추가로 존재한17개 incremental 파일은 별도 관측 목록으로 남기고 새 조립에는 넣지 않았다. 이 차이를114개 손상 또는 독립 고정된131개로 기록하지 않는다.

새 ASCII 폴더에 고정된 DB·입력·report만 복사해 Standard25.1std.0 Build1129 ASM/CPF를 실행했다. 두 단계 모두0오류/0경고다. 원본 DB·입력·report는 조립 후에도 동일하고 map/fit/STA report는 복사본에서도 동일하다. ASM이 자체 DB/report를 만드는 것은 허용하지만 기존 fit/STA를 새 실행으로 기록하지 않는다. 조립 도구는 원본을 수정하지 않는다.

066 encoder의 ESC9B/RUN5B/RUNLONG77·65535 상한과 EOF 규칙을 재사용했다. Python 복원과 실제 C 프로그래머 핀/FIL/tick 모형의510856바이트 전부가 RBF와 같다. 경계66309바이트도 통과했다. C의13오류 대조는 open/read/close/PROG/INIT/DONE high·low, 잘린/zero token5종, 누적 시간 한도다. 예상 오류·종료·mask 해제·postinit 금지·재시도 없음까지 검사한다. 실제 FPGA DONE 또는 설정 성공의 관측은 아니다.

최종 C host는 고정069 ARM 소스의 `nes_diag_runtime.c/h`와 `fpga.c`에 실제 포함된 programmer 본문을 쓴다. 공개 helper와의 첫 바이트 동일성 검사는 LF 및 materialized header의 SPI/TIMER/MENU 오류 코드 추가 때문에 실패했다. 기존 바이트를 수정하거나 같다고 가정하지 않고 정확한069 입력으로 재실행했다. 동결069 manifest와 byte 해시를 검증하고 programmer 본문 포함을 검사하는 `nes_cf68_pair_programmer.py`가 이 절차를 재현한다.

23개 사전 점검은 정확한 쌍/독립 digest/파일 손상/경로/백업 변경/복원 계획과 구형 ARM·RBF·쌍·잘못된 ID/로그·추가 EOF바이트를 포함한다. 모두 **로컬 SD 모형**이다. 변경 대상6파일과 base/menu의 제한 백업 및 읽기 전용 복원 계획만 제공하며 실제 설치/복원 명령은 없다. GBC·게임·세이브 전체 백업은 별도로 확보한다. 기존066 계약의 물리 백업 한계와 준비 조건도 유지한다.

## 재현과 보존

공개 clone은 private fit DB·ARM·ROM·로그·바이너리를 제공하지 않는다. 명시적으로 공급한 원본068 fit와069 동결 archive가 필요하다. 새 출력 폴더에서만 실행한다.

```powershell
python -B tools/nes_cf68_pair_assemble.py --fit <original068-fit03> --out <new-ascii-dir> --quartus-bin <Standard25.1-bin64>
python -B tools/nes_cf68_pair_preflight.py prepare --firmware <pinned069.stm> --rbf <new-ascii-dir>/output_files/board.rbf --out <new-pair>
python -B tools/nes_cf68_pair_preflight.py verify --package <new-pair> --manifest-sha <independent-pair-digest>
python -B tests/nes-functional/cf68_pair_preflight_test.py --package <new-pair> --manifest-sha <independent-pair-digest> --legacy-package <frozen066-pair> --out <new-local-tests>
python -B tools/nes_cf68_pair_programmer.py --mcu-evidence <frozen069-complete> --out <new-C-host> --gcc <host-gcc> --packed <new-pair>/sd-overlay/sd2snes/fpga_nl8.bi3 --raw <new-pair>/reference/board.rbf
python -B tools/verify_nes_cf68_pair.py --evidence <frozen071>
```

경계 C 시험은 생성된 `test_01_eof_and_long_run/boundaries.bi3`와 `.rbf`를 같은 C host에 공급한다. `backup`/`rollback-plan`은 새 CF68 preflight의 동일 CLI이며 읽기 전용이다. 실제 SD 경로를 임의 추정하지 않는다. 동결374파일 manifest `a70297c41f163eacdf9423e9c93ba8abb5a828aa9bf05e3112eadde7d5848cbd`를 보존하고 `freeze_nes071.py` 또는044–071 finalizer를 다시 실행하지 않는다. 처음 두 입력 검사 실패는 터미널 결과를 전사한 기록이며 새 raw log가 있었던 것으로 쓰지 않는다. Git이 공개 JSON의 CRLF를LF로 정규화하므로 입력 JSON은 동결 목록과 파싱 결과를 대조한다. 동결 원시 JSON 바이트는 기존 manifest 해시로 그대로 보존한다.

## 다음 완료 조건과 물리 시험

오프라인 쌍 목표는 달성했지만 H11의 설치 가능한 쌍과 H12의 실제 백업/복원은 아직 부분이다. 준비도5완료/6부분/1미완료를 유지한다. 아래 조건을 확인한 뒤 외부 실기용 제한 패키지를 만들고 사용자에게 전달한다.

1. 실제 SD의 원본 firmware/base/menu·게임·세이브를 독립 백업하고 readback 해시와 복원 절차를 확보한다. base RLE·menu 크기 모형만으로 실제 `smc_id`/`sgb_id`·plain mapper/carttype/offset·4MiB 이하·특수 FPGA/SGB/EGBC 없음의 분류를 승인하지 않는다. 다음 개발은 실제 원본 파일 검사 또는 기존 SD→TXT 방식의 읽기 전용 수집부터 진행한다.
2. 카드/WP·로그 생성·실제 소요 시간·LED 가시성, 중단/실패의 RESET/USB 보호와 수동 복원 수단을 기록한다. 기존 `/sd2snes/nes-verify-last-069.txt`가 있으면 실행 중 덮어쓰기 전에 별도 백업한다. 현재 제한 backup은 변경6파일/base/menu만 기록하므로 로그 보존은 추가 준비 조건이다. PC와 실기 직접 연결은 요구하지 않는다. known 부품·사진·분해를 다시 요청하지 않는다.
3. 전압/PCB/비동기 SPI/SNES와 reset 해제 전 전원 안정 조건, lockedHIGH 쓰기 클록 정지 시 CE8µs 초과 반례를 검토한다. 같은 입력 PLL은 독립 차단이 아니고200µs 대기는 전압 측정이 아니다. 임의 외부 timing 가정으로 H06을 완료 처리하지 않는다.
4. 사용자 실행 후 TXT의 verified/STOP/base/menu-PREPARED와 실제 메뉴 화면·재진입·GBC 정상 플레이를 각각 관측한다. `true`는 안전한 메뉴 복귀 가능, RAM/UART의 RETURN_READY_RESET_RELEASED는 화면 증명이 아니다. native/shared peripheral 오류는 RESET/USB를 유지하고 추가 SD/base를 금지하며 START·불확실한 DATA/ACK 재시도는 계속 차단한다.
