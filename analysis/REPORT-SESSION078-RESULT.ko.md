# 078 — 보고서·FatFS·SD GPIO 전체 저장 세션

## 결과와 범위

계획P1의 **전체 저장/재읽기 호스트 연결**을 완료했다. 동결074 보고서 생성·쓰기 함수, 전체077 FatFS·runtime·권한 관리, 실제077 native CMD17/CMD24·데이터·CRC·응답·busy 함수를 연결했다. 기존073/074 시험의 메모리 복사식 SD 전송을 GPIO 에지 카드 모형으로 대체했다. 정상/오류116검사와 보호 제거2인과 대조가 통과했다.

이는 **077 MCU와074 보고서 소스를 결합한 호스트 시험 구성**이다. 그대로 링크한 새 ARM 펌웨어가 아니다. 생산 코드·RTL·077 펌웨어는 변경하지 않았고 새 ARM/Questa/Quartus/설치 패키지는 없다. 사용자의0바이트 TXT 원인은 미확정이다. P1 전체는 관측 구현·전체 부팅 시간 검증이 남아 부분 달성이다.

## 연결과 완료 조건

`sdinv_format → sdinv_write_report → f_open/f_write/f_sync/f_close/f_read → sdn_read/sdn_write/sdn_ioctl → cmd_fast/send_command_fast → 실제 GPIO clock helper/데이터/CRC/busy`

전체 FatFS와 보고서 함수는 동결 원본을 복사했고 native는 선언이 아닌 실제 함수 정의를 추출했다. 모델은 송신 CMD 핀에서 명령·주소를 복원하고, 쓰기 DATA 네 lane의 CRC를 직렬 비트로 독립 검사하여 섹터 매체에 반영한다. 읽기는 매체의 데이터/CRC nibble을 GPIO 입력으로 제공하며 실제 C의 수신/CRC 검사가 실행된다. 저장 후 별도의 FatFS remount로 캐시를 버리고 파일 크기·전 바이트를 다시 확인한다.

카드·GPIO·초기화 완료 상태·시간과 ARM CRC primitive의 호스트 C 대체는 모형이다. ARM CRC assembly, 실제 SysTick/인터럽트 지연·전기 타이밍·카드 전원 손실·부팅·MCU 실행은 검증하지 않았다. 읽기 데이터가 응답 뒤에 시작하는 경우를 모델링했으며 응답/데이터 중첩의 모든 위상은 이번 범위가 아니다. 소스의 inactive legacy/menu 함수에는 실행 시 실패하는 stub을 둬 시험 밖 경로 사용을 금지했다.

| 검사 | 결과 |
| --- | --- |
| 실제 formatter 출력 | 합성된 absent 입력4개의 보고서2879바이트. 원본 파일 수집기 전체를 실행한 것은 아님 |
| FAT16/FAT32 정상 세션 | 각각20 SD 명령=10읽기+10쓰기, 단계2–8, sync·close·재열기·내용 비교 통과 |
| 모형 상승 에지 | FAT16 24332 / FAT32 25483. 초기 mount 포함, 추가 cold remount 전. 실측 시간 아님 |
| 모든 명령 응답 위치 | 20×2=40 위치에서 R1 CRC 오류 전달·해당 명령 이후 재시도/추가IO 금지 |
| 모든 쓰기 종료 위치 | 10×2=20 위치에서 손상 end 거부. 카드에 이미 반영됐을 수 있는 쓰기를 되돌리거나 재시도하지 않음 |
| 모든 읽기 CRC 위치 | 10×2=20 위치에서 실제 수신 CRC 오류 전달 |
| 길이/주소/할당 | 1/511/512/513/4500/6143바이트, SDHC/SDSC 주소 모형, 짧은busy, 기존 이름 회피, 불연속 할당, 전체 remount 비교 |
| 추가 오류/예산 | 정상 CRC지만 내용 변조, WP, 명령/데이터 무응답, busy poll 상한·tick wrap, 보고서 시간 예산, tick 정지 시 FAT 할당 poll 한도 |
| 인과 대조 | 종료 비트 검사 제거는 `result==8` 오류 거부 assertion에서 실패. 내용 비교 제거는 `result==7` assertion에서 실패 |

최종116검사는 FAT별41(정상1+R1오류20+쓰기end10+읽기CRC10)=82, 길이12, FAT별 추가11×2=22다. 단계2=생성,3=쓰기,4=sync,5=쓰기close,6=재열기,7=재읽기,8=읽기close이며 close/재열기는 캐시 때문에 항상 SD 명령을 내는 것은 아니다.

## 시간·관측에서 확인한 한계

- 보고서 쓰기 허용 시 공유 예산은1000tick/10000회이며100Hz 정상 동작 가정에서10초다. 성공 모형 기본 tick은 고정이고, 별도 에지 기반 tick/wrap 모형으로 만료를 검사했다.10초는 엄밀한 전체 실행 상한이 아니라 검사 지점에서 적용하는 예산이다.
- busy는100tick/2000000poll, 명령 응답은200000회, 데이터 시작은2000000회로 제한된다. 중첩 호출이 끝나야 상위 검사로 돌아오므로 마지막 호출의 시간과 화면 대기·부팅 구간을 포함한 실기 총 상한은 아직 없다. poll 수를 시간으로 임의 환산하지 않는다.
- 실제074는 `sdinv_run` 전에 legacy `file_init`/부팅을 거친다. mini 화면을 준비한 뒤 RESET을 유지하고, shared fault에서는 `nes_diag_blocked`로 들어가 RESET을 계속 잡는다. 이는 검은 화면과 양립하지만 사용자 실패가 어느 하위 원인인지는 증명하지 않는다.
- [다음 관측 설계](../docs/nes-report-observation078-contract.ko.md)는 실패 후 SD/SPI 보호를 해제해 출력하는 대신 **실행 전 단계 표식을 보여 주고 해당 단계의 SD 작업 동안 RESET 유지**하는 방향이다. 아직 구현/ARM/실물 확인 전이다.

## 재현·보존

공개 clone만으로 private074/077 원본 플랫폼을 복원할 수 없다. 기존 두 manifest를 확인하고 읽기만 하며 새 출력 폴더를 쓴다.

```text
python tools/test_nes_report_session078.py --evidence074 <frozen074> --evidence077 <frozen077> --gcc <gcc.exe> --out <new-output> --mode normal
```

대조는 `--mode no-end`, `--mode no-readback`을 각각 새 폴더에서 실행한다. `tools/verify_nes_report_session078.py --evidence <frozen078>`는 저장된 입력·출력·공개 소스 해시를 확인한다.

최초run-01은 함수 prototype을 정의로 잘못 추출하고 smc.h를 누락하여 컴파일 실패했다. run-02는 미사용 메뉴의 CRC 링크 심벌 누락으로 실패했다. 추출 정규식과 실제 헤더/범위 밖 호출 금지 stub을 보완했다. run-03의82검사·run-04의108검사와 초기 대조도 보존했다. 최종은run-05의116검사 및 no-end-02/no-readback-02다. native의 기존 fallthrough/unused-parameter 경고는 숨기지 않았다.

동결044–077과 생산/GBC 소스는 유지한다. 다음은 단계 화면 관측의 실제 연결·예산을 확인하는 P1 잔여 작업이며, 준비도4완료/7부분/1미완료와071 설치보류를 유지한다.
