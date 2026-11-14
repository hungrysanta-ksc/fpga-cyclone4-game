# MMC767 60초 재시험

MMC767은 MMC765의 부팅 중 60초 타이머 오작동을 수정한 B 60초판이다. 우선 이 판 하나로 지난 MMC763 성공 때와 같은 첫 레벨 동선을 플레이한다.

1. 전원을 끄고 `01-MMC767-B-60SEC-SD-ROOT` 폴더의 내용만 SD 루트에 복사한다.
2. 기존에 사용한 동일 SMB3 ROM을 `sd2snes/nes/mmc767.nes`로 복사한다.
3. 메뉴에서 `NES MMC3 767.nh1`을 선택한다. 첫 레벨을 플레이하고 약 60초 뒤 자동 메뉴 복귀를 확인한다.
4. `sd2snes/nes-progress-mmc767.txt`, `nes-budget-mmc767.txt`, `nes-game-last-mmc767.txt`를 보관한다. 집계는 5–40초·40–55초다. 재시도 전에는 로그를 복사한다.

두 번째 설치 폴더는 지난 MMC766 장시간판의 동일 파일이다. MMC767 부팅 수정은 ARM의 60초판에만 적용했다. 중간 성 ROM 마감 오류는 조사 중이며 이번 비교에 성 재방문은 필요하지 않다. 장시간판을 선택할 경우 `sd2snes/nes/mmc766.nes`와 `NES MMC3 766.nh1`을 사용하고 L+R+Start+Select로 종료한다. RESTORE와 게임 ROM은 포함하지 않는다.
