# MMC896 · 첫 D0의 SRAM·Flash 대조

MMC895 INIT에서는 작업 메모리 초기화·첫 런타임 E0·STOP·메뉴 복귀가 성공했다. OFFER에서는 검은 화면이 지속됐다. MMC896의 두 마커는 같은 펌웨어에서 같은 8바이트 D0를 보내고 같은 응답을 검사한다. SRAM 마커는 ARM 부팅 때 초기화한 SRAM에서, FLASH 마커는 Flash에서 DMA가 그 바이트를 읽는다.

1. 전원을 끄고 ZIP의 `MMC896-OFFER-AB-SD-ROOT` **안의 내용물**을 SD 루트에 복사한다. 기존 모험도 4 `sd2snes/nes/mmc895.nes`를 같은 폴더에 `mmc896.nes`로 복사한다.
2. 전원을 켜고 **NES SRAM 896.nh1**을 한 번 실행한다. ROM 로딩이 끝난 뒤 메뉴로 자동 복귀하는지 확인한다.
3. 전원을 완전히 껐다 켜고 **NES FLASH 896.nh1**도 한 번 실행한다. 양쪽 모두 게임 화면을 그리기 전에 첫 유효한 입력 제안을 확인하고 STOP하도록 했다.
4. 각 실행의 메뉴 복귀 여부와 `sd2snes`에 생성된 `nes-progress-`, `nes-budget-`, `nes-game-last-` 로그를 전달한다. 파일명이 각각 `mmc896-sram.txt`와 `mmc896-flash.txt`로 끝나므로 두 실행 후 한꺼번에 복사해도 된다. 검은 화면이 계속되면 전원을 껐다 켠 뒤 남은 로그만 전달한다.

## 판독

| 기록 | 확인할 수 있는 것 |
|---|---|
| DISPLAY_NEXT | START 직전. bytes는 SRAM 7, FLASH 4이고 total은 ARM 스택 포인터다. |
| OFFER_STOP_OK | RESET을 건 상태에서 STOP 명령과 상태·적재 길이 응답까지 확인했다. total이 0이면 입력 진단의 앞선 검사에도 오류가 없었다. |
| PROBE_STOPPED | STOP 뒤 두 차례 관측값과 화면 상태를 검사했다. total이 0이면 진단 성공이다. |
| MENU_PREPARED | base 복구 뒤 메뉴를 준비했다. 실제 메뉴 표시 여부는 사용자가 함께 확인한다. |

첫 상태 조회 E0는 1회, D0는 제안을 기다린 횟수만큼 1회 이상, D1·D2는 0회가 정상이다. 두 마커 모두 DISPLAY_NEXT까지만 남으면 이 로그로 D0 송신·수락·STOP 도달 여부를 구분할 수 없다.
