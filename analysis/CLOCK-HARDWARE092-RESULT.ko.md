# CLOCKREPORT090 실기 결과092

## 작업 목표

사용자가 전달한 HW090000.TXT·최종 화면·복원 성공 보고를 대조해, RESET 유지 중 기준 클록 관측과 보고서 왕복의 실제 결과를 확인한다. PR42는 확인 시점에 미병합이어서 같은 PR에 회수 결과를 이어 기록한다.

## 작업 내용

CLOCKREPORT090 실기 회수092: HW090000.TXT1099바이트에서 두 연속 구간2/3의 count가1342354로 같고 VALID/LIVE=1, LAST_GAP=0이다. 사진의 동일파일/저장·재읽기성공/코드0 및 사용자 복원성공을 확인했다. 이번 보드·실행의 RESET-held 기준클록 활동과 관측·저장·표시 왕복은PASS다. 절대주파수/CF86외부보호/게임실행 승인은 별도다.

| 항목 | 결과 |
| --- | --- |
| 원본 TXT |1099바이트, SHA `5ba647a785c5c35b82ae0acc09f08498b6d30c47277239d118d43e41c7cd29de`|
| 관측 구간 |순번2와3, 각각 count1342354 / window8000000 / divisor16|
| 두 구간 flags |0x07: VALID1·LIVE1·EVER_GAP1·LAST_GAP0|
| 펌웨어 시간/시도 |301tick(100Hz 기준 약3.01초),172회,345 SPI프레임|
| 사진 |CLOCKREPORT090 CF87 / CLOCK ACTIVE / 동일HW090000.TXT / TXT SAVED + READBACK OK / Save code0|
| 복원 |사용자가 직접 성공 확인. 이번 메시지에 없는 별도 menu/GBC 재실행을 주장하지 않음; 기존084 PASS는 유지|

`EVER_GAP=1`은 시작부터 누적한 sticky bit다. RTL은 age127/live0로 시작해 동기화가 채워지기 전 이 bit를 세우며, initial0의 flags06과도 일치한다. 판정에 사용한 두 완성 구간은 `LAST_GAP=0`으로 중단 표시가 없다. 이를 현재 실패로 해석하지 않는다. 모든 짧은 고장이나 영구적 가용성을 보장한다는 뜻도 아니다.

## 작업 결과

**이번 실기 관측·저장·표시·사용자 복원 확인 목표는 달성했다.** CF87/MCU 관측과 mini 복귀·실제 SD 보고서 왕복이 이번 기기에서 동작했다. 기준 클록은 이 RESET-held 관측 구간에서 활동했다. 관측 소스가독립고장에도유지되는지,CLKIN절대주파수,비동기clear전파/외부IO/common-cause와CF86/전체NES/SMB3는 아직 미완료다.

기존 검사 도구는 `[0-9A-F]`만 허용해 실제 소문자 `7a/7b`를 거부했다. 고정090 ARM의 printf.c는 x/X 모두 소문자 hexdigits를 사용한다. 펌웨어/원본TXT를 바꾸지 않고 새 `check_nes_clock_report092.py`에서 두 대소문자를 허용했다. 원본·대문자·소문자3경우의 raw/decoded가 같고 count/raw/result/비16진수4변조는 거부했다. 첫090 검사 실패 로그와 원본사진/TXT는 private 근거에 보존했다. 기존044–091 동결파일/검사/패키지/firmware는 변경하지 않았다.

다음은 확보한 기준클록 가용성 근거를 반영해 CF86의 외부메모리/async assertion/common-cause 조건과 최신MCU·전체SPI·쌍이미지 범위를 좁히는 작업이다. 추가 저장/클록 동일시험·부품/LED/분해/PCUSB/복원 재질문은 필요하지 않다. 첫 게임 목표 SMB3(J)/mapper4/PRG256KiB+CHR128KiB는 유지한다. 새빌드/RTL/Questa/실기패키지 제작은 이번에 하지 않았다.

전체NES 준비도4완료/7부분/1미완료는 별도 범위로 유지한다. [메타데이터](clock-hardware092-verification.json), [첫 게임 계획](../docs/development/NES-GAME-COMPATIBILITY.ko.md). 새동결15파일 manifest `2b0854934f97256d330bc90c80b91732ce92e886cab5be3cd468695bb7a17641`. 완료finalizer재실행 금지.
