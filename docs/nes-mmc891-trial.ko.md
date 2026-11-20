# MMC891 · NES BOOT 진단

이번 시험에서는 MMC890이 검은 화면으로 남았을 때 보드가 RESET 벡터 두 바이트와 첫 명령을 공급했는지 확인한다.

1. 전원을 끄고 ZIP 안의 `MMC891-ADVENTURE-60SEC-SD-ROOT` 폴더 **내용물**을 SD 루트에 복사한다.
2. 이전 시험에 쓴 모험도 4 ROM을 `sd2snes/nes/mmc891.nes`로 복사한다.
3. 전원을 켜고 SD 메뉴에서 **`NES-DIAG/NES BOOT 891.nh1`**을 한 번 실행한다. 자동 메뉴 복귀 여부를 기록한다. LED 관찰이나 게임 조작은 필요 없다.
4. `sd2snes/`의 `nes-progress-mmc891.txt`, `nes-budget-mmc891.txt`, `nes-game-last-mmc891.txt`를 전달한다. 검은 화면으로 남아 전원을 다시 켠 경우에는 다음 NES 실행 전에 생성된 파일을 보관한다.

NES BOOT는 표시 준비 확인 뒤 STOP·메뉴 복귀로 이어지는 진단이다. 이번 판의 성능 비교는 보류한다.
