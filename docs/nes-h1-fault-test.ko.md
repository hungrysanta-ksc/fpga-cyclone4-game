# H1 039: 최초 FPGA 오류 확인

038 사용자 로그는 F2_STATUS/07, start=0, stop=0, base_restored=1이었다.
MCU가 RESET이 아니라 FPGA 오류 응답을 받아 복귀한 경우다. 아직 하위 원인 수정본은 아니다.
039는 최초 오류를 보존하는 FPGA와 그 기록을 읽는 MCU를 함께 제공한다.

## 적용: 두 파일을 함께 교체

콘솔 전원을 끄고 현재038 SD를 PC에 연결한다. 기존 sd2snes/firmware.stm과
sd2snes/fpga_nh1.bi3 두 파일을 먼저 PC의 별도 폴더에 백업한다.
패키지의 sd-overlay/sd2snes 안에 있는 동일한 두 파일을 SD의 sd2snes 폴더에 덮어쓴다.
sd-overlay 폴더 자체를 복사하지 않는다. 둘 중 하나만 교체하지 않는다.
기존 NES H1 037.nh1은 그대로 실행한다. 확장자·표식 이름·게임·GBC/base·세이브는 바꾸지 않는다.
화면 제목은 NES H1 034로 유지된다. 프로토콜은39로 바뀌어 기존34 FPGA와의 혼합은 초기 진입에서 거부한다.

자동 해시 검사·백업·복원 도구(Python3.11 이상)를 쓰려면 다음과 같이 실행한다.
E:/는 실제 SD 루트, C:/NES-H1-039-backup은 SD 밖의 새 백업 폴더로 바꾼다.

    python manage_nes_h1_fault_sd.py check --sd-root E:/
    python manage_nes_h1_fault_sd.py install --sd-root E:/ --backup C:/NES-H1-039-backup

현재038 MCU/036 FPGA/C44 GBC를 확인한 뒤 두 원본을 백업한다.
두 파일 교체 도중 중단되면 콘솔을 켜기 전에 아래 restore를 한다.

## 한 번 재현

1. 안전 제거 후 전원을 완전히 껐다 켜고 기존 NES H1 037.nh1을 실행한다.
2. RESET을 누르지 않고 자동 메뉴 복귀를 기다린다. 순환하면 약10초 뒤 직접 RESET으로 돌아온다.
3. 메뉴 복귀 후 전원을 끄고 SD의 **sd2snes/nes-h1-last-039.txt** 전체를 전달한다.
   038 로그 파일은 새 파일이 아니다. 이번에는 이름 끝이039인 파일을 확인한다.

이번 로그의 detail_hex는 식별/프로토콜/상태 재확인과 최초 오류 코드를 포함한다.
버스 처리부·전송부·패턴 생성부 중 어느 오류인지 구분하며, 첫 오류 이후 값이 바뀌어도 최초 기록을 유지한다.
주소/제어 신호는 오류를 처음 관측한 클록의 값이다. 원래 오류를 일으킨 버스 사이클의 정확한 주소라고 단정하지 않는다.
43개의10ms tick 같은 경과시간에는 FPGA 설정 시간이 포함된다. polls도 정확한 밀리초값이 아니다.
기록은 SNES RESET 유지→스냅샷 읽기→STOP→기본 FPGA 검증 후 작성된다. 오류 판정/복귀 동작은 유지한다.
기본 FPGA 복원 실패나 SD 기록 실패라면 새 파일이 없을 수 있다. 파일 없음도 결과로 알려주면 된다.
재시험 전 이전039 로그를 PC로 옮겨 오래된 기록과 혼동하지 않는다.

## 복원

직접 설치했다면 PC에 백업한038 firmware.stm과036 fpga_nh1.bi3 둘 다 복원한다.
자동 도구를 썼다면 다음을 실행한다.

    python manage_nes_h1_fault_sd.py restore --sd-root E:/ --backup C:/NES-H1-039-backup

복원 후에도 진단 텍스트는 보존한다. 전체 C44로 돌아가려면039→038→037→C44 순서로 각 단계 백업을 사용한다.
이번 묶음은 실제 보드의 오류 원인을 수집하는 진단 후보이며 전기 타이밍 signoff나 NES 게임 지원 완료가 아니다.
