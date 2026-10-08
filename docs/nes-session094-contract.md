# CF86 MCU 세션 계약094

상태는 IDLE → CONFIG → ARMED → IDLE(정상 종료) 또는 FAILED다. FAILED를 지우는 공개 API는 없다. MCU 재시작 후 새 FPGA 전체 구성·새 ROM 전체 적재·CHECK를 요구한다. 고장 난 이미지에 이어 붙이는 재시도는 허용하지 않는다.

CONFIG 진입은 RESET held, USB IRQ disabled, offload/blocktrans/log permission 없음, 공유 오류 없음이 조건이다. 실제 bounded 구성/READY 대기 다음에 DONE/RDY를 확인하여 ARMED가 된다. CF86/F0/F1 검증 후 BEGIN한다.

전송 전·각 비트 시작·샘플 직전·전송 종료에 상태를 확인한다. 검출 실패는 즉시 FAILED로 간다. 취소용 CS HIGH/SCK LOW/MOSI LOW는 허용하지만 새로운 프레임, SD/FatFS, 기본 FPGA 구성, IRQ/RESET 복구는 금지한다. 정상 CHECK/FINISH/STOP 뒤의 GPIO 복구·finish에도 검사하며 실패 시 verified를 지운다.

이 검사는 폴링이다. 두 검사 사이 짧은 펄스나 실제 MCU 실행 시간이 보장되지 않는다. CF86의 sticky 메모리 무효화와 전체 프로토콜 검증을 함께 유지해야 한다. 양쪽 클록이 함께 멈출 때의 CE 제한은 해결되지 않았으며 별도 승인 조건이다. GPIO 안전 상태는 외부 PSRAM 무전원·전기 안전의 증거가 아니다.

정상 후보는 load/CHECK/STOP 진단이며 RUN을 허용하지 않는다. 비정상 후보 이후 실기 사용자는 전원을 끄고 검증된044로 복원한다. 다만094는 아직 배포 패키지가 없으므로 사용자에게 설치를 요구하지 않는다.

공개 호스트 재현: `python tools/test_nes_cf86_session094.py --gcc <gcc> --out <새 디렉터리>`. 네 대조는 `--mutation ready|latch|verify-fail|candidate`를 각각 새 출력 경로로 실행한다. ARM 준비는 `prepare_nes_session094_arm.py --baseline <동결077/arm/source> --out <새 경로>`이며 build/check 도구와 기존 환경 도구 경로를 사용한다. 077 원본은 절대 수정하지 않는다.
