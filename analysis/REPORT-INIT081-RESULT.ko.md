# 081 — 보고서 전용 SD 초기화와 FatFS mount 연결

## 달성한 목표

준비 화면 앞에서 실행되던 SD 초기화를 보고서 전용의 유한 대기·응답 검사 경로로 옮겼다. 실제 초기화 C의 GPIO 카드 시험과 실제 FatFS mount를 연결하고, 최종 ARM에서 초기화→mount→080 mini→writer 호출을 확인했다. **이 범위는 달성했으며 P1 전체는 부분 완료다.** 사용자 실기의 0바이트 원인은 아직 확정되지 않았다.

SDREPORT081은 132320바이트, SHA256 `5931eec90956022104b8aa42851525b52b3f3a805d50a48ca71c33357357649d`인 **컴파일 검증용 후보**다. 설치 패키지는 만들지 않았다. `/HW081nnn.TXT`와 기존 3072바이트 저장 시험을 사용하며 이미 확인한 하드웨어를 재수집하지 않는다.

## 변경과 보호

- 기존 sdnative.c 전체 바이트를 앞부분에 보존하고 보고서 전용 함수를 끝에 추가한다. 기존 `sdn_initialize`의 active077 거부도 그대로다. 별도 보고서 링크의 강한 `disk_initialize` 정의는 성공한 최초 초기화의 상태만 반환한다. 초기화 전·오류 후·잘못된 drive·재진입은 거부하며 자동 재초기화하거나 오류를 지우지 않는다.
- FatFS는 카드가 초기화됐어도 새 mount에서 `disk_initialize`를 호출한다. 이 실제 경계를 시험으로 연결했으며, 단순히 `disk_state=DISK_OK`만 설정한 중간 ARM01은 최종 후보가 아니다.
- CMD7 선택 해제/2042클록→CMD0→CMD8→CMD55/ACMD41→CMD2/3/9→CMD7/busy→CMD13→CMD55/ACMD6→CMD16 순서다. CMD2의 CID를 보존하며 CSD 용량 계산은 범위 검사 후 드라이버 상태에 반영한다. 모든 성공 조건 이전에는 DISK_OK를 게시하지 않는다.
- 응답 시작·전송 비트, 명령 번호, end/CRC7, R1/R6 오류, CMD8 전압·echo, APP_CMD, OCR 전압, CMD13의 전송 상태를 검사한다. R2는 내부 CRC, R3는 CRC 없는 예약 비트 형식으로 구분한다. CMD8 무응답을 구형 카드로 추정하지 않는다. 이번 전용 경로는 CMD8에 정상 응답하는 SD v2 SDSC/SDHC·SDXC 범위이며 구형 SD v1/MMC/SDUC 지원을 주장하지 않는다.
- RESET LOW/USB IRQ off/offload0/전송 없음/보고서 쓰기권한 닫힘이 필요하다. 매 느린 반주기에서 실제 bounded 타이머를 호출하고, 반환 뒤 소유권과 공유 오류를 다시 확인한 다음 클록을 출력한다. 초기화 경로의 printf/UART/legacy 느린 명령 호출은 없다.
- ACMD41은 누적 200tick(정상100Hz에서 명목2초)/2048회 한도, 응답 시작은1000클록, CMD7 busy는100tick/250000회 한도다. 상위60초/1000000poll 예산도 공유하며 먼저 소진되는 한도가 우선한다. tick 정지에서도 유한 반복으로 종료한다는 근거이며 실제 벽시계·성능 보장이 아니다. 기존 저장1000tick/10000poll과7×500ms는 변경하지 않았다.

프로토콜 근거는 SD Association Physical Layer Simplified Specification 6.00 §4.2.3, §4.5, §4.9다. [공식 배포 안내](https://www.sdcard.org/downloads/pls/)와 [동일 규격 원문 사본](https://www.taterli.com/wp-content/uploads/2017/05/Physical-Layer-Simplified-SpecificationV6.0.pdf)을 대조했다. 공식 PDF 직접 다운로드는403으로 실패해 원문 사본을 사용했다. 초기화 제한은1초보다 길게 잡았고 R3를 CRC 오류로 취급하지 않는다.

## 검증 결과와 범위

| 검증 | 결과 |
| --- | --- |
| GPIO 초기화 + 실제 FatFS mount | 8558검사. 정상17명령/7990반주기, SDSC/SDHC 용량, tick wrap, 모든7990타이머 실패 위치, 주기적 카드 제거, 모든15응답 위치의 무응답·CRC/end/index 오류, 의미 오류, ready/busy 영구 대기, 소유권·첫 오류·재진입 거부 |
| mount 연결 | 새 mount/다시 mount에서 초기화 명령을 재전송하지 않음. 미초기화/잘못된drive/쓰기보호 상태 전달, sector 읽기 오류→실제FatFS 실패→이후 추가 읽기 금지 |
| 인과 대조2 | 응답 형식·CRC 검사 제거는 손상 응답 수용 assertion, 타이머 실패 뒤 클록 출력 허용은 추가 GPIO assertion에서 각각 실패 |
| 최종 ARM02 | main→전용run→실제초기화→file_init→f_mount→전용disk_initialize→상태 연결. 080 boot/decode/최종문구와 writer→079체크포인트7호출 확인 |
| 보존 | sdnative 원본 전체 prefix, FatFS/fileops/timer/SPI/메모리/runtime/079checkpoint/080boot·decode12파일 동일. 정상044/GBC·원본NES·기존044–080 동결 불변 |

GPIO 카드·시간·USB/RESET·CRC primitive는 호스트 모형이다. mount의 sector 데이터는 모형 VBR이며 081 시험에 전체 CMD17/24 저장 경로는 포함하지 않았다. 기존079 실제 writer/FatFS/native185·타이머5 및080 boot/platform881 근거는 동일 소스 범위에서 재사용하며 새 전체 실행으로 합산하지 않는다. ARM은 링크·호출 근거이며 실제 MCU 실행이 아니다. 새 RTL/Questa/Quartus/FPGA 조립·물리 화면 시험은 없다.

main의 초기 UART 배너와 사전 file_init 호출을 보고서 후보에서 제거했다. 하지만 MCU 전원·클록·GPIO·TIM2/SysTick·USB/CIC 초기 설정이 실행 가능해야 한다는 시작 전제는 남는다. 이 코드가 CPU/클록 정지나 모든 main 초기 설정을 복구한다고 주장하지 않는다.

최초 wrap 시험은 공유 예산 시작 후 tick 원점을 바꿔 실패했다. 시험 설정 순서를 고쳤고 생산 코드 오류로 계산하지 않는다. 이후 FatFS 결합의 UART 헤더/미사용함수 COFF 링크 의존성 오류, ARM01의 mount 연결 누락과 Make 최초 의존성 실패도 원문을 보존했다. 최종 normal-06/변이-06/ARM02를 기준으로 한다.

## 다음 작업과 완료 조건

1. 실제 초기화→실제 FatFS/native CMD17/24 writer→재읽기와 080 mini/최종문구를 **단일 플랫폼 실행**에 연결한다. 지금의 mount VBR 모형과 별도079 저장 시험을 합쳐 전체 검증 완료로 표시하지 않는다. 첫 mount의 강한 disk_initialize 연결을 유지하고 오류 이후 자동 재초기화를 금지한다.
2. 화면 이전 실패는 현재 외부에서 검은 화면만 보일 수 있다. 안전한 관측 경계·최대 대기 안내·각 결과별 다음 조치와 정상044 복원 자료가 있어야 보고서 전용P3/실기를 판단한다. 숨겨진 LED·추가 분해·같은 파일·PC USB를 다시 요구하지 않는다.
3. 준비도4완료/7부분/1미완료를 유지한다. CF68 외부 타이밍P2/같은쌍P3와 전체NES 자원4LAB/P5·P6는 별도다.

재현: `tools/test_nes_report_init081.py`는 고정080 evidence/GCC와 새 출력 폴더를 사용한다. `tools/nes_report081_prepare.py`→기존079 ARM builder→`tools/check_nes_report081_arm.py` 순서다. 빌더 출력명의 obj-report079와 실제 VERSION SDREPORT081을 혼동하지 않는다. `tools/verify_nes_report081.py`는 동결 근거만 읽는다. 개인 입력이 필요한 현재 경로를 공개 clone만으로 재현 가능하다고 표시하지 않는다.
