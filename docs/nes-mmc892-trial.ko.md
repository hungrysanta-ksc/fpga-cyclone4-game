# MMC892 부팅 시험

1. 전원을 끄고 ZIP 안의 `MMC892-ADVENTURE-60SEC-SD-ROOT` 폴더 내용물을 SD 루트에 복사한다. MMC891 시험에 쓴 모험도 4 ROM을 `sd2snes/nes/mmc892.nes`로 복사한다.
2. SD 메뉴에서 **`NES-DIAG/NES BOOT 892.nh1`**을 한 번 실행한다. 표시 준비 확인 뒤 자동으로 메뉴에 복귀하는지 확인한다. 게임 입력과 LED 관찰은 필요 없다.
3. 다음 NES 실행 전에 `sd2snes/`의 `nes-progress-mmc892.txt`, `nes-budget-mmc892.txt`, `nes-game-last-mmc892.txt`를 보관한다. 검은 화면이 지속되어 전원을 다시 켰다면 생성된 로그와 화면 상태를 전달한다.

이번 판은 ARM의 RESET 해제 순서를 검증한다. 같은 FPGA와 65816을 사용하며, 표시 FPS는 게임 실행으로 별도 측정한다.
