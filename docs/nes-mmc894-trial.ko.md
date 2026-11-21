# MMC894 · 첫 입력 블록 실기 진단

1. 전원을 끄고 ZIP의 `MMC894-FIRST-BLOCK-SD-ROOT` 폴더 안 내용물을 SD 루트에 복사한다. 기존 모험도 4 파일 `sd2snes/nes/mmc893.nes`를 같은 폴더에 `mmc894.nes`라는 이름으로 복사한다.
2. SD 메뉴에서 **NES BLOCK 894.nh1**을 한 번 실행한다. ROM 로딩 뒤 첫 입력 블록을 검사하면 게임 화면을 그리기 전에 자동으로 STOP하고 메뉴로 돌아온다. 게임 조작이나 LED 확인은 필요 없다.
3. 실행 뒤 `sd2snes/nes-progress-mmc894.txt`와 생성된 `nes-budget-mmc894.txt`, `nes-game-last-mmc894.txt`를 보관한다. 메뉴로 돌아오지 않으면 전원을 껐다 켠 뒤 남은 로그만 보관한다. 다시 실행하면 같은 파일이 덮어써진다.

### 판독

MMC893의 진행 기록 80개는 판 번호와 경과 시간을 제외하면 MMC892 일반 실행과 같다. 마지막 기록은 223.510초의 `DISPLAY_NEXT`다. 이 시점은 ROM 393,216B 대조 완료 후 START 직전이다. 이후 실행 중에는 SD에 기록하지 않으므로 마지막 줄만으로 정지 명령을 특정할 수 없다.

MMC894에서 `DISPLAY_NEXT bytes=3`의 `total`은 START 직전 ARM 스택 포인터의 십진수 값이다. `PROBE_STOPPED bytes=3 total=0`이면 부팅, 첫 D1 데이터 CRC, D2 뒤 D0의 다음 토큰 확인, STOP 검사를 통과했다. `total`이 0 이외이면 오류 코드를 확인한다. `MENU_PREPARED`와 최종 메뉴 기록은 base·메뉴 복귀 경로를 판정하는 데 사용한다. 진단 성공 시 표시 프레임 수는 0이다.
