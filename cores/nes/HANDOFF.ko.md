# NES 다음 작업 인계 — 055 이후

현재 후보는 **NES-R1-SPI-LIVE-055**다. [결과](../../analysis/SPI-LIVE-RESULT.ko.md)와 [재현 계약](../../docs/nes-spi-live-contract.md)을 먼저 읽는다. 실기 기준은044이며 새 SD 이미지는 없다.

## 완료한 경계

- 054의 CRC/길이/순번 검사와 CS 종료 commit을 거쳐,96KiB와80KiB 진단 ROM을 처음부터 SPI로 적재하고 실제 코어를 실행했다.2종8프레임491520픽셀과 패킷/이벤트 내용이053과 같다. release tick과 이벤트 시각의 일정한 차이는 결과에 기록했다.
- 처음에 미초기화된 PSRAM 핀 모델은 WE/byte lane 쓰기로만 채웠다. 상태 응답,각 바이트 완료,전체 내용,END/START와049 scrub·052 읽기 마감을 검증했다. 실제 물리 readback 검사기는 아니다.
- 합성 모듈32개가054 공동 fit와 같은 바이트다. 기존13866LE/948LAB/26M9K,**LAB15개 여유**를 재사용한다. 새 fit/STA나 새 보드 통과가 아니다.
- 054 C callback250kHz 파형/044 SPI 공유 근거를 보존한다.055 전체 적재는 가속 디지털 자극이며 실제 STM32·SD/메뉴 호출은 남았다.

## 다음 구현 순서

1. materialized044의 실제 STM32 GPIO/SPI 소유권과 USB IRQ 보호 아래054 C 전송기를 호출한다. 오래된 원본 H1 세션을 그대로 쓰지 않는다. 기존3바이트 transaction에8바이트를 억지로 전달하지 않고 핀 callback을 소유권 안에서 연결한다. SD 입력은 읽기 전용으로 제한하고 iNES 헤더/mapper/PRG·CHR 길이·trainer/지원 밖 형식을 검증하며 실패 시 START를 보내지 않는다. 현재 바이트당 DATA+STATUS는80KiB 약45.5초/96KiB 약54.7초라는 진단 처리량을 명시한다.
2. 승인된 ROM의 CHR16/32KiB 형상을 한곳에 고정해 SPI BEGIN 길이와 코어 CHR 마스크를 함께 설정한다. 현재 시험은 둘을 별도 fixture 입력으로 맞췄고 공동 top은 ext_chr_32k 입력을 받는다. reset을 유지한 채 적재 완료·물리 메모리 무결성을 확인하고,공통 reset/049 scrub·실제 NES 클록을 연결한다. GPIO 반환·base FPGA 복구·USB IRQ 복원은 정상/실패 모두 검증한다. base 복구 실패 시RESET과 IRQ 보호를 유지하고,성공 시에도 원래 USB IRQ enable 상태를 보존한다. CRC8/loaded를 PSRAM readback으로 간주하지 않는다. SNES_SYSCLK/PIN_A9는 주파수·지역·라우팅 미확인 후보다.
3. 보드 클록/소비자가 남은15LAB에 들어가는지 공동 예산부터 확인한다. 필요한 최적화는 동등성 회귀를 동반한다. 실제 SNES 소비자/frame deadline/복구·핀/PLL 공동 fit·외부 IO/CDC/STA가 끝나기 전 새 실기 이미지를 만들지 않는다.

044 화면 순환/RESET 복구·GBC 보고,041 실패,043/044 SDF 실패,050/051 지연 대조,053/054 실패와055 초기 full-count ready 기대 오류를 보존한다.055는 고정053 export를 새 폴더에서 변환하며 원본 checkpoint는 수정하지 않는다. RUN 이후60ms 수집과150ms 실행 watchdog,별도1초 적재 watchdog을 구분한다. 기존 개별 읽기 마감을 늘리지 않는다.

[과거 주의사항](history/AGENTS-053.md), [공개/로컬 재현 구분](REPRODUCING.ko.md), [주요 진전 커밋·PR 규칙](../../docs/development/MILESTONE-WORKFLOW.ko.md)을 따른다.055는 SPI에서 실제 코어까지 연결된 검증 진전으로 정리한다.
