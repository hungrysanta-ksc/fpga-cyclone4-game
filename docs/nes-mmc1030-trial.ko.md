# MMC1030 커비 입력 시간 계측판

이 판은 MMC1028의 FPGA 파일과 커비 입력 계측용 ARM을 사용한다. MMC1029·1030은 같은 ARM 코드를 실행한다. 각 판에서 직전 화면 공개와 첫 D1 요청, 블록 복원, 마지막 D2 반환 확인을 대조한다.

1. ZIP 안 `MMC1030-KIRBY-60SEC-SD-ROOT`의 내용을 SD 루트에 복사한다. 이전과 같은 일본판 커비를 `sd2snes/nes/mmc1030.nes`로 둔다.
2. 전원을 껐다 켠 뒤 `NES MMC3 1030.nh1`을 선택한다. 입력 없이 60초를 기다리고 메뉴 복귀를 확인한다.
3. `sd2snes` 폴더의 `nes-budget-mmc1030.txt`, `nes-progress-mmc1030.txt`, `nes-game-last-mmc1030.txt`, `nes-frame-mmc1030.bin`을 보관한다.

먼저 두 판을 각 한 번 실행한다. 비교 구간은 1–30초와 30–60초이며, 43.6초 전후에는 같은 타일 작업량의 입력과 출력 시각을 대조한다.
