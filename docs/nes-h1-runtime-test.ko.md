# H1 038: 자동 메뉴 복귀 사유 확인

037에서 화면1 뒤 자동 메뉴 복귀가 보고됐다. 이 묶음은 원인 식별용이며 화면 순환 결함이
해결되었다는 수정본이 아니다. MCU에 종료 기록만 추가하며 FPGA036과 화면 프로그램034는 그대로다.

## 적용

콘솔 전원을 끄고 SD를 PC에 연결한다. 기존 037에서 실행하던 SD를 사용한다.
직접 복사할 때는 먼저 SD의 sd2snes/firmware.stm을 PC의 별도 폴더에 백업한 뒤,
이 묶음의 sd-overlay/sd2snes/firmware.stm을 SD의 sd2snes/firmware.stm으로 교체한다.
기존 fpga_nh1.bi3와 NES H1 037.nh1, GBC/base 이미지·세이브는 그대로 둔다.
이번에는 .nh1을 새로 만들거나 이름·확장자를 바꾸지 않는다. sd-overlay 폴더 자체를 복사하지 않는다.
설치 전 기존 펌웨어/FPGA 해시는 manifest.json의 baseline을 참고한다.

해시 검사와 자동 백업·복원을 사용하려면 Python3.11 이상에서 실행한다.
E:/는 실제 SD 루트, C:/NES-H1-038-backup은 아직 없는 PC 백업 폴더로 바꾼다.

    python manage_nes_h1_runtime_sd.py check --sd-root E:/
    python manage_nes_h1_runtime_sd.py install --sd-root E:/ --backup C:/NES-H1-038-backup

도구는035 MCU/036 FPGA/C44 GBC,기본 이미지와 STM32 메뉴 m3nu.bin을 확인한다.
MCU 한 파일만 교체하며 SD 밖의 백업을 먼저 검증한다. 실제 SD에는 자동 접근하지 않는다.
안전 제거 후 SD를 콘솔로 옮기고 전원을 완전히 껐다 켠다.

## 한 번 재현한 뒤 기록 확인

1. 기존 NES H1 037.nh1을 실행한다. 화면 제목은 NES H1 034가 맞다.
2. RESET을 누르지 말고 자동 메뉴 복귀를 기다린다. 순환하면 약10초 뒤 직접 RESET으로 돌아온다.
3. 메뉴 복귀가 완료된 다음 전원을 끄고 SD의 **sd2snes/nes-h1-last-038.txt**를 확인한다.
   이 텍스트 전체를 전달하면 된다. 새 H1 영상은 이전 영상과 다른 파일명으로 보관한다.

exit_reason=F2_STATUS이면 last_status_hex가 FPGA 상태 응답이다. 07이면
RUN/LOCK은 유지된 채 통합 오류 bit가 켜진 경우다. 하위 bus/frontend/producer 원인은 아직 구분되지 않는다.
RESET_ASSERTED이면 MCU가 실제 RESET 입력의 asserted 값을 읽은 경우다. 사용자가 버튼을 눌렀다는 뜻은 아니다.
START_ERROR는 초기 설정/식별/ARM 단계 실패, SPI_IO는 거래 함수 실패다.
elapsed_ticks_10ms는 설정 시작부터 종료 감지까지의 시간(10ms 단위)이며 아날로그 계측값이 아니다.
base_restored=1은 기록 전에 기본 FPGA token까지 검증했다는 뜻이다.

기록은 H1 STOP·GPIO/SPI 복원·기본 FPGA 확인 후 RESET 유지 상태에서 작성하고 파일을 닫는다.
기록 실패는 메뉴 복구를 막지 않는다. 설정/기본 FPGA 복구가 panic에 빠지면 새 파일이 없을 수 있다.
파일이 없으면 파일 없음 자체를 알려주면 된다. 재시험 전 이전 로그를 PC로 옮겨 오래된 기록과 구분한다.
게임이나 세이브에는 쓰지 않는다.

## 되돌리기

직접 복사했다면 전원을 끄고 PC에 백업한035 firmware.stm을 원래 위치에 복원한다.
자동 도구를 썼다면 다음을 실행한다.

    python manage_nes_h1_runtime_sd.py restore --sd-root E:/ --backup C:/NES-H1-038-backup

진단 로그는 증거로 남긴다. 완전한 C44 복원은 먼저038→037(035 MCU)로 돌아온 뒤 기존037 백업/복원 절차를 따른다.
