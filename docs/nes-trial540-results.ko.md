# MMC540 제한 실기 전달

선택은 539의 행 주소 비교 ARM과 538의 예산·descriptor 선행 준비 및 raw 서비스 직접 호출 65816이다. 두 시작 위상에서 30개 첫 BG 공급 구간, 951의 SEAL 후 한 VBlank 표시, 952·954 최종 대기 0회와 밀집 평균·마지막 ACK 조건을 통과했다. 실기 기준은 MMC533의 12.24fps이며 MMC540은 사용자 시험을 기다린다. [일정별 비교](nes-first539-results.ko.md)

| 검증 항목 | MMC540 |
|---|---:|
| Quartus Lite 전체 FIT | 성공 |
| LE / 조합 함수 / FF | 15,164 / 14,172 / 8,394 |
| RAM 비트 / M9K | 264,816 / 51 |
| 관련 setup / hold, 구현·명목 | +0.078 / +0.139ns |
| 전체 최저 setup / recovery | −7.081 / −8.480ns |
| ARM Flash / 여유 / BSS | 212,428 / 564 / 18,592B |
| 전달 라벨 변경 전후 동일 ARM 함수 | 788개 |

MMC533 전체 보드의 73개 입력 중 소비 ROM 초기값만 바꿨다. 관련 경로 setup·hold는 통과했고, 모든 코너의 전체 STA 요약·구현 및 명목 경로 목록·미제약 포트 수가 MMC533과 같았다. 사용자가 승인한 MMC529 동등 조건의 제한 실기 판정을 적용했다. 1–40초·40–60초 표시 집계, 미완료 제외, 새로운 메뉴 항목과 이전 항목 거부, STOP/base 복구의 정상·program·done·busy·token 경계를 전달 ELF에서 확인했다. [보드·펌웨어·복구 검증](../analysis/trial540-verification.json)

패키지 이름은 `MMC540-TRIAL.zip`, 메뉴 항목은 `NES MMC3 540.nh1`, 게임 경로는 `sd2snes/nes/mmc540.nes`다. 로그 세 파일도 `mmc540`으로 분리했다. 해시가 확인된 기존 menu/base를 포함하며 게임은 사용자가 준비한다. 요청대로 RESTORE를 제외했다. 독립적으로 두 번 만든 ZIP이 바이트 단위로 같다. [패키지 파일·해시](../analysis/trial540-package.json) · [설치 및 시험 방법](nes-mmc540-trial.ko.md)

재현은 [540 라벨 생성기](../tools/prepare_nes_trial540.py)와 기존 MMC479 ARM 빌더를 사용한다. [보드 준비기](../tools/prepare_nes_map535_board.py)에 MMC533 보드와 538 client04를 주고 Quartus Lite `quartus_sh --flow compile board`, `quartus_sta -t timing506.tcl`을 실행한다. 기존 windows518·tile532 credit·menu533(`--trial 540`)·transfer512 recovery(`--trial 540`) 검사를 실행하고 [검증기](../tools/verify_nes_trial540.py) 뒤 [포장기](../tools/package_nes_trial540.py)를 실행한다.
