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

Quartus Lite 전체 보드를 새 디렉터리에서 MAP·FIT·ASM·STA했다. 15,334/15,408 LE, 963/963 LAB, 56/56 M9K다. 최악 setup +0.410ns, hold +0.149ns, recovery +1.575ns, removal +0.489ns이다. 지정 경로 6개 그룹과 기존 미제약 경로 수를 확인했다. RBF와 프로그래머에 공급하는 BI3 바이트가 MMC891과 일치한다. ARM 이미지는 212,992B로 기존보다 36B 늘어 Flash 여유가 0B다. MMC892의 실제 부팅·메뉴 복귀는 NES BOOT 892로 확인할 차례다. [최종 수치와 해시](../analysis/trial892-package.json) · [실기 순서](nes-mmc892-trial.ko.md)

## 재현

1. MMC891 인계 자료로 891E 보드와 최종 ARM 소스를 준비한다. `nes_reset892.py board TEMP`로 보드를 합성하고 `arm`으로 패치를 만든다. `build_nes_mmc479_arm.ps1`의 Base는 probes/nes-trial891/link-credit, Patch와 Out은 probes/nes-reset892/patch와 link다.
2. `check_nes_reset892.py cpu TEMP CPU출력`으로 첫 쓰기까지의 명령을 기록한다. Questa Starter FLOAT 래퍼 안에서 `check_nes_reset892.py simulate TEMP RTL출력 --trace CPU출력`을 실행한다.
3. 최종 링크로 `check_nes_menu533.py`, `check_nes_transfer512_recovery.py --fault none`와 `package_nes_trial855.loader`를 판번호 892로 실행해 WORK에 menu.json, base/result.json, loader.json을 만든다. 기존 `package_nes_trial704.image`로 재합성 보드를 892로 변환한 다음 `package_nes_reset892.py TEMP RTL출력`을 실행한다. 이 단계에서 최종 ARM 응답 재생과 ZIP 재검증을 수행한다.
