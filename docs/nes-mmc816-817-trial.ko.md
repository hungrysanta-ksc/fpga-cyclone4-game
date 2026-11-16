# MMC816·817 실기 시험

전원을 끄고 아래에서 한 판을 선택해 설치 폴더 **안의 내용 전체**를 SD 루트에 복사한다. MMC813에서 쓰던 SMB3(J) ROM을 그 판의 ROM 위치에 넣는다.

| | MMC816 · 60초 | MMC817 · 시간 제한 없음 |
|---|---|---|
| 설치 폴더 | `01-MMC816-60SEC-SD-ROOT` | `02-MMC817-LONG-SD-ROOT` |
| ROM 위치 | `sd2snes/nes/mmc816.nes` | `sd2snes/nes/mmc817.nes` |
| SD 메뉴에서 실행 | `NES MMC3 816.nh1` | `NES MMC3 817.nh1` |

**MMC816**은 MMC813과 같은 동선으로 첫 레벨을 플레이하고 60초 자동 종료 후 메뉴 복귀를 확인한다. 비교 구간은 5–40초와 40–55초다. MMC813 실측은 각각 702화면(20.06fps)과 310화면(20.67fps)이었다.

**MMC817**은 첫 레벨을 지나 중간 성의 내려오는 천장과 다음 스테이지까지 플레이한다. 원하는 시점에 **L + R + Start + Select**를 함께 길게 눌러 메뉴로 복귀한다. 예기치 않게 복귀하면 마지막 장면과 조작을 기록한다.

각 실행 직후 `sd2snes` 폴더의 세 로그를 보관한다. 여러 번 실행할 때는 PC에 복사한 파일명에 회차를 붙인다.

| 판 | 진행 | 표시 통계 | 종료 상태 |
|---|---|---|---|
| MMC816 | `nes-progress-mmc816.txt` | `nes-budget-mmc816.txt` | `nes-game-last-mmc816.txt` |
| MMC817 | `nes-progress-mmc817.txt` | `nes-budget-mmc817.txt` | `nes-game-last-mmc817.txt` |
