# MMC533 제한 실기 전달

532의 작은 tile 우선·최대 128B map 소비기와 ARM을 사용한다. MMC529 실기 보드와 비교해 관련 경로 통과와 전체 STA 무회귀를 확인하는 조건으로 전달했다. 실기 FPS와 실제 메뉴 복귀 결과는 사용자 시험을 기다린다.

| Quartus Lite 25.1 전체 보드 | MMC529 | MMC533 |
|---|---:|---:|
| FIT · LE / 조합 함수 / FF | 성공 · 15,164 / 14,172 / 8,394 | 동일 |
| RAM 비트 / M9K | 264,816 / 51 | 동일 |
| 관련 경로 setup / hold, 구현·명목 | +0.078 / +0.139ns | 동일 |
| 전체 최저 setup / recovery | −7.081 / −8.480ns | 동일 |
| 미제약 입력 / 출력 포트 | 54 / 57 | 동일 |

73개 보드 입력에서 소비 ROM 초기값만 바꾸어 새 프로젝트로 FIT·ASM·STA를 실행했다. 모든 코너의 전체 STA 요약 57개 항목에서 slack과 TNS가 같았다. 구현 경로 목록의 일부 행은 출력 순서가 달랐으나 코너, 클록, 양 종단, slack, 지연과 행별 출현 횟수는 구현·명목 모두 일치했다. 전체 최저 hold +0.139ns, removal +0.487ns, 최소 펄스 폭 +2.627ns였다. 기존 음수와 미제약 IO를 포함하는 **MMC529 동등 조건의 제한 실기 판정**이다. [보드·검증 수치](../analysis/trial533-verification.json)

전달용 STM32 이미지는 212,420B로 212,992B 한도에 **572B**가 남으며 BSS는 18,592B다. 532에서 선택한 ELF와 788개 함수의 주소·크기·바이트가 모두 같았다. 헤더 뒤 펌웨어의 차이는 같은 길이의 시험 식별자 10곳뿐이다. STM3 길이·CRC·반전값, 새 실행 항목 선택과 이전 항목 거부, 1–40초·40–60초 표시 카운터와 미완료 프레임 제외를 검증했다.

두 위상의 65816 독립 재생은 각각 53화면의 실제 표시·최종 ACK를 포함해 8,133/8,128개 이벤트 시각과 RGB가 532 선택 기록과 일치했다. 양 뱅크의 STOP·새 패킷 우선, 이미 시작한 DMA의 완료, 독립 검사와 cold 복구 22건을 다시 실행했다. 실제 전달 ELF의 credit·STOP 경계 6건을 대조했다. base 전용 ARM 복구 시험에서는 MMC533 경로에서 STOP 후 base를 복원하고, programmer·DONE·busy·token 오류 시 안전 복귀를 차단했다. 메뉴 준비·해제 함수는 정상일 때만 준비 기록 후 해제 상태를 남겼다. base 복구 실패, 메뉴 준비 실패, 오류 latch, 체크포인트 실패에서는 해제를 막았다. 이 시험의 programmer·상태 응답·로그 I/O는 모델이다.

`probes/nes-trial533/trial01/MMC533-TRIAL.zip`은 저장소 부모의 작업 폴더에 있다. SOF 변환부터 두 번 독립 포장한 결과는 503,811B와 SHA-256 `8ac77a3f6260ae52b4927a49b1ad15748818890a308c2aab92269d97f9f961c2`로 같았다. MMC529 ZIP에서 해시가 일치하는 menu/base를 가져왔고, RESTORE·게임 ROM은 제외했다. [파일 목록·해시](../analysis/trial533-package.json) · [설치·로그 회수 방법](nes-mmc533-trial.ko.md)

재현하려면 [준비기](../tools/prepare_nes_trial533.py)의 `board`에 529의 526 late 보드와 532의 `client-pair01`을, `labels`에 532의 ARM02/src를 준다. 새 보드에서 Quartus Lite `quartus_sh --flow compile board`와 `quartus_sta -t timing506.tcl`을 실행한다. labels는 기존 MMC479 ARM 빌더의 Patch 입력이다. 532 priority·재생·credit 검사, 518 windows 검사, 512 recovery 검사(`--trial 533`)와 [메뉴 검사](../tools/check_nes_menu533.py)를 실행한 뒤 [검증기](../tools/verify_nes_trial533.py)와 [포장기](../tools/package_nes_trial533.py)의 `--timing matched-mmc529`를 사용한다.
