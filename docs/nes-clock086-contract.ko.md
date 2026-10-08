# CF86 reset 경계와 새 배치·CDC 검증

CF85의 단일 클록 정지 검사는 디지털 동작 검증이었다. 086에서 처음 실제 배치와 별도 기준 클록을 선언하니 `ref_fault/ref_qualified`가 memory reset 식을 통해 내부 상태 레지스터의 data/reset 경로에 직접 연결돼 있었다. CF86은 이 연결을 수정한 후보다. ID는86이며 이전 MCU·071 파일 쌍과 섞지 않는다.

## 수정과 검증

기존 `memory_release[1]`은 raw fault에서 비동기로0이 되고, CLKIN의2단 FF를 통해1로 돌아온다. 이 출력을 초기 대기와 최종 memory reset의 기준으로 사용한다. raw 신호를 downstream reset 식에 다시 OR하지 않는다. 클록 없이 핀을 해제하는 비동기 assert는 유지하고, 내부 상태를 다시 허용하는 해제 경계만 메모리 영역으로 옮긴다.

| 경계 | 적용한 원칙 |
| --- | --- |
| heartbeat의 영역 이동 | 상대 영역의 첫 동기화 FF까지만 false path. 첫→둘째 FF와 이후 제어는 계속 타이밍 분석 |
| ref fault/qualification → memory release | 두 source에서 두 reset-release FF의 비동기 clear 경로만 제외. 실제 배선에서 setup/hold data 연결이 없는지 별도 감사 |
| 나머지 경로 | clock-group 전체 제외 없음. raw guard가 일반 제어 FF로 다시 연결되면 routed 감사 실패 |
| 정상 초기 대기 | release FF 뒤에 기존1600클록 대기 유지. 이전 디지털 시험의180µs 이내 접근 금지와250µs 준비 확인을 재검증 |
| 고장 중단 | 이미지 무효화·자동 재무장 금지·저장 SRAM 비활성·RUN 거부 유지. 두 클록 정지/locked HIGH 반례도 유지 |

최종 fit03과 기능 wave01의 생산 입력16개가 동일하다. 20/약21.477/22MHz 기준 클록의4 GPIO 회귀·128정지 경우·130360응답 비트와 보호 제거4개를 검사했다. 비동기 assert를 없애면 메모리 클록 정지 중 차단 검사가 실패한다. 실제 수정 전 CF85 fit01도 같은 routed 감사에서 일반 제어 FF로의 잘못된 연결 때문에 거부된다.

별도 배선 DB 사본에서 예외를 제거한 뒤3corner의 모든 기준↔메모리 경로를 열거한다. 36행은 heartbeat setup/hold12행과 reset clear recovery/removal24행이다. 기준↔PLL 영역 경로가 생기면 실패한다. 두 번째 동기화 FF까지 false path로 확대하지 않는다. 예외3개의 source/destination 수가 달라져도 SDC가 실패한다.

## 타이밍 결과의 의미

- 최종2446 LE / 191 LAB / 1514 registers / 44 M9K / 135 physical pins / 0 virtual pins / PLL1. CPU/PPU 없는 진단 수치이며 전체NES 여유4LAB와 무관하다.
- 3corner39개 **제약된 내부 summary**가 양수, 최솟값0.158ns다. 기준 입력 A9는 GCLK14로 배치됐다. 원래 CF85 fit01의−5.354ns 및 수정 후 예외 전 fit02의−2.561ns를 보존한다.
- 22MHz 가정은 TimeQuest1ps 해상도에 맞춰45.454ns로 명시했다. 이는 약22.000264MHz의 약간 보수적인 상한이며 실기에서 측정한 값이 아니다. 첫 실행의45.454545→45.454 절삭 경고를 보존한다.
- 새 PSRAM3168경로를 추출했다. PCB각 leg20ns/추가5ns **미측정 가정**에서 최소64.565ns, leg60ns 대조에서는−15.435ns다. CF68 결과를 재사용한 것이 아니다. 이 숫자는 실측 PCB slack이나 외부 IO 승인이 아니다.
- 실제 STA에는 input54포트/744경로, output49포트/1391경로가 아직 미제약이다. 기존 H1의 `async_reg` 미인식·ROM 쓰기 포트 기본0·폭 절삭·dual-clock RAM 경고와 3.3V IO 조건 경고도 남긴다. 경고0인 것은 Questa 컴파일이며 Quartus 전체가 아니다.

비동기 clear→Q의 최대 지연, 실제 pin/PCB/전압·부하 및 메타안정성 MTBF, 두 입력의 물리적 독립성/RESET-held 연속성은 이번에 승인하지 않았다. 4.374µs 검출/3.350µs CE LOW는 여전히 RTL 모형 값이다. 내부 slack 양수나 동기화 FF 위치 확인으로 이 범위를 확대하지 않는다. `installable=false`, 전체 준비도4완료/7부분/1미완료를 유지한다.

## 기존 base의 명령FE 조사

보존된 MK3 base 소스는8MHz 입력에 PLL×12로 CLK2=96MHz를 만들고, `mcu_cmd.clk`와 `clk_test.clk`가 CLK2를 사용한다. 따라서 소스 수준에서는96000000개 샘플 구간이 약1초라는 관계가 맞다. 카운터의 다음1주기는 결과 갱신·초기화에 쓰인다. 최초 완료 전 반환값은FFFFFFFF이며, 명령FE의 dummy byte에서 완료된 값을 한 번 latch한 후4바이트를 반환한다. 측정 모듈에는 SNES RESET 입력이 없다.

이는 **그 소스의 연결 분석**이다. 사용자 `fpga_base.bi3`는 해시가 고정돼 있지만 그 binary와 조사한 base 소스의 빌드 동일성은 아직 입증하지 않았다. 사용자 기기에서 RESET-held에도 기준 클록이 존재한다는 측정도 없다. 따라서 받은 base에서 무조건 명령FE를 호출하거나 반환값을 물리 Hz로 확정하지 않는다. CF86 자체에도 새 FE 측정기를 추가하지 않았다.

다음에는 저장용 정보 재수집을 반복하지 않고, 이미 보유한 입력으로 실제 base의 명령 지원·측정창 provenance를 먼저 좁힌다. 동일성을 확정할 수 없으면 검증된 자체 후보의 **PSRAM 접근을 시작하지 않는** READY/클록 관측 경로를 설계한다. 실기 관측은 지금처럼 외부에서 firmware를 실행하고 TXT/영상을 회수한다. 분해·LED·PC USB를 요구하지 않는다.

## 재현과 다음 단계

```powershell
& $Python -B -X utf8 tools/nes_clock_timing086.py --corrected --cdc-constraints --out $FreshFitASCII --quartus-bin $Quartus
& $Python -B -X utf8 tools/nes_clock_audit086.py --fit $FreshFitASCII --out $FreshAuditASCII --quartus-bin $Quartus
& $Python -B -X utf8 tools/nes_clock_io086.py --fit $FreshFitASCII --out $FreshIOASCII --quartus-bin $Quartus
& ./tools/run_nes_clock_reset086.ps1 -Python $Python -FloatWrapper $FloatWrapper -QuestaBin $QuestaBin -Out $FreshWaveASCII -HostRun $Frozen060Host
# 각각 새 폴더: -Mutation bypass-guard / same-clock / nonsticky / synchronous-assert
& $Python -B -X utf8 tools/verify_nes_clock086.py --evidence $Frozen086Evidence
```

모든 경로는 절대 경로로 지정한다. Quartus/Questa 작업 폴더는 ASCII여야 한다. 공개 생성 도구와 private060 파형/동결 증거의 재현 범위를 구분한다. 실제 Starter FLOAT 한 seat를 순차 사용한다. 첫 감사의 잘못된 `report_unconstrained_paths` 호출과 한글 경로의 도움말 실행 실패는 보존했고, 설치 API 및 [공식 report_ucp 문서](https://resources.altera.com/quartushelp/current/tafs/tafs/tcl_pkg_sta_ver_1.0_cmd_report_ucp.htm)를 확인해 경로 수집기를 수정했다. 회로를 바꿔 이 오류를 숨기지 않았다.

다음 완료 조건은 기준 클록의 실제 가용성·외부 타이밍/비동기 차단과 공통 고장 정책을 좁히는 것이다. 이어 최신 MCU의 CF86 승인·전체80/96KiB C GPIO/SD/STOP/복구, 같은 fit의 ASM/압축/ARM/base/menu/정상044 복원 쌍을 만든다. 새 ARM·ASM·전체 길이 SPI·실기·설치 패키지는 이번 범위에 없다. 성공한084 저장·화면·정상044복원/메뉴/GBC와 기존044–085 archive는 그대로 보존한다.
