# 080 — mini·부트 ROM과 최종 화면의 오류 보호

## 작업 결과

079 이후 계획 중 **embedded mini 준비부터 보고서 결과 문구까지의 보호 경로**를 구현하고 검증했다. SDREPORT080은 기존 `fpga_rompgm`의 LED 패닉/재시도와 `snes_bootclear`의 초기 `sleep_ms`를 호출하지 않는다. 별도 bounded mini 프로그래머와 부트 ROM 전량 재읽기, 준비·최종 문구 비교를 사용한다. 이 범위의 구현·호스트·ARM 검증은 완료했다.

P1 전체와 실기 진입은 여전히 부분 완료다. main의 `file_init → f_mount → sdn_initialize`는 새 경로 이전에 실행된다. 카드 초기화의 ACMD41 반복은 무한 대기할 수 있고 느린 명령의 타이머/UART 보호도 아직 연결되지 않았다. active077에서 카드 초기화를 의도적으로 거부하므로 단순히 진단 활성화나 호출 순서를 앞으로 옮겨 해결하면 안 된다. **새 설치 패키지는 만들지 않았다.**

PR #28 미병합 상태에서 사용자가 후속 작업을 허용했다.079 head `53a36abb83e0d51de6a645c41eb15e4e0fc3a99c` 위에서 별도080 브랜치를 만들었다. 후속 PR은079 브랜치를 base로 삼아 이번 변경만 검토한다. 병합 순서는079(PR28) → 080이며079 병합 후080의 base를 master로 전환한다. 자동 병합은 하지 않는다.

## 변경한 동작

1. 진입 시 RESET 유지·USB 비활성 상태를 확보한다. 이미 active이거나 shared fault가 있으면 재진입을 거부한다. 이전 오류를 지워 재시작하지 않는다. 초기 mount의 `file_res`가 실패이면 mini나 SD를 추가로 접근하지 않는다.
2. 정상 mount 이후60초/100만poll 공통 IO 예산 안에서 mini를 설정한다. PROGB/INITB/DONE은 각100tick/500만poll과 공통 예산으로 제한한다. 재시도·SD·UART·LED 패닉을 사용하지 않는다. 실패 시 최초 오류와 RESET을 유지한다.
3. 고정된 embedded RLE 입력의 경계·run 길이·출력 한도를 검사한다. mini153544바이트와 부트 ROM65535바이트를 기존 실제 C decoder/caller의 출력과 전 바이트 비교했다. 마지막FF를 버리는 기존 caller 동작까지 유지하며 임의로65536바이트로 보정하지 않는다. 이 decoder는 두 고정 입력용이며 범용 RLE 호환 API가 아니다.
4. 부트 ROM은256바이트씩 SRAM에 기록하고 전량 재읽어 비교한다. mapper/mask 설정 뒤24줄 모두를 지우고 읽기 비교한다. 이 모든 동안 RESET을 유지한다.
5. 준비 문구와 최종 결과·경로·코드도 UART 없는 동일 SRAM 쓰기/읽기 비교 함수를 사용한다. 저장 중의 단계2–8은 그대로079 checkpoint를 호출한다. 보고서 오류8/shared fault 뒤에는 최종 화면을 접근하지 않는다. 논리적인 파일 오류만 보호가 살아 있는 상태에서 실패 문구로 표시한다.

mini/부트 입력 해시와077 nativeSD/FatFS/타이머/SPI/메모리·RESET,079 단계 callback은 그대로다. 이름만 `/HW080nnn.TXT`로 바꾼 실제 writer와 새 플랫폼을 ARM에 연결했다. 정상044/GBC/068 RTL/071 쌍은 변경하지 않았다.

## 검증 근거와 한계

| 항목 | 결과 |
| --- | --- |
| 고정 이미지 차등 | 실제 legacy `rle_mem_getc`를 실행해 mini153544/boot65535 출력과 새 decoder를 바이트별 비교. 잘린 escape/run·zero run·잘못된 마지막바이트·출력한도·sink 실패 검사 |
| boot/화면 플랫폼 |881검사. 정상 SRAM 전량 비교,563개 접근 각각의 공유 오류,256개 ROM·24개 화면 readback 손상, pin/timebase 정지·wrap, 최종 화면10개 접근 오류, mount/저장 실패, 소유권·재진입 거부 |
| 인과 대조2 | 부트 바이트 비교 제거는 손상 assertion에서, 저장 뒤 오류 guard를 reset으로 대체하면 추가 화면 접근 assertion에서 실패 |
| 최종 ARM | main→run080→session→boot/decode/화면/실제writer, writer→기존checkpoint7회 확인. 초기 `file_init` 호출도 남아 있음을 검사하며 감추지 않음 |
| 변경 영향 |10개 native/079 checkpoint 파일 해시 동일. 기존079의 실제 FatFS/native 통합185·timer5·인과3은 같은 소스 근거로 재사용하며 새 실행으로 세지 않음 |

881검사는 실제080 플랫폼·boot·decoder·runtime을 실행하지만 **FPGA 핀·SRAM·시간·USB와 보고서 저장 함수는 모형**이다. 이번 플랫폼 모형에서 실제 FatFS/CMD17/CMD24를 다시 실행하지 않았다. 그 근거는079에 별도로 남으며, 새 bootstrap부터 native 카드까지의 단일 전체 세션 시험은 아직 없다. 실제 ARM 실행, 화면 픽셀/가독성, SD 초기화, 보드 신호 타이밍을 검증하지 않았다.

ARM firmware132160바이트, SHA256 `79f97dd91001954ab753222d839dd7a9f2f5949b60e2a79ff661c7b21be56e2a`. mini 압축54754바이트 SHA256 `9ae79c3028391063338d42ae16b19acf48d0d80858939b015ef6481f55cbefe9`; boot 압축2811바이트 SHA256 `4805e32bc1118c266e69d0424f503b55c7016d3b21d61bec03527a3f06a08ff5`.

초기 host의 `smc.h` 누락, ARM의 기존 `fpga_get_done` 미선언, Make 첫 의존성 실패를 원본 로그에 보존했다. 최종normal-03/negative-03/ARM-02. 최초855검사도 보존하고 최종881과 구분한다.079 빌더를 수정 없이 재사용하므로 출력 폴더 이름은 `obj-report079`이며 바이너리 ID는 `SDREPORT080`이다.

## 다음 완료 조건

- 별도 report-only SD 초기화 경로에서 ACMD41/느린 명령/타이머/UART의 실제 하위 종료와 응답 검증을 연결한다. active077의 초기화 거부를 전역 삭제하거나 shared fault를 지워 우회하지 않는다.
- 카드 초기화 실패와 mini 준비 실패, 저장 단계 실패를 구분할 진입 순서·관측표를 만든다. 실행 중인 MCU/시간 기준을 전제로 한 보장과 reset/clock/startup 전제 밖 실패를 구분한다.
- 실제 플랫폼과 native SD를 한 세션에 결합해 초기화→준비 화면→저장→재읽기→최종 화면까지 검증한다. SRAM 비교는 화면 소비 ACK가 아니다. 외부 시험 전에 관측 가능한 가설·시간 경계·정상044 복원 절차를 구체화한다.
- 보고서 전용P3는 이 조건을 충족하면 CF68의 별도P2를 기다리지 않고 판단한다. 미확정 실기 원인을 사전 확정하라는 순환 조건은 두지 않는다. 기존 입력/LED/분해/PC USB를 다시 요구하지 않는다.

개인 증거는 `tools/verify_nes_report080.py`로 확인한다. 재실행은 `nes_report080_prepare.py`, `test_nes_report_boot080.py`, `build_nes_report080_arm.ps1`, `check_nes_report080_arm.py`와 고정079 evidence가 필요하다. 공개 clone만으로 모든 입력이 제공된다고 주장하지 않는다.044–080 완료 증거와 finalizer는 덮어쓰지 않는다.
