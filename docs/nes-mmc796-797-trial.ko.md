# MMC796 · MMC797 NES 부팅 시험

먼저 60초판에서 SMB3의 첫 화면과 SD 메뉴 복귀를 확인한다.

| 판 | 복사할 폴더 | 기존 SMB3(J) 파일을 복사할 위치 | 메뉴에서 고를 항목 |
|---|---|---|---|
| 60초 | 01-MMC796-60SEC-SD-ROOT | sd2snes/nes/mmc796.nes | NES MMC3 796.nh1 |
| 장시간 | 02-MMC797-LONG-SD-ROOT | sd2snes/nes/mmc797.nes | NES MMC3 797.nh1 |

1. 기기 전원을 끄고 한 판의 **폴더 안 내용물 전체**를 기존 SD 루트에 덮어쓴다. 기존 게임·세이브는 그대로 사용한다. 각 판에는 공용 ARM, 메뉴·base, NES 보드와 PR160의 eGBC 보드·렌더러가 함께 들어 있다.
2. MMC763과 같은 ROM을 표의 위치와 이름으로 복사한다. 전원을 완전히 껐다 켜고 메뉴에서 해당 번호를 선택한다. MMC792 실기에서는 ROM 적재·읽기 확인에 약 3분 52초가 걸렸다. 60초 플레이 타이머는 게임 구동 후 시작한다.
3. MMC796에서 스테이지 선택과 1-1을 플레이하고 자동 메뉴 복귀를 확인한다. MMC797은 장시간 플레이한 뒤 L + R + Start + Select를 함께 길게 눌러 종료한다.
4. 메뉴 복귀 후 SD의 sd2snes 폴더에서 nes-progress-mmc796.txt, nes-game-last-mmc796.txt, nes-budget-mmc796.txt를 전달한다. 장시간판은 이름의 796이 797로 바뀐다. 진행이 멈추면 존재하는 파일만으로도 확인할 수 있다.

**암전이 지속될 때** 선택 후 약 6분이 지나도 첫 화면이나 SD 메뉴가 나오지 않으면 전원을 끄기 전에 카트리지의 READY·READ·WRITE LED 중 어떤 것이 켜져 있는지 사진 또는 글로 남긴다. ROM 검증이 끝난 뒤에는 세 LED로 다음 단계를 표시한다.

| 켜진 LED | ARM이 마지막으로 진입한 단계 |
|---|---|
| WRITE | DISPLAY_NEXT 기록 및 START 확인 |
| READ | 첫 E0 상태 확인 |
| READ + WRITE | SNES RESET 해제 확인 |
| READY | 해제 후 상태 확인 |
| READY + WRITE | 65816 프로그램의 WRAM 복사·준비 확인 |
| READY + READ | 프레임 처리 |
| 세 개 모두 | STOP 및 종료 검사 |

RUN 중에는 SD에 쓰지 않는다. 전원 차단 뒤 남은 DISPLAY_NEXT는 적재를 마쳤다는 뜻이며, 그 뒤에 어느 단계에서 멈췄는지는 LED로 구분한다. 종료 검사 뒤 LED는 원래 동작으로 돌아간다.
