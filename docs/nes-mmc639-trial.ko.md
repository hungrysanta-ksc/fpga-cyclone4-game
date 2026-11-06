# MMC639 실기 설치 및 확인

1. MMC613을 시험한 FXPAK Pro / Mk.III에서 사용하세요. ZIP의 `01-MMC639-SD-ROOT` 폴더 **안의 내용**을 SD 카드 최상위에 복사하세요. `NES MMC3 639.nh1`이 SD 최상위에, `firmware.stm`과 `fpga_mmc639.bi3`가 `sd2snes` 폴더에 있어야 합니다. 함께 들어 있는 `fpga_base.bi3`와 `m3nu.bin`은 게임 종료 후 메뉴로 돌아갈 때 씁니다. RESTORE 묶음은 제외했습니다.
2. 기존 SMB3(J) 파일 `sd2snes/nes/mmc613.nes`를 같은 폴더에 **`mmc639.nes`로 복사**하세요. ROM 내용은 그대로 사용하며 비교 ROM의 CRC32는 `5a04eed7`입니다.
3. 메뉴에서 **NES MMC3 639.nh1**을 실행하세요. MMC613과 비슷한 동선으로 첫 레벨을 플레이하고 약 60초 뒤 메뉴 복귀를 확인하세요. 비교 구간은 **5–40초 / 40–55초**입니다.
4. 종료 뒤 SD의 `sd2snes` 폴더에서 아래 새 로그 세 개를 보내주세요. 실행에 실패하면 재시도 전에 그 실행의 로그를 별도로 복사해 주세요.

- `nes-progress-mmc639.txt`
- `nes-budget-mmc639.txt`
- `nes-game-last-mmc639.txt`
