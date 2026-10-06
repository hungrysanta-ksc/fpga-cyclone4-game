# NES H1 044 — 입력 샘플링 수정 실기 시험

041에서 자동으로 메뉴로 돌아온 증상을 재검증하는 시험판이다. 입력 샘플링과
오류 기록을 개선했지만, 실제 보드에서 해결됐는지는 아직 확인하지 않았다.
정상/오류 회귀와 제한된 입력 해소 모델은 통과했으며, 원래 지연 모델의
불확정값 실패와 외부 전기 타이밍 미측정은 남아 있다.

## 설치와 확인

1. 콘솔 전원을 끄고 SD의 **sd2snes/firmware.stm**, **sd2snes/fpga_nh1.bi3**를
   PC의 새 백업 폴더에 복사한다. 아래 기존041 해시와 맞는지 확인한다.
   다르면 알 수 없는 파일 위에 덮어쓰지 말고 현재 파일을 먼저 확인한다.
2. 묶음의 **sd-overlay/sd2snes/**에 있는 두 파일을 SD의 **sd2snes/**에 복사한다.
   **firmware.stm과 fpga_nh1.bi3를 모두 교체**하고 복사한 파일의044 해시를 확인한다.
   sd-overlay 폴더 자체를 SD에 넣지 않는다.
3. SD를 안전 제거하고 전원을 완전히 껐다 켠 뒤 기존 **NES H1 037.nh1**을 실행한다.
   확장자를 바꾸지 않는다. 화면 제목 **NES H1 034**도 유지된다.
4. 정상 기대는 **LINK SCREEN1 → 2 → 3 → 1** 순환이며 격자/막대/십자가가 약1초마다 바뀐다.
   약15초간 관찰한 뒤 RESET으로 메뉴 복귀, 한 번 재실행을 확인한다.
   자동으로 메뉴에 돌아오면 그 시점에서 멈추고 로그를 보존한다.
5. 메뉴 복귀 후 전원을 끄고 **sd2snes/nes-h1-last-044.txt** 전체를 전달한다.
   이전041/039 로그 대신 **044 로그**가 필요하다. 화면 순환 여부와 자동 종료 여부도 함께 기록한다.
   정상 순환·재진입이 된다면 기존 GBC 게임의 시작과 메뉴 복귀도 한 번 확인한다.

프로토콜은0x44, 로그 candidate는 **NES-H1-SAMPLING-044**다.
MCU044는 이전 FPGA와의 혼합을 초기 식별에서 거부한다.
fpga_base.bi3, fpga_egbc.bi3, m3nu.bin, 게임과 세이브는 유지한다.
`reference-034.png`는 변경 없는 ROM의 실제034 에뮬레이터 캡처이며 새 실기 영상이 아니다.

## SHA-256 확인

- 새044 firmware.stm: `1c3b40a3459d24114cb4d91ee9d861d1a08025a670ef25317ef489092203693b`
- 새044 fpga_nh1.bi3: `71ffacd82227ae68b186dd3d3fab9619a69c4cdef73b5c44c55621caff4e0888`
- 기존041 firmware.stm: `ad88de3ad14bb192de7cd6e74150bca3ca09507d803d315edcb4359b30b7143a`
- 기존041 fpga_nh1.bi3: `b6c7d930a8fb618f1a1ae27724faf1b177c3407526601c8b465cb82472e1453f`

PowerShell에서 실제 SD 경로를 넣어 `Get-FileHash E:/sd2snes/firmware.stm`처럼 확인한다.

## 자동 검사·백업·복원 (선택)

Python3.11 이상으로 묶음 폴더에서 실행한다. E:/는 실제 SD, 백업은 SD 밖의 새 폴더로 바꾼다.

    python manage_nes_h1_sampling_sd.py check --sd-root E:/
    python manage_nes_h1_sampling_sd.py install --sd-root E:/ --backup C:/NES-H1-044-backup

기존041 MCU/FPGA와 C44 GBC를 확인하고 두 파일을 백업한 뒤 FPGA→MCU 순서로 설치한다.
다른 펌웨어·변경된 복구 파일은 덮어쓰지 않는다. 복사 중 중단됐다면 전원을 켜기 전에 복원한다.

    python manage_nes_h1_sampling_sd.py restore --sd-root E:/ --backup C:/NES-H1-044-backup

직접 복사했다면 이번에 백업한 두 파일을 모두 되돌린다. 로그와 세이브는 보존한다.
이 시험은 NES 게임 지원 완료나 전기적 타이밍 검증 완료를 뜻하지 않는다.
