# NES H1 040 — 정상 읽기 종료 오검출 수정

039 실기 기록의 frontend=1을 근거로 정상 읽기 종료를 오류로 잡는 RTL 결함을 재현·수정했다.
이 묶음은 **FPGA 파일 하나만 교체**한다. 현재039 firmware.stm은 그대로 필요하다.
실기 해결 여부는 아래 화면 순환 시험으로 확인한다.

## 직접 복사

1. 콘솔 전원을 끄고 SD의 기존 **sd2snes/fpga_nh1.bi3**를 PC의 새 백업 폴더로 복사한다.
2. 이 묶음의 **sd-overlay/sd2snes/fpga_nh1.bi3**를 SD의 **sd2snes/fpga_nh1.bi3**에 덮어쓴다.
   sd-overlay 폴더 자체를 SD에 넣지 않는다. firmware.stm, fpga_base.bi3, fpga_egbc.bi3, m3nu.bin은 그대로 둔다.
3. 이전 **sd2snes/nes-h1-last-039.txt**는 PC로 옮겨 보존한다. 새 실행 기록과 구분하기 위해서다.
4. 안전 제거 후 콘솔 전원을 완전히 껐다 켜고, 기존 **NES H1 037.nh1**을 실행한다.
   확장자를 바꾸지 않는다. 화면 제목 **NES H1 034**도 기존과 같다.

파일 확인(SHA-256):

- 교체할040 FPGA: `093695235a041e5171b42efc985557d14a78138b96598f13f9721042b28027fd` (165,212바이트)
- 유지할039 MCU: `57199290c967ac7fa43cc0818467e6b2a395e64e03aef0bd0c587db4d3f1a8b8`
- 복원용039 FPGA: `7d12e8126cbe137b12a81345e537c74a707bd0cfa200149ae7a27379e310c056`

## 확인할 동작

LINK SCREEN 1 → 2 → 3 → 1이 약1초 간격으로 바뀌는지 먼저10초 정도 본다.
격자/막대/십자 무늬가 서로 구분되어야 한다. ZIP의 reference-034.png는 변경 없는 ROM의 실제034 에뮬레이터 실행에서 얻은 기준 화면이다.
정상 순환하면 RESET으로 메뉴에 돌아온 뒤 다시 실행하고, 기존 GBC 게임도 다시 실행되는지 확인한다.

자동 복귀하거나 화면1에 멈추면 그 상태 그대로 결과를 알려준다. 메뉴로 돌아왔을 때 SD의
**sd2snes/nes-h1-last-039.txt**를 전달한다. MCU를 유지하므로 **040 로그 파일은 생기지 않는다**.
파일 내부 candidate=NES-H1-FAULT-039도 정상이다. 이것은 MCU 식별자이며, FPGA040 적용 여부는 위 파일 해시로 확인한다.
정상 순환 후 RESET으로 돌아와도 새 로그를 함께 전달하면 종료 경로를 확인할 수 있다.
새 로그가 없으면 그 사실도 결과로 기록한다.

## 자동 검사·백업·복원 (선택)

Python3.11 이상에서 묶음 폴더를 기준으로 실행한다. E:/는 실제 SD, 백업 경로는 SD 밖의 새 폴더로 바꾼다.

    python manage_nes_h1_release_sd.py check --sd-root E:/
    python manage_nes_h1_release_sd.py install --sd-root E:/ --backup C:/NES-H1-040-backup

현재039 MCU/FPGA와 C44 GBC를 확인한 뒤 FPGA 원본만 백업·교체한다.
중단이나 복원이 필요하면 다음 명령을 실행한다.

    python manage_nes_h1_release_sd.py restore --sd-root E:/ --backup C:/NES-H1-040-backup

직접 복사했다면 이번에 백업한039 fpga_nh1.bi3 하나를 되돌린다. 진단 로그는 보존한다.
전체 C44 복구는 기존039→038→037→C44 각 단계 백업을 사용한다.

이 시험은 H1 전달 경로 진단이다. NES 게임 코어 완료나 보드 외부 전기 타이밍 검증을 뜻하지 않는다.
