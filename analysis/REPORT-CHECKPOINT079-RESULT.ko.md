# 079 — 저장 작업 전 단계 표시와 ARM 연결

## 달성 범위

보고서의 단계2–8마다 **문자열 쓰기·33바이트 재읽기 비교 → RESET 해제 → bounded500ms → RESET 재유지 → FatFS 작업**을 연결했다. 호스트 통합185검사, 실제077 타이머 함수5검사, 보호 제거3인과 대조와 최종 ARM 호출 검사를 통과했다. 이 범위는 달성했으나 **P1 전체는 부분 완료**다. 부팅/file_init·mini 준비의 종료 조건, 실제 화면 가독성 및 복원 패키지 판단은 남는다. 사용자의0바이트 실기 원인은 확정하지 않았다.

새 후보는 `SDREPORT079`이고 보고서 이름은 `/HW079000.TXT`부터 CREATE_NEW로 빈 이름을 찾는다. 3072바이트의 명시적인 저장 시험 데이터를 쓰며 이전에 받은 하드웨어/파일 정보를 다시 수집하지 않는다. 파일 존재만으로 성공을 판단하지 않고 sync·close·재열기·크기·전 바이트 비교를 통과해야 완료 문구로 간다.

**compile-only이며 설치용으로 전달하지 않았다.** MCU077 네이티브SD/FatFS/타이머/SPI/메모리·RESET 함수와068 RTL, 정상044/GBC 및071 쌍을 변경하지 않았다. 별도 보고서용 main/플랫폼/체크포인트를 새 ARM 후보로 결합했다. 최종 main은 보고서 전용 noreturn 경로로 들어가며 메뉴/게임을 실행하지 않는다.

## 보호와 시간

- active 진단, 보고서 쓰기 권한, mini 준비, USB IRQ 비활성, SD offload0, 블록 전송 없음, RESET LOW가 모두 필요하다. 파일을 열어 둔 단계에서도 SD 함수가 반환한 경계에서만 SRAM을 사용한다. FatFS FIL/캐시를 화면 코드가 변경하지 않는다.
- SPI write/read가 요청 길이를 반환해도 shared fault를 별도로 확인한다. 글자 비교 실패나 타이머 오류도 실패로 처리한다. 오류 뒤 단계 callback은 RESET 유지 외에 추가 SRAM·SD 작업을 하지 않는다. 첫 오류를 덮거나 권한을 다시 열지 않는다.
- 기존 보고서 예산1000tick/10000poll은 그대로다. 정상7회×500ms=명목3.5초도 같은 예산에 포함되므로 SD와 부가 처리에 남는 명목 시간은6.5초 이하다. 실측 보장이 아니다. 단계 전/문자 검증 후/RESET 재유지 후에 총예산을 검사하며 진행 중인 한 bounded 호출만큼 초과할 수 있다.
- 500ms 타이머는42000000카운트, 별도52tick/42100000poll로 종료한다. frozen tick에서도 유한 횟수로 빠져나오는 근거이며 벽시계52tick 이내 보장은 아니다. 별도의 예산 재시작·SD 타임아웃 완화는 없다.
- 준비 화면 이전 legacy `file_init`, embedded mini 프로그래밍과 `snes_bootclear` 초기 대기는 아직 이 계약 밖이다. 마지막 결과 화면도 legacy bootprint를 사용하며 shared 오류를 확인하지만 실제 화면 소비를 확인하는 ACK는 없다.

## 검증과 한계

| 검증 | 결과 |
| --- | --- |
| 실제074 보고서 writer + 전체077 FatFS/runtime/native GPIO 카드 | 기존116검사에 체크포인트를 실제 삽입. FAT16/32, 모든 SD 응답/쓰기end/읽기CRC 실패, 전체 재읽기, 쓰기 권한 회수 유지 |
| 새 체크포인트69검사 | 각7단계×4표시 오류×FAT2=56, 소유권/RESET8, 표시시간·wrap2, 권한/단계3. shared fault 이후 SRAM/SD 접근 금지 |
| 실제077 TIM2 함수5검사 |500ms 정상·정지된 카운터/poll 종료·100Hz wrap/시간 종료·카운트 overflow·이전 SPI 오류 보존 |
| 인과 대조3 | 글자 비교 제거는 손상 허용 assertion, RESET 재유지 제거는 정상 세션 assertion, 예산 재개방은 총시간 assertion에서 각각 실패 |
| 최종 ARM | main→전용run→writer→7개 checkpoint 호출, checkpoint→SRAM write/read·RESET·bounded timer·오류 처리, writer→실제FatFS 호출 확인 |
| 입력 보존 |1351개 준비 입력 해시 검사. 지정8개 native 소스077 동일, mini SHA256 동일. 새 Quartus/Questa/FPGA 조립 없음 |

카드/GPIO·SRAM/RESET/USB·TIM2 레지스터·SysTick은 호스트 모형이고 ARM CRC primitive는 호스트 대체다. 타이머 단위 시험은 실제 함수와 runtime/return의 정확한 앞부분을 사용하고 무관한 메뉴 복사 함수만 제외했다. 최상위 bootstrap/최종 화면 플랫폼은 소스·ELF 근거이며 모형으로 전체 실행하지 않았다. 실제 MCU 실행·화면 픽셀·인터럽트 지연·SD 초기화/아날로그 타이밍·전원 손실은 이번 결과가 아니다.

최종 펌웨어132104바이트, SHA256 `f80be9ac447edcc18d98354fc249286859b5971080baecd67a92e50b31813657`. mini SHA256 `9ae79c3028391063338d42ae16b19acf48d0d80858939b015ef6481f55cbefe9`. 빌드는 성공했어도 설치 승인이나 실제 하드웨어 성공을 뜻하지 않는다.

## 다음 작업과 재현

1. 준비 화면 전 boot/file_init/mini 경로의 공유 소유권과 정지 조건을 닫고 최종 결과 화면까지 실제 플랫폼 사건 순서를 검증한다. 기존077 하위 보호를 전역 변경하지 않는다.
2. mini의 RESET 후 SNES 초기화·font/WRAM/DMA 갱신 때문에 SRAM 비교만으로 가시성을 단정하지 않는다. 기존 부트 소스는 초기화를 다시 거친 뒤24행을 VRAM으로 보낸다. 500ms가 충분하다는 실측은 없다. 관측 가능한 화면 계획과 실패/복원 절차가 준비되면 한정된 외부 시험으로 판단하며, 미확정 물리 원인을 사전에 확정하라는 순환 조건을 만들지 않는다.
3. 보고서 전용P3는 이 조건과 정상044 복원 자료를 만족하면CF68의P2와 독립 판단한다. 준비도4완료/7부분/1미완료와P1 부분 상태를 유지한다. 사용자에게 같은 파일·LED·분해·PC USB를 다시 요청하지 않는다.

`tools/test_nes_report_checkpoint079.py`는 동결074/077 evidence와GCC, 새 출력 디렉터리가 필요하다. `--mode normal/no-compare/no-reset/no-budget`을 각각 실행한다. `tools/nes_report079_prepare.py`→`tools/build_nes_report079_arm.ps1`→`tools/check_nes_report079_arm.py`가 별도 compile-only 후보 경로다. `tools/verify_nes_report079.py`는 개인 동결 증거를 확인하며 공개 clone만으로 재현된다고 주장하지 않는다.

첫 소스복사 오류, 타이머 정의 추출/미사용 메뉴 링크 오류, ARM 선언 누락/버전 길이 초과와 Make 최초 의존성 실패를 보존했다. 최종 정상normal-06/변이-06/ARM-03을 기준으로 하며 과거044–078 동결은 수정하지 않는다. ARM 검사 최초CRLF 파싱 오류와 자동 승인 검토의 기존 빌더 변경 우려도 작업 기록에 남겼다. 기존074 빌더는 해시 불변이다.
