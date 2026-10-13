# NES168 — 최초 실패 SNES 응답을 보존하는 실기 시험판

PR109를 머지한 master에서 `codex/nes-sink-response-168`을 시작했다.167 실기에서는 BEGIN/END/COMMIT8회·ABORT0회, 표시 ACK7회 뒤 `native_result5/sink_error3`으로 종료했다. 이번 변경은 그 검사에서 잃었던 요청·응답을 남기는 최소 MCU 보강이다. **게임 화면 갱신 오류의 수정 완료를 주장하지 않는다.**

## 변경 경계

배포167 MCU 소스1408개를 해시 확인해 복제하고5파일만 수정,2파일을 추가한다. sink 검사, 진단 로그/초기화, 빌드 목록과168 경로·버전이 대상이다. 최초 실패 요청 헤더16바이트와 ACK12바이트, 유효성·항목 마스크를32바이트 전역 상태에 복사한다. RUN 버퍼 해제 뒤에도 남고 다음 실행 또는 sink reset에서 지운다. 재진입·재시도로 증거를 덮어쓰지 않는다. 실패 후 기존 fail-stop은 유지한다.

원래 ACK 조건과 새 항목 마스크는 같은 수락/거절 결과를 낸다. 마스크 bit0=status, bit1=op, bit2=sequence, bit3=serial, bit4=generation, bit5=signature다. `ack_valid=0`이면 exchange가 성공하지 않은 것이므로 zero ACK를 실제 응답으로 해석하지 않는다. `ack_valid=1`이면 F6/CRC/상태 검사를 통과해 얻은 ACK다. request hex는 op·section·sequence16LE·serial32LE·generation16LE·offset16LE·length16LE·reserved16LE 순서다.

SNES가 반환하는 E0는 패킷 검증, E1는 비교 입력, E2는32개 DMA 명령 상한, E3는 전송 예산, E4는 STOP이다.167 실기에서 어떤 값을 받았는지는168 결과 전까지 미확정이다. MCU 전송 실패·만료 등은 기존 native_result와 함께 판정한다. status 오류만 있어도 무조건 E2/E3로 추정하지 않는다.

## 검증

- 세 명령의12개 ACK 바이트 각각256값, 총9216조건에서 기존 수락/거절과 동일하다. BEGIN/DATA/SEAL 각각 E0~E4와 exchange 실패18조건에서 첫 실패·재시도 차단·초기화를 확인했다. 형식 출력169바이트의 경계/실패 무쓰기 검사도 통과했다.
- 변경 MCU receiver/runtime/sink를 함께 실행해 기존10조건(정상, deadline, guard/IO/ACK 오류, idle/stalled tick)을 통과했다. native 입력은 이전 RTL SPI 캡처이며 새 FPGA 부팅 시험은 아니다.
- 실제65816 SNES 클라이언트와 변경 C sink를 연결해 정상3프레임 다음에 별도로34개 떨어진 map 변경(E2), 예산1의 변경(E3)을 만들었다. 각180개 실제 ACK,3프레임183552픽셀을 기존 두 SMB3 기준 장면과 대조했다. E2/E3 원문과 status-only 마스크01이 남고 실패 장면은 표시 완료로 처리되지 않았다. 이 파일 mailbox 모델은 물리 SPI·167 실제 장면 재현·속도 증거가 아니다.
- 전체 ARM 링크197308바이트, 정적RAM26552. RUN37320+보수적IRQ508 뒤 여유1044바이트다.13개 라이브러리/IRQ 몸체의 명령·피연산자를 심볼 기반 재배치만 허용해 대조하고 호출 그래프를 다시 검사했다. 새 trace32바이트를 포함한 계산이며 실측 최고 스택 사용량은 아니다.
- 실제 생성된 C 보고서 포맷터에 숫자형 최댓값,16개 모든 버튼 항목,16개 PPU 이력, 가장 긴 메뉴 문자열을 넣어3966/4096바이트를 확인했다. 새 원문 때문에 로그가 통째로 누락되지 않는다. save_report4864 스택은 유지되고 formatter16은 RUN 밖에서만 호출된다.
-167 ZIP의 FPGA·SNES·ROM·메뉴·164 복원 파일을 바이트 그대로 재사용했다. FPGA 합성/FIT/Questa를 반복하지 않았다. RUN 중 SD 쓰기와 별도 세이브 SRAM 사용은 없다. 기존 조건부 IO·리셋 한계와 실기 품질 미완료도 그대로다.

## 재현·실패 기록·인계

`tools/nes_sink_trace168.py --prior <검증된167 arm01> --out <새 폴더>`는 입력 펌웨어/소스를 확인해168을 생성한다. 기존 `build_nes_game149_arm.ps1`과 고정 mini로 링크한다. `tools/check_nes_sink168_arm.py`는167 armcheck03과 실제 ELF를 비교하고 `check_nes_runlease165.py`의 RUN/IRQ 검사를 재사용한다. 한글 경로의 objdump 헤더 인코딩을 피하도록 상대 ARM 경로를 사용한다. `test_nes_sink168.py`의 출력은 Lua 파일 접근을 위해 새 ASCII 경로를 사용한다. `test_nes_sink168_report.py`는 실제 생성된 포맷터를 검사한다. `release_nes_sink168.py`는 이 결과와167 ZIP을 묶고 전체 파일/해시를 다시 읽는다.

선택 결과는 arm02/armcheck01/test02/report01/release01이다. arm01은 ARM GCC 배열 인자 선언 경고로 실패해 그대로 보존했다. PC test01은4프레임 파일 왕복이 기존60초 도구 제한을 넘어서 종료됐다. test02는 PC 에뮬레이터 도구 제한만180초로 늘렸으며 실기60초는 동일하다. release 사전 검사에서 host 생성 C의 CRLF 차이를 확인했고 CRLF→LF 이외 차이는 허용하지 않는다. 실행된 두 바이트 해시는 모두 보존했다. 이전 완료 archive/record/audit는 수정하지 않는다.

NES GAME 168.nh1로 실행 후 두 TXT를 받는다. 먼저 버튼을 누르지 않아도 되고 같은 짧은 화면이면 영상은 불필요하다. ack_valid1/mismatch01이면 ACK status E0~E4를 해석하고 실제 실패 op·길이·순번·세대로 경로를 한정한다. E2/E3라면 해당 장면의 변경 범위/명령 수·전송 예산을 재현하고 한도를 해제하지 않은 유한 분할·표시 완료 처리로 수정한다. token/signature 불일치면 패킷/ACK 소유권·snapshot을 먼저 고친다. ack_valid0이면 하위 통신/guard 종료를 분석한다. 수정 후 곧바로 SMB3 실기, 이후 AV→장기 플레이/오류·리셋 로그→입력 유지 순서. 같은167/044·무변경 FPGA FIT는 반복하지 않는다.

[168 설치 안내](nes-game168-ready.ko.md) · [검증·해시](../analysis/sink168-verification.json) · [167 실기 결과](nes-game167-hardware01.ko.md). 실기 ZIP/ROM은 비공개 로컬 산출물이다.
