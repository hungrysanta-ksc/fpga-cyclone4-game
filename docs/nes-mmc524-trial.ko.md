# MMC524 제한 실기 시험

1. ZIP을 풀고 `01-MMC524-SD-ROOT` 안의 파일을 SD 카드 루트에 복사한다. `sd2snes/firmware.stm`은 이번 전달본으로 설치한다.
2. MMC520에서 실행했던 `sd2snes/nes/mmc520.nes`를 같은 폴더에 `mmc524.nes`로 복사한다. 동일한 SMB3(J) 원본 393,232B, CRC32 `5a04eed7`을 사용한다.
3. 메뉴에서 **NES MMC3 524.nh1**을 실행한다. 앞선 시험과 비슷하게 첫 레벨을 플레이하고, 적이 많은 장면에서의 움직임과 타일 깨짐, 입력, 약 60초 뒤 메뉴 복귀를 확인한다.
4. 다음 세 로그를 SD 카드의 `sd2snes`에서 복사한다. 여러 번 실행할 때는 회차마다 보관한다.
   - `nes-progress-mmc524.txt`
   - `nes-budget-mmc524.txt`
   - `nes-game-last-mmc524.txt`

MMC520과 같은 방식으로 1초 이상 40초 미만과 40초 이상 60초 미만을 따로 비교한다. ROM과 RESTORE는 전달본에서 제외했다. 실기 성능과 실제 메뉴 복귀는 이 시험에서 확인한다.
