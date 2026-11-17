# MMC824 모험도 4 무입력 데모 · 60초 실기판

1. 전원을 끄고 ZIP의 `MMC824-ADVENTURE-60SEC-SD-ROOT` 폴더 **안의 내용물**을 SD 루트에 복사한다. 기존 파일은 덮어쓴다.
2. MMC820에서 사용한 일본판 모험도 4 ROM을 같은 SD의 `sd2snes/nes/mmc824.nes`로 복사한다. 원본의 SHA-256은 `9d7402da135fd1290346ccc9332836daee3a9a3cda3789999c3f86efdb5b19c2`다.
3. SD 메뉴에서 `NES MMC3 824.nh1`을 선택하고 버튼을 뗀다. 타이틀에서 시작 버튼을 누르지 않고 자동 플레이 데모와 약 60초 뒤 메뉴 복귀까지 기다린다.
4. SD의 `sd2snes/`에서 `nes-progress-mmc824.txt`, `nes-budget-mmc824.txt`, `nes-game-last-mmc824.txt`를 보관한다. 화면이 일찍 멈췄다면 마지막으로 보인 장면과 메뉴 복귀 여부도 함께 기록한다.

비교 기준은 같은 무입력 동선에서 측정한 MMC820의 **5–40초 15.51 FPS, 40–55초 16.20 FPS**다. 각 구간에서 표시가 완료된 화면만 센다.
