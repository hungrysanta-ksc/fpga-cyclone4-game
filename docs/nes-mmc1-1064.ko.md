# NES 1064 · 젤다 1·2 한글판 실기 시험

DEBUG 또는 RELEASE ZIP 하나를 골라 그 안의 `sd2snes` 폴더를 SD 루트에 덮어쓴다. 두 판 모두 SD 메뉴에서 기존 `.nes` 파일을 직접 선택한다. DEBUG는 동작을 기록하며 RELEASE는 60초 제한 없이 플레이할 수 있다.

1. DEBUG에서 젤다 1 한글판을 선택하고 타이틀에서 시작한다. 첫 방을 나가 화면이 스크롤될 때 배경과 캐릭터가 정상인지 확인한다. 젤다 2 한글판도 타이틀에서 시작해 화면을 전환한다.
2. 각 게임에서 `L+R+START`로 퀵메뉴를 열어 빈 슬롯에 `SAVE STATE`를 한다. `EXIT TO MENU`로 나간 뒤 같은 ROM을 다시 선택해 `LOAD STATE`로 방·캐릭터 위치와 조작이 이어지는지 확인한다.
3. 게임 안에서 기록한 뒤 퀵메뉴의 SRAM 저장을 실행한다. SD 메뉴로 나갔다 같은 ROM을 선택해 게임의 파일 선택 화면에서 저장 내용을 확인한다.
4. 게임을 바꾸기 전에 SD에서 `nes-progress-debug1064.txt`, `nes-game-last-debug1064.txt`, `nes-frame-debug1064.bin`, `nes-stop-debug1064.bin` 중 생성된 파일을 게임별로 복사한다.

이번 MMC1 보드는 PRG ROM 256KiB·CHR RAM 8KiB·배터리 RAM 8KiB 구성이다. FF1&2의 SXROM은 상위 PRG와 배터리 RAM 뱅크 추가 검증이 필요하다.
