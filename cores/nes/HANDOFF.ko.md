# NES 현재 인계 — SPI101 전송 완료 순서

SPI 진단 경로의 TXE→BSY 종료 순서를 수정했다. 지연 시작·위상·오류336경우와 기존 하위 통합34경우, 보호 제거4개·원본 반례2개 및 같은 ARM 검사에 통과했다. 강제 중단과 핀 차단은 미완료다.

PR50 병합 `6977f6c8fdd30f1f09d1fffc9357e9f7731e0b84`와 이전 head 포함 확인. 현재 `codex/nes-spi-abort-101`. 브랜치명은 착수 목표를 유지하지만 이번 완료 범위는 정상 완료 순서이며 강제 중단 구현은 아니다. [101 결과](../../analysis/SPI101-RESULT.ko.md)·[101 계약](../../docs/nes-spi101-contract.md)을 먼저 읽는다. PR은 사용자만 병합하며 한국어 제목/작업 목표·작업 내용·작업 결과를 유지한다.

## 다음 작업과 완료 조건

1. 101 ARM/097 이미지를 기준으로 실제 오류 경로의 SPI 강제 중단·CS/SPE/SCK/GPIO 상태를 구현·검증하고, UART/printf·타이머·CIC·RESET 연결을 확인한다. 이후 최종 파일 쌍·044 복원·외부IO/공통고장·관측 가능한 제한 실기를 확정한다.
2. `nes_diag_blocked`는 RESET/USB 보호 뒤 무한 루프만 수행하며 SPI disable/mux 분리를 하지 않는다. 정상 종료 TXE→BSY와 고착 오류 강제 중단을 분리한다. 새로운 CS LOW/DR 접근 차단으로 진행 중 비트 취소를 주장하지 않는다. MCU reset/GPIO 재매핑/주변장치 reset 중 선택은 실제 핀·소유권·SPI 모드 근거와 오류 호출 위치를 함께 검토한다. 이미 출력된 부분 명령은 무효 처리하고 같은 세션에서 자동 재개하지 않는다.
3. 실제 UART/printf·timer/CIC/resetGPIO와 observer는 다음 통합 대상이다.101 phase 모델은 blocked 본문만 새로 연결했고 observer는 stub이다. 전체 부팅/main 메뉴 루프는 아직 미검증. 현재 main2구간/full load/native/RTC/SRAM은100 연결을 재사용했다.
4. 정상101은 TXE를 먼저 확인하고 BSY를 확인한다. exchange의 중복 TXE를 다시 추가하면 보고 후10초/10000 공유 예산을 소진했던 main01 반례를 참고한다. 예산을 늘리거나 fault를 초기화하지 않는다. 단일wait25tick이며 둘을 합친25tick 보장은 아니다. 진단 시 동시 SPI IRQ/DMA 부재의 소유권 전제가 남는다.
5. 새 production 변경이 없으면101 ARM과097 ASM을 재사용한다. UART/abort 등 production이 바뀌면 host 원문·ARM 연결을 갱신한다. 동일 쌍/정확044복원/외부IO/공통고장/관측 절차 전 installable=false 유지. 사용자에게 기존 저장·클록·복원·부품·LED·분해·PC USB를 다시 요청하지 않는다.

## 최종 증거와 실패 보존

- 생산변경은 SPI의 sync/exchange 두 진단 분기와 VERSION CF86-SPI101. 레거시 본문/CS/RTC099/native/main/platform은 원문 유지. 첫 TXE 실패 시 BSY 미진입. 원본100 sync 조기CS,exchange 이전응답 두 반례는 상태 모델이며 실제 ARM 타이밍으로 재현됐다는 의미가 아니다.
- 최종 phase04 336 + unit01 13/main02 18/fat32-96-01 3, negative-sync/exchange/reverse/fault02 4개 및 baseline-sync/exchange02 2개. 최초 phase01 WinError623/negative-sync01 문자열 선택 실패/ARM01 main01 예산 실패와 phase02/03·build01을 모두 보존. 완료된 finalizer나044–101 archive를 수정하지 않는다.
- ARM02 182416 SHA `af5992164120769ab7beafc093013bb2c97a0e40f68d122cf73c8a9753e5b590`, ELF `52ff6fc129c9811d4a52c398c2f126066c24bdc288217f8f21c278d47337442b`. 고정100 builder/checker 재사용으로 obj-nes-100/보조 이름100은 역사적 이름, 입력 VERSION101이 실제다. 새 fit/ASM/Questa/실기/설치 패키지 없음.
- 098 메뉴주소0xC00000 두 수정,099 RTC 오류17/제한,094 sticky session을 유지한다.100 상태쓰기 오류는 RESET1회 해제 뒤 재보호할 수 있고, 보고서 RTC 실패는0바이트 가능. prepared 로그를 최종 메뉴 성공으로 쓰지 않는다.
- 097 동일086fit RBF510856 SHA6d916f4235fcd0d4d725059f0a2f4317ea49e3637c04a53db0b8ced85cb220c1, packed219453 SHA6ebad40acadf9978b150391a786ecaf89a0e753989e088a10db8839c03ac4805,071encoder/no089terminalFF. 사용자base legacyEOFpadding/원본HDL 동등성 미증명.044복원169056 SHA1c3b40a3459d24114cb4d91ee9d861d1a08025a670ef25317ef489092203693b.

## 실기·게임 목표

084 저장/재읽기/화면/044복원/메뉴/GBC,092 클록활동/TXT/복원 PASS 유지. 외부 실기는 사용자가 패키지 실행 후 로그를 보내는 방식이다. 두 클록 정지+locked HIGH CE9us 반례와 외부 전기적IO 승인은 미해결.

준비도4완료/7부분/1미완료·설치false. 첫 게임 SMB3(J),mapper4,PRG256KiB/CHR128KiB,393232bytes SHA dbb1cb5e18b091ca9101b1c2f5a5d6bdbeaa4a30ae1a504251310f6765cabb49.80/96KiB진단은384KiB게임지원이 아니다. ROM/바이너리/사용자자료/라이선스는 Git에 넣지 않는다. 전체 코어자원/DMC/IRQ/영상/입력/음향은 별도다.
