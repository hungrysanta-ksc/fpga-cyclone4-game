# NES065 — 메뉴 재적재·늦은 로그의 하위 종료와 보호

**범위를 정한 목표를 달성했다.** 진단의 보호 범위를 메뉴 준비와 RESET 해제 후 안정화까지 이어서, 버퍼 적재·SRAM 전체 비교·SPI/TIM2/FatFS/SD 쓰기 오류를 복귀 판단에 연결했다. host 시험과 최종 ARM 호출을 검증했다. **실기 진입 준비 전체는 미완료**다. 설치 쌍, 실제 외부 IO·물리 시간·화면 복귀·재진입 관측이 남는다.

PR18은2026-10-07T03:54:55Z 병합됐다. master 28e58e240d999c7c53b1e3da9c439a8c1d4367ea에서 진행했으며 044/GBC 실기 기준과 동결044–064 근거를 보존한다.

## 달라진 동작

- 수동 진단 시작 전에 RESET/USB 보호와 active 표시를 확보한다. probe 종료 후에도 메뉴가 준비되고 RESET 해제 후100ms 안정화·CIC/SRAM 검사가 끝날 때까지 보호를 유지한다. 후속 오류는 RESET을 다시 잡고 BLOCKED로 들어간다. 이는 외부 전원/RESET을 기다리는 보호 상태이며 패드 취소가 아니다.
- 실제 load_rom의 진단 전용 분기는 메뉴 파일만 허용하고 FPGA SD 오프로딩 대신 독립 FIL/256바이트 버퍼로 복사한다. 읽은 모든 바이트를 SRAM에서 다시 읽어 비교하고 크기·seek·short read·close·주소 상한을 검사한다. 메뉴 payload 상한은4MiB다. 일반 mapper0/1·carttype0–2만 허용하고 특수 칩·추가 FPGA/SGb/EGBC·MSU 경로를 배제한다.
- 실제 SPI BSY/TXE/RXNE/MCU_RDY 대기와 TIM2 지연에 tick·poll 종료를 넣었다. active SPI 블록 수신은 byte 방식이며 DMA 대기를 사용하지 않는다. TIM2는 stale UIF를 지우고 실패 시 CR1을 정리한다. 정상 GBC/일반 메뉴의 inactive 기존 본문은 유지한다.
- FatFS의 실제 move_window/get_fat에 누적 예산을 연결했다. 메뉴 준비는60초/1,000,000회, 늦은 로그는10초/10,000회다. 캐시 hit와 빈 클러스터 탐색도 한도를 소모하므로 SD busy만 제한하는 설계의 빈 경계를 닫는다. 소프트웨어 정책이며 물리 최대 시간을 측정한 값은 아니다.
- PREPARED_RESET_HELD 창에서만 CMD24 단일 블록 로그 쓰기를 허용한다. 실제 DATA/네 lane CRC16/응답 token/유한 busy 검사를 사용하고 불확실한 쓰기를 재시도하지 않는다. 논리적인 로그 open/write/short/close 실패는 선택적 기록 실패로 처리하지만 native SD·SPI·TIM2·FatFS 예산 오류는 RESET/USB 해제를 막는다. 오류 뒤 새 SD 읽기/쓰기 역시 차단한다.
- SD 파일은 PREPARED 기록만 남긴다. 이후 RETURN_READY_RESET_RELEASED는 RAM/UART에만 기록하고 SD를 다시 쓰지 않는다. 이 상태명은 코드가 복귀 준비 경계에 도달했다는 뜻이며 실제 화면 성공 관측이 아니다. 제한된 진단 복귀에서는 최근/즐겨찾기 항목 수를0으로 표시하고 cfg_save를 생략한다. 일반 재적재 경로는 원래 목록을 읽는다.

## 실행 근거

| 검사 | 최종 결과 | 실제 경계 |
| --- | --- | --- |
| 메뉴 복사 |20경우, 최대4MiB 및 전체 byte 비교 | 실제 helper C, FatFS/SRAM 모델 |
| SPI/TIM2 |12경우, 멈춘 tick·wrap·stale UIF | 실제 helper C, 레지스터 모델 |
| 늦은 로그 |24경우, 원래 USB IRQ 상태2종 | 실제 메뉴 C, 파일/SD 오류 모델 |
| SD 쓰기 |16경우, 네 lane CRC·응답·busy·no retry | 실제 writer/DATA helper, CMD24 응답/GPIO 모델 |
| FatFS |7경우, 캐시 한도·클러스터 탐색·inactive 유지 | 실제 move_window/get_fat/put_fat/create_chain, FAT/card 모델 |
| RESET 이후 복귀 |14경우, TIM2/CIC/SRAM 실패 시 RESET 재확보 | 실제 main의 준비/해제/안정화 구간, 주변 호출 모델 |
| 상위 회귀 |41 SD/복구,18입력 거부,16메뉴, native 오류 보호2 | 실제 상위 C, SD/programmer/GPIO 모델 |
| 인과 대조 |4개 모두 지정 assertion에서 실패 | 비교·로그 fault gate·SD CRC 전달·FatFS 예산 제거 |
| 전체 직렬 경계 |80/96KiB,180224바이트,901152프레임, 마지막 ACK/FINISH/STOP, START 없음 | 실제 C GPIO 전환/샘플,2µs 시간 모델 |
| ARM 전체 link |세 marker·한 공통 run call·같은 목적지 두 분기·메뉴 복사·FatFS guard 두 호출 | compile-only. STM32에서 실행하지 않음 |

두 전체 SPI trace의 SHA256은063과 동일하다. 따라서063의50,464,224응답 비트 보드 핀 재생과061의2386LE/186LAB/44M9K/135핀/PLL1·내부 최소0.131ns fit을 **동일 trace/생산 RTL 범위에서만** 재사용한다. 신규 Questa/Quartus 실행은 하지 않았다. 새 메뉴 SPI/TIM2/FatFS 경로의 물리 시간·위상·외부 IO 검증으로 확대하지 않는다. 전체 NES 코어959LAB/4LAB 여유와 마지막8프레임은 별도다.

compile-only firmware SHA256: aa5bec7d945ed6904961e555f4c54599203aa32f764e2690bacca16127d7e5a5. 설치하지 않는다. 일반 load_rom의 헤더 분류·설정 전체는 소스 검토/ARM link 근거이며 이번 host가 실제 전체 함수를 실행한 결과가 아니다.

## 보존과 다음 목표

로컬 probes/nes-menu-return-065에3249파일을 동결했다. manifest SHA256은00588f074cdc63f1736267a735df8fd4b1b25b5721d42f77d78708ac207923c2다. 초기 준비 구문 중복·표식 변환 오류, include/host stub 누락, ELF 짧은 분기 검사, FatFS macro/longjmp 시험 컴파일 실패를 보존했다. 최초 동결 감사는 build 로그 이름만 잘못 참조했다. 공개 verifier를 실제 arm-08.log 경로로 수정해 감사했으며 동결 archive는 수정하지 않았다. [기계 판독 결과](menu-return-verification.json), [계약·재현](../docs/nes-menu-return-contract.md).

현재 준비도는 완료5/부분6/미완료1을 유지한다. 다음은 정확한 PSRAM 부품·speed grade/보드 대응·외부 IO와 최종 FPGA ASM/압축 roundtrip·ARM 쌍·원본 SD 백업/rollback을 같은 후보로 묶는 작업이다. 메뉴 실제 파일 형상·시간 예산·LED/UART 가시성·SD write protect/card 상태·RESET 재진입은 제한된 실기에서 확인해야 한다. 그 전에는 SD 복사 요청이나 실기 준비 완료를 선언하지 않는다.
