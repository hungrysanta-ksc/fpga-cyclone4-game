# MMC892 · 첫 RESET 벡터 공급

MMC891 실기에서 모험도 4 적재와 START 뒤 두 벡터 주소만 관측되고 stage 0의 누적값이 `03`으로 남았다. MMC892는 첫 E0에 응답이 없을 때 기존 SPI73 응답의 현재 active 비트(플래그 bit 6)를 ARM이 확인한 뒤 SNES RESET을 놓는다. 정상 E0이면 기존 경로로 진행한다. SPI73 응답의 ID·버전을 확인하고 최대 64회까지 기다린다. 상태가 유효하지 않거나 끝까지 active가 되지 않으면 RESET을 유지한 채 STOP·복구로 간다. 이전 플래그의 누적값을 판단에 쓰지 않는다. 해제 뒤 E0의 빈 큐·CRC 검사도 실행한다.

## 재현한 순서

MMC891E의 실제 로컬 메모리는 START 뒤 NES 클록 8,192회 동안 RAM을 지운다. 그동안 core_reset이 유지되고 브리지가 host_ready를 올릴 수 없다. 이 브리지의 session_reset은 ROM 주소 동기화 레지스터도 0으로 유지한다. /WR가 RESET 중 낮으면 core_reset이 풀려도 브리지 수락은 /WR 유휴까지 기다린다. SPI73의 active 비트는 core_reset만 풀려도 읽을 수 있다.

보드 최상위 RTL에 정상 클록과 검증된 START를 인가했다. NES 클록 주기는 46.566ns, 호스트는 84MHz이며 SPI에는 최종 ARM의 2.625MHz 분주와 SS 전후 2µs 대기를 적용했다. START 후 상태 조회, E0, 벡터 스트로브 순서로 재생했다. 표의 ns는 각 주소의 읽기 시작부터 1ns 간격으로 관측한 최초 값이다.

| 조건 · 시작 위상 4개씩 | 최초 벡터에서 host_ready | 하위 바이트 tag 일치·출력 | 상위 바이트 출력 | 결과 |
|---|---:|---:|---:|---|
| MMC891 · 첫 E0 무응답 후 바로 해제 | 118ns 안에 없음 | 없음 | 없음 | stage 0, `03` |
| MMC892 · RESET 중 /WR 유지, SPI73 active 확인 후 해제 | 26–35ns | 62–71ns | 26–35ns | `00 80`, 첫 쓰기 `$7000=1` |
| 첫 E0부터 유효한 대조군 | 읽기 시작 시 이미 준비 | 26–35ns | 26–35ns | 같은 벡터와 첫 쓰기 |

실패 조건에서 주소 tag만 강제로 `$00:FFFC`와 일치시켜도 OE는 비활성이고 데이터 핀은 고임피던스였다. 반대로 host_ready가 이미 올라간 상태에서 주소를 변경하면 이전 tag 동안 OE가 꺼지고, 새 tag가 일치한 뒤 정확한 바이트를 구동했다. 따라서 이 재현에서 먼저 막힌 곳은 세션 준비였다. 주소 일치 검사는 유지했다. 실기의 실제 RESET 에지나 SNES 내부의 데이터 래치 시각은 계측하지 않았다.

수정 전 RTL 자극에서 START→첫 읽기는 약 0.101ms, 수정 후에는 약 0.425ms였다. 수정 후 네 위상 모두 10번째 SPI73에서 active가 관측됐다. 이 수치는 핀 파형에 대한 재생값이다. 명령 사이 MCU 실행 시간·IRQ는 포함하지 않는다. 65816의 첫 명령부터 첫 stage 쓰기까지는 Mesen에서 얻은 실제 명령 fetch 20건과 640 마스터클록의 쓰기를 보드에 재생했다. 연속 CPU·FPGA 공동 실행은 아니다.

## 최종 링크와 보드

최종 ARM의 RUN 루틴에 네 위상에서 읽은 실제 SPI73 바이트를 재생했다. MMC891은 E0 무응답 시 추가 조회 없이 RESET을 놓았고, MMC892는 각 응답열의 10번째 조회 뒤에만 놓았다. 64회 무응답(active 미설정), 마지막 회차의 준비, 잘못된 ID·버전, 해제 뒤 E0 CRC 오류, 이미 준비된 E0, START 단독과 일반 게임 경로도 검사했다. 수락된 벡터를 읽는 도중 STOP하면 1ns 검사점에서 OE가 풀렸다. 실제 ARM의 STOP 순서·base 복구·메뉴 해제는 주변장치를 모델링해 확인했다.

Quartus Lite 전체 보드를 새 디렉터리에서 MAP·FIT·ASM·STA했다. 15,334/15,408 LE, 963/963 LAB, 56/56 M9K다. 최악 setup +0.410ns, hold +0.149ns, recovery +1.575ns, removal +0.489ns이다. 지정 경로 6개 그룹과 기존 미제약 경로 수를 확인했다. RBF와 프로그래머에 공급하는 BI3 바이트가 MMC891과 일치한다. ARM 이미지는 212,992B로 기존보다 36B 늘어 Flash 여유가 0B다. 아래에 같은 보드의 실기 결과를 기록했다. [최종 수치와 해시](../analysis/trial892-package.json) · [실기 순서](nes-mmc892-trial.ko.md)

## NES BOOT 892 실기 결과

모험도 4의 393,216B 전체를 적재하고 같은 길이를 대조했다. 첫 E0가 무응답이고 후속 E0가 유효한 조건에서 첫 stage 쓰기 `01470001`과 표시 준비 `01ffa903`을 관측했다. MMC891은 같은 진단에서 stage 0으로 5초 만에 시간 초과했다. MMC892는 10ms 단위 24틱(약 240ms)에 stage 3에 도달했다. 이는 부팅 대기 구간 시간이다. SPC 음소거 해제도 확인했다.

STOP과 base 복구가 성공했고, 사용자가 실제 SD 메뉴 복귀를 확인했다. 부팅 진단 1회 결과이며 게임 프레임 수는 0이다. 다음 비교는 같은 설치의 `NES MMC3 892.nh1`으로 무입력 60초를 실행한 뒤 MMC872와 오프닝 1–30초·데모 30–60초 표시 FPS를 대조한다.

## NES MMC3 892 일반 실행 실기 결과

일반 실행에서는 검은 화면이 지속됐고 사용자가 본체 RESET을 눌러도 메뉴로 돌아오지 않았다. 진행 파일은 40,960B(512B × 80)다. 앞의 79개 레코드는 경과 시간을 제외한 모든 필드가 BOOT 성공본과 일치했다. 양쪽 모두 seq 79는 222,470ms의 DISPLAY_NEXT였고 일반 실행의 모드 값은 0, BOOT는 2였다. 일반 실행에서 이후의 DISPLAY_STOPPED·STOP_DONE·MENU_PREPARED 기록은 없었다. 기존 budget·game-last는 BOOT 실행 때 생성된 파일이다.

최종 ARM의 run136은 DISPLAY_NEXT를 기록한 뒤 START를 요청한다. 다음 SD 체크포인트는 세션에서 돌아와 STOP을 검사한 뒤에 남는다. 따라서 일반 실행의 START 수락, stage 3, 첫 프레임 실행, STOP 중 어디까지 갔는지는 미확정이다. nes_checkpoint112는 RUN 중 SD 기록을 허용하지 않는다. 현행 부팅 대조 시험도 native_frames222를 모형으로 대체한다.

MMC872와 MMC892의 최종 ELF에서 native_frames222 진입 시 각각 31,864B(레지스터 저장 8B 포함)를 예약한다. .bss 끝 0x20007954와 스택 상단 0x20010000도 같다. 호출자·하위 함수·IRQ를 포함한 실제 스택 최저점은 미측정이다. 다음 검증은 최종 ARM의 실제 프레임 루틴으로 첫 입력부터 첫 표시 ACK까지 재생하고, 짧게 종료하는 대조 조건에서 STOP·base·메뉴까지 확인한다. 60초 성능 비교는 일반 실행 복구 뒤 진행한다.

## 재현

1. MMC891 인계 자료로 891E 보드와 최종 ARM 소스를 준비한다. `nes_reset892.py board TEMP`로 보드를 합성하고 `arm`으로 패치를 만든다. `build_nes_mmc479_arm.ps1`의 Base는 probes/nes-trial891/link-credit, Patch와 Out은 probes/nes-reset892/patch와 link다.
2. `check_nes_reset892.py cpu TEMP CPU출력`으로 첫 쓰기까지의 명령을 기록한다. Questa Starter FLOAT 래퍼 안에서 `check_nes_reset892.py simulate TEMP RTL출력 --trace CPU출력`을 실행한다.
3. 최종 링크로 `check_nes_menu533.py`, `check_nes_transfer512_recovery.py --fault none`와 `package_nes_trial855.loader`를 판번호 892로 실행해 WORK에 menu.json, base/result.json, loader.json을 만든다. 기존 `package_nes_trial704.image`로 재합성 보드를 892로 변환한 다음 `package_nes_reset892.py TEMP RTL출력`을 실행한다. 이 단계에서 최종 ARM 응답 재생과 ZIP 재검증을 수행한다.
