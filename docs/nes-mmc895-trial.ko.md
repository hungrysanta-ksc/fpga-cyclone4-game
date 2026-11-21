# MMC895 · 첫 입력 제안 확인

같은 MMC894에서 BOOT는 부팅과 메뉴 복귀에 성공했고 BLOCK은 검은 화면에 머물렀다. MMC895는 같은 FPGA와 65816을 사용한다. 이번에는 ARM이 FPGA에서 첫 입력 블록의 길이와 상태 응답을 확인한 직후 STOP한다.

1. 전원을 끄고 ZIP의 `MMC895-FIRST-INPUT-SD-ROOT` 폴더 안의 내용물을 SD 루트에 복사한다. 기존 모험도 4 `sd2snes/nes/mmc894.nes`를 같은 폴더에 `mmc895.nes`라는 이름으로 복사한다.
2. 루트의 **NES OFFER 895.nh1**을 한 번 실행한다. ROM 로딩 뒤 게임 화면을 그리기 전에 메뉴로 돌아오는 것이 정상이다.
3. 메뉴 복귀 여부와 `sd2snes/nes-progress-mmc895.txt`, `nes-budget-mmc895.txt`, `nes-game-last-mmc895.txt` 중 생성된 파일을 전달한다. 검은 화면이 계속되면 전원을 껐다 켜고 남은 로그를 보관한다. 같은 판을 다시 실행하면 진행 파일이 덮어써진다.

## 결과 판독

OFFER 성공은 `PROBE_STOPPED bytes=4 total=0`으로 확인한다. 실행 통계에서 첫 E0는 한 번, D0는 한 번 이상이고 D1·D2는 0이어야 한다. 유효한 D0가 올 때까지 조회하므로 D0 수는 보드마다 달라질 수 있다. 메뉴 복귀만으로 성공을 판정하지 않는다. STOP 뒤에 기록된 오류 코드와 budget을 함께 본다.

다른 종료점은 같은 펌웨어의 `NES-DIAG`에 있다. 이번 실기에서는 OFFER 하나만 실행한다.

| 이름 | 검사 완료 뒤 STOP하는 지점 |
|---|---|
| BOOT | 65816 stage 3 |
| INIT | 작업 메모리 초기화와 최초 런타임 E0 응답 검사 |
| OFFER | CRC가 맞고 데이터 준비 비트와 길이 1–256B가 유효한 첫 D0 |
| DATA | 실제 D1 데이터 CRC와 첫 블록 해석, D2 전 |
| BLOCK | D2 뒤 D0에서 다음 토큰 확인 |
