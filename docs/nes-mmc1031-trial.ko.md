# MMC1031 커비 60초 입력 계측판

MMC1030의 OBJ 선행 읽기 경로에서 첫 입력 블록이 준비된 뒤 ARM이 읽기까지 걸린 시간을 기록한다.

1. ZIP 안 `MMC1031-KIRBY-60SEC-SD-ROOT`의 내용을 SD 루트에 복사한다. 기존에 사용한 일본판 커비를 `sd2snes/nes/mmc1031.nes`로 둔다.
2. 전원을 껐다 켜고 `NES MMC3 1031.nh1`을 선택한다. 입력 없이 60초 실행한 뒤 메뉴 복귀를 확인한다.
3. `sd2snes` 폴더의 `nes-frame-mmc1031.bin`, `nes-budget-mmc1031.txt`, `nes-progress-mmc1031.txt`, `nes-game-last-mmc1031.txt`를 보관한다.

MMC1031과 MMC1032를 각각 한 번 실행한다. 표시 FPS는 1–30초와 30–60초로 나누고, 입력 시각은 후반 30초에서 작업량이 맞는 화면끼리 비교한다. 화면 깨짐이 자연스럽게 보이면 판 번호와 대략적인 경과 초를 함께 적어 둔다.
