# MMC813·814 첫 스테이지 진입 재시험

전원을 끄고 선택한 설치 폴더 안의 내용 전체를 SD 루트에 복사한다. 기존 시험에서 쓴 SMB3(J) ROM을 해당 이름으로 복사하고 아래 항목을 실행한다.

| | MMC813 · 60초 | MMC814 · 장시간 |
|---|---|---|
| 설치 폴더 | `01-MMC813-60SEC-SD-ROOT` | `02-MMC814-LONG-SD-ROOT` |
| ROM 위치 | `sd2snes/nes/mmc813.nes` | `sd2snes/nes/mmc814.nes` |
| SD 메뉴 항목 | `NES MMC3 813.nh1` | `NES MMC3 814.nh1` |

**MMC813**에서 이전과 같은 동선으로 월드 1의 1-1에 들어간다. 첫 화면이 그려진 뒤 조작이 이어지는지, 60초 후 SD 메뉴로 돌아오는지 확인한다. 완주한 실행은 MMC807 첫 레벨의 5–40초(19.03fps)·40–55초(18.47fps)와 비교한다.

**MMC814**에서도 1-1에 진입해 진행한다. 진입이 정상이면 중간 성 이후까지 플레이하고 **L + R + Start + Select**를 함께 길게 눌러 SD 메뉴로 복귀한다. 도중에 자동으로 복귀했다면 마지막으로 보인 장면을 기록한다.

각 실행 직후 SD의 `sd2snes` 폴더에서 아래 세 파일을 보관한다. 같은 판을 다시 실행하기 전에 복사해야 이전 기록이 남는다.

| 판 | 진행 | 표시 통계 | 종료 상태 |
|---|---|---|---|
| MMC813 | `nes-progress-mmc813.txt` | `nes-budget-mmc813.txt` | `nes-game-last-mmc813.txt` |
| MMC814 | `nes-progress-mmc814.txt` | `nes-budget-mmc814.txt` | `nes-game-last-mmc814.txt` |
