# NES 현재 인계 — 실제 하위 SPI100

실제 SRAM·FPGA 명령·STM32 SPI를 연결하고 오류 이후 새 칩 선택과 추가 DR 접근을 차단했다. 단위13·main 통합21경우, 대조5개와 원본 반례, 같은 ARM 링크가 통과했다.

PR49 병합 `13118bdb15df113fe8e68df00f99344840fccbbd`와 기존 head 포함 관계를 확인했다. 현재 `codex/nes-lower-spi-100`. [100 결과](../../analysis/LOWER100-RESULT.ko.md), [재현 계약](../../docs/nes-lower100-contract.md)을 먼저 읽는다. PR은 사용자만 병합한다. 한국어 제목과 작업 목표·작업 내용·작업 결과 세 절을 유지한다.

## 다음 작업과 완료 조건

1. 100 ARM/097 이미지를 기준으로 실제 UART/printf·타이머·CIC·RESET 호출과 이미 시작된 SPI 전송의 취소/핀 상태를 검증한다. 이후 최종 파일 쌍·044 복원·외부IO/공통고장·관측 가능한 제한 실기를 확정한다.
2. 이번 CS/DR 모델은 오류 이후의 추가 소프트웨어 접근 차단만 증명한다. SPI BSY 고착 시 이미 시작된 비트/SCK/SPE·GPIO/CS 해제의 실제 상태는 미검증이다. 이 항목을 닫지 않고 모든 물리 IO가 즉시 멈춘다고 쓰지 않는다. 레지스터/FPGA 바이트 응답/시간/SD 카드·핀·CRC primitive, UART/printf/CIC/RESET/GBC disarm은 여전히 모델이다.
3. 현재 main 두 구간, 전체 load_rom,099 RTC를 그대로 재사용한다. main은 공유 오류 뒤에도 일부 함수 호출을 계속하므로 실제 lower 차단을 확인한다. firstboot=false/pending/base 복원/IRQ 차단에서 시작하며 부팅 전체와 이후 메뉴 루프는 미검증이다.
4. 098 메뉴 주소0xC00000 두 검사 수정과099 RTC 한도/오류17 유지. 해제 후 autoboot/status 호출까지 보호한다.100 status 쓰기 고착은 해제1회 뒤 공유 예산 오류16·재RESET으로 종료한다. 준비 TXT 성공을 최종 메뉴 성공으로 쓰지 않는다. report RTC 실패는 저장0바이트가 가능하다.
5.097 ASM과 기존 mini를 재사용하고 불필요한 fit/ASM/Questa를 반복하지 않는다. production C가 바뀌면 ARM 갱신과 host 원문/ELF 연결을 확인한다. 최종 동일쌍/정확한044복원본/외부IO와 두 클록 정지+lockedHIGH CE9us 반례/관측 절차 확정 전 설치false를 유지한다.

## 완료와 고정 입력

- 100 생산 변경은 stm32f4xx/spi.c·fpga_spi.h·VERSION 세 파일. sync/async select는 공유 오류 뒤 CS LOW 금지, deselect HIGH는 정리로 허용한다. BSY/TXE/RXNE/READY와 drain은 공유 예산/최초 오류 및 개별25tick/1Mpoll을 확인한다. 진단 비활성 레거시 SPI 기능 경로는 유지했으나 CPU 사이클/GBC 실기를 새로 측정하지 않았다.
- 실제 memory7/fpga_spi16/SPI9 본문을 추출·컴파일했다. 진단/단위 호출 분기를 실행했으며 모든 레거시 함수/분기의 실행 증거는 아니다. main/load/native/RTC는 변경하지 않았다. 최종unit03=13/main01=18/fat32-96-01=3/negative-select,async,budget,drain,ready01=5/negative-baseline01. 정상 DR쓰기139042/CS선택2079/메모리읽기67584, SD명령1534/1637·보고쓰기5전부 해제전.
- ARM02 182404바이트 SHA75f0bb6125aa12666e03eaec46c6a0811dab7f11d9f821b624cfdfb8867d6050, ELF67a22a07e2e4186cdf62600091476a37c5189b7069f604bee9146d22d6cf387f. VERSION CF86-IO100, 수동표식/보고 파일/세션094 유지. compile-only. host fpga_spi.c/spi.h의 CRLF→LF만 정규화 비교했고 별도 해시 기록. 나머지 production 입력도 원문 일치.
- private probes/nes-lower100/evidence 및 analysis/lower100-verification.json/verifier가 최신 근거다. 최종빌드는arm02;arm01은 함수 경계 줄바꿈 수정 전 준비본. 초기추출·매크로/DMA컴파일·checker줄끝 비교 실패와 Make 의존성 재시도를 보존했다. 완료 finalizer 재실행/044–100 archive 수정 금지.
- 097 동일086fit ASM RBF510856 SHA6d916f4235fcd0d4d725059f0a2f4317ea49e3637c04a53db0b8ced85cb220c1, packed219453 SHA6ebad40acadf9978b150391a786ecaf89a0e753989e088a10db8839c03ac4805.071encoder/no089terminalFF. 사용자base legacyEOFpadding/HDL출처 미증명 유지.044복원169056 SHA1c3b40a3459d24114cb4d91ee9d861d1a08025a670ef25317ef489092203693b.

## 실기·제품 목표

084 저장/재읽기/화면/044복원/메뉴/GBC,092 클록 활동/TXT/복원 PASS를 유지한다. 부품·LED·분해·PC USB·기존 파일 질문이나 완료된 실기 시험을 반복하지 않는다. 사용자가 외부 실기에서 패키지를 실행하고 로그를 보내는 방식이다.

준비도4완료/7부분/1미완료·설치false. 전체 코어 자원/DMC/IRQ/영상/입력/음향은 별개다. 첫 게임 Super Mario Bros3(J), mapper4,PRG256KiB/CHR128KiB,393232bytes SHA dbb1cb5e18b091ca9101b1c2f5a5d6bdbeaa4a30ae1a504251310f6765cabb49.80/96KiB진단은384KiB게임지원이 아니다. ROM/바이너리/사용자 자료/라이선스는 Git에 넣지 않는다.
