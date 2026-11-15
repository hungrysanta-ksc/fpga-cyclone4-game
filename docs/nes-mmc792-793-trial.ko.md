# MMC792 · MMC793 실기 시험

| 설치 폴더 | SD 루트의 실행 항목 | 사용자 SMB3(J) ROM 위치 | 종료 |
|---|---|---|---|
| 01-MMC792-60SEC-SD-ROOT | NES MMC3 792.nh1 | sd2snes/nes/mmc792.nes | 약 60초 뒤 자동 복귀 |
| 02-MMC793-LONG-SD-ROOT | NES MMC3 793.nh1 | sd2snes/nes/mmc793.nes | L + R + Start + Select를 함께 길게 누름 |

1. 전원을 끄고 **시험할 폴더 하나의 내용물**을 SD 루트에 복사한다. 판을 바꿀 때는 그 폴더의 `sd2snes/firmware.stm`, FPGA 이미지, 메뉴와 base 파일을 함께 복사한다.
2. MMC763에서 사용한 동일한 SMB3(J) ROM을 표의 경로에 복사하고 메뉴에서 같은 번호의 실행 항목을 고른다.
3. MMC792는 MMC763 때와 같은 동선으로 스테이지 선택을 거쳐 1-1을 플레이한다. 자동 종료 후 메뉴가 돌아오는지 확인한다. 실제 표시 횟수는 5–40초(35초)와 40–55초(15초)로 나누고 map·OBJ 작업량과 함께 비교한다.
4. MMC793은 60초를 넘겨 플레이한다. 월드 1의 스페이드 보너스와 중간 성의 천장이 내려오는 방에서 진행·표시 상태를 확인하고 수동 종료 후 메뉴 복귀를 확인한다. 예상치 못한 복귀나 화면 깨짐이 있으면 장면과 대략적인 플레이 시간을 기록한다.
5. 매 회차가 끝나면 SD의 `sd2snes` 폴더에서 아래 세 파일을 복사한다. 같은 판을 재실행하면 로그가 갱신된다.

| 판 | 진행 | 시간·작업량 | 마지막 실행 상태 |
|---|---|---|---|
| MMC792 | nes-progress-mmc792.txt | nes-budget-mmc792.txt | nes-game-last-mmc792.txt |
| MMC793 | nes-progress-mmc793.txt | nes-budget-mmc793.txt | nes-game-last-mmc793.txt |
