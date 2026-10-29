# NROM476 설치·비교

같은 이동 ROM·같은 FPGA471을 사용하며 ARM의 CRC 계산과 필수 tag 목록 순회만 바꾼 후보이다. [검증 범위](nes-receive476-contract.ko.md). **실기 FPS는 미정**이며 비교 기준은474 평균23.59fps/정상 구간 약24fps다.

## 설치

1. 전원을 끄고 기존 SD·저장 자료를 백업한다.
2. `01-NROM476-MOVING-SD-ROOT`의 내용을 SD 루트에 덮어쓴다. firmware·`sd2snes/fpga_nrom476.bi3`·`sd2snes/nes/nrom476.nes`를 함께 복사한다.
3. **NES NROM 476.nh1**을 실행한다. FPGA와 ROM 내용은474와 같지만 새 firmware가 찾는 이름은476이다.
4. 막대 이동·A 누름의 붉은색 유지/해제 후 파랑·약60초 자동 STOP와 메뉴 복귀를 확인한다. 초기 적재/readback 시간은 RUN FPS와 별도다.
5. 가능하면 메뉴 복귀 뒤 한 번 더 실행한다. 오류·멈춤이 있으면 경과 시간·화면을 기록하고 BLOCKED_RESET_HELD를 강제로 해제하지 않는다.

## 반환할 파일

- `sd2snes/nes-progress-nrom476.txt`
- `sd2snes/nes-budget-nrom476.txt`
- `sd2snes/nes-game-last-nrom476.txt`

재실행 전에 회차별로 보관한다. 영상 동작이 이전과 같으면 TXT와 메뉴 복귀 여부만으로 우선 비교할 수 있다. 새 비용 항목은 추가하지 않았고 **cost_schema=474는 의도적으로 유지**한다. 파일명/실행 identity는476이다. phase·opcode·quiet는 중첩되므로 합산하지 않는다.

## 원복과 선택 비교

전원을 끄고 **02-RESTORE474-SD-ROOT** 내용을 SD 루트에 복사하면 직전 실기 정상474로 돌아간다. 실행 항목은 NES NROM 474.nh1이다.03은471,05는164,06은467 복원물이다. 기존 저장 파일은 전달본에 포함하지 않았다.

04-STATIC-COMPARE는 기존428 정적 ROM의 선택 비교용이다. 이동 로그를 먼저 보관하고 ROM만 덮어쓴다. 이동 장면 복원은01의 ROM만 다시 복사한다. 기본 이동 장면 CRC32는 `0fddf31c`로474와 같다. 정적14.97fps를 이번 이동 장면과 직접 비교하지 않는다.

CPU 고정 replay 명령38.91% 감소는 실기 FPS 개선율이 아니다.30/60fps·일반 NES/MMC4/5·전체 CDC/IO 승인을 미리 주장하지 않는다.
