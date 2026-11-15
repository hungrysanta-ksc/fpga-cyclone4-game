# MMC798 · MMC799 NES 재시험

MMC796에서 일반 SNES와 eGBC의 실행·메뉴 복귀가 실기로 확인됐다. NES는 seq 0–79를 기록하고 232.090초의 DISPLAY_NEXT에서 SD 기록이 끝났다. 콘솔 리셋으로 메뉴를 복구하지 못했고 전원을 껐다 켠 뒤에는 메뉴가 정상적으로 떴다. 마지막 레코드는 393,216바이트 적재와 읽기 검사를 마친 위치다. START 응답과 첫 화면은 이 파일에 기록되지 않는다.

이번 판은 실기에서 SMB3를 플레이했던 MMC763(60초)·764(장시간)의 ARM 게임 처리와 각 판의 NES FPGA·65816을 다시 짝지었다. 공용 펌웨어에는 PR160의 8MiB eGBC 로더와 MMC796의 RESET 입력 확인을 적용했다. 속도 비교는 NES 첫 화면과 메뉴 복귀가 확인된 뒤 진행한다.

## 먼저 MMC798 일반 실행 한 번

1. 전원을 끄고 ZIP에서 **01-MMC798-60SEC-SD-ROOT 폴더 안의 내용 전체**를 기존 SD 루트에 덮어쓴다.
2. 이전 시험에 쓴 SMB3(J) 파일을 `sd2snes/nes/mmc798.nes`로 복사한다. 메뉴에서 루트의 **NES MMC3 798.nh1**을 고른다.
3. 적재·검사에 약 3분 52초가 걸린다. 게임이 뜨면 평소처럼 플레이해 60초 뒤 메뉴가 돌아오는지 확인한다. 화면과 메뉴 모두 뜨지 않으면 선택 후 약 6분에 전원을 껐다 켜고, 다음 실행 전에 SD의 `sd2snes/nes-progress-mmc798.txt`와 생성된 `nes-game-last-mmc798.txt`, `nes-budget-mmc798.txt`를 복사한다.

## 일반 실행에서 다시 암전될 때

같은 설치본·같은 ROM을 그대로 사용한다. 각 진단도 ROM 전체를 검사하며 **게임 화면 없이 메뉴로 돌아오는 것이 정상**이다. 각 실행 뒤 로그를 따로 보관한다. 파일명은 같은 판을 실행할 때마다 재사용한다.

| 메뉴의 NES-DIAG 폴더에서 선택 | 확인하는 경계 | 정상 SD 진행 레코드 |
|---|---|---|
| 먼저 **NES BOOT 798.nh1** | START, RESET 해제, 65816 WRAM 준비 응답을 확인한 뒤 프레임 실행 전에 STOP | `stage=PROBE_STOPPED bytes=2 total=0` 뒤 `MENU_PREPARED` |
| BOOT도 메뉴로 돌아오지 않을 때 **NES START 798.nh1** | SNES를 RESET 상태로 둔 채 START 수락을 확인하고 즉시 STOP | `stage=PROBE_STOPPED bytes=1 total=0` 뒤 `MENU_PREPARED` |

PROBE_STOPPED에서 bytes는 선택한 진단 번호, total은 첫 오류 코드다. 두 항목 모두 STOP 응답·상태·보존된 관측값을 확인한 뒤 SD에 기록한다. BOOT의 total=6은 65816 준비 검사 실패, 9는 RESET 해제 단계 실패다. 끝까지 확인하지 못하면 마지막으로 남은 레코드와 메뉴 복귀 여부를 사용한다. RUN 도중 SD에 쓰지 않는다.

## 장시간판

MMC798에서 NES 실행과 메뉴 복귀를 확인한 뒤 같은 방법으로 **02-MMC799-LONG-SD-ROOT**를 설치한다. ROM은 `sd2snes/nes/mmc799.nes`, 실행 항목은 **NES MMC3 799.nh1**이다. L + R + Start + Select를 함께 길게 눌러 종료한다. 로그 세 종류와 선택 진단도 번호 799를 사용한다.
