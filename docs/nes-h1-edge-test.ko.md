# NES H1 041 — 최초 frontend 오류 원인 계측

040 실기에서도 화면이 완성되기 전에 자동 복귀했다. 이전 수정만으로 해결되지 않았으며,
이번041은 오류 조건·그 순간의 주소/상태·읽기 길이를 수집하는 진단 후보다.
040 읽기 종료 수정은 유지하고 오류를 무시하거나 종료 경로를 완화하지 않는다.

## 직접 설치

1. 콘솔 전원을 끄고 SD의 **sd2snes/firmware.stm**과 **sd2snes/fpga_nh1.bi3**를 PC의 새 백업 폴더에 복사한다.
2. 이 묶음의 **sd-overlay/sd2snes/** 안에 있는 위 두 파일을 SD의 **sd2snes/**에 덮어쓴다.
   **이번에는 두 파일 모두 교체**한다. sd-overlay 폴더 자체를 SD에 넣지 않는다.
   fpga_base.bi3, fpga_egbc.bi3, m3nu.bin, 게임·세이브는 그대로 둔다.
3. 안전 제거 후 콘솔 전원을 완전히 껐다 켜고 기존 **NES H1 037.nh1**을 실행한다.
   확장자는 바꾸지 않는다. 화면 제목 **NES H1 034**도 그대로다.
4. RESET을 누르지 않고 증상을 한 번 재현한다. 순환한다면 약10초 뒤 RESET으로 메뉴에 돌아온다.
5. 메뉴 복귀 후 전원을 끄고 **sd2snes/nes-h1-last-041.txt** 전체를 전달한다.
   **이번에는039가 아닌041 로그**다. 새 파일이 없거나 이전보다 빨리 종료되면 그 상태도 알려준다.

프로토콜은0x41이다. MCU041은 이전0x39 FPGA와의 혼합을 초기 진입에서 거부하며,
start_result/식별·프로토콜 기록으로 잘못된 쌍을 구분한다. 새 MCU 로그의 candidate는 NES-H1-EDGE-041이다.
로그는 기존14바이트 기록에 최초 frontend 원인16바이트를 추가한다.
각 조건은 오류를 설정하는 바로 그 클록에서 기록한다. 계측값은84MHz 디지털 샘플이며 물리 파형 측정치는 아니다.

파일 확인(SHA-256):

- 새041 firmware.stm: `ad88de3ad14bb192de7cd6e74150bca3ca09507d803d315edcb4359b30b7143a`
- 새041 fpga_nh1.bi3: `b6c7d930a8fb618f1a1ae27724faf1b177c3407526601c8b465cb82472e1453f`
- 기존039 firmware.stm: `57199290c967ac7fa43cc0818467e6b2a395e64e03aef0bd0c587db4d3f1a8b8`
- 기존040 fpga_nh1.bi3: `093695235a041e5171b42efc985557d14a78138b96598f13f9721042b28027fd`

## 자동 검사·백업·복원 (선택)

Python3.11 이상에서 묶음 폴더를 기준으로 실행한다. E:/는 실제 SD, 백업 경로는 SD 밖의 새 폴더로 바꾼다.

    python manage_nes_h1_edge_sd.py check --sd-root E:/
    python manage_nes_h1_edge_sd.py install --sd-root E:/ --backup C:/NES-H1-041-backup

현재039 MCU와040 FPGA 및 C44 GBC를 확인하고 두 원본을 백업한 뒤 FPGA→MCU 순으로 설치한다.
알 수 없는 파일은 덮어쓰지 않는다. 복사 도중 중단되면 콘솔을 켜기 전에 다음으로 복원한다.

    python manage_nes_h1_edge_sd.py restore --sd-root E:/ --backup C:/NES-H1-041-backup

직접 복사했다면 이번에 백업한 두 파일을 모두 되돌린다. 로그는 별도로 보존한다.
전체 C44 복구는 기존 단계별 백업을 사용한다.

정상 기대 화면은 LINK SCREEN1→2→3→1,격자/막대/십자가 약1초마다 바뀌는 모습이다.
reference-034.png는 변경 없는 ROM의 실제034 에뮬레이터 캡처다. 이번에 새로 실행한 에뮬레이터 결과가 아니다.
이 묶음은 실기 원인 계측용이며 NES 게임 지원 완료나 외부 전기 타이밍 검증을 뜻하지 않는다.
