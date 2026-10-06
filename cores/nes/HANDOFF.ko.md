# NES 다음 작업 인계 — 056 이후

현재 후보는 **NES-MCU-LOADER-056**다. [결과](../../analysis/MCU-LOADER-RESULT.ko.md)와 [재현 계약](../../docs/nes-mcu-loader-contract.md)을 먼저 읽는다. 실기 기준은044이며 새 SD 이미지는 없다. 055의 [전체 SPI→코어 근거](../../analysis/SPI-LIVE-RESULT.ko.md)는 별도로 유지한다.

## 완료한 경계

- 054의 CRC/길이/순번 검사와 CS 종료 commit을 거쳐,96KiB와80KiB 진단 ROM을 처음부터 SPI로 적재하고 실제 코어를 실행했다.2종8프레임491520픽셀과 패킷/이벤트 내용이053과 같다. release tick과 이벤트 시각의 일정한 차이는 결과에 기록했다.
- 처음에 미초기화된 PSRAM 핀 모델은 WE/byte lane 쓰기로만 채웠다. 상태 응답,각 바이트 완료,전체 내용,END/START와049 scrub·052 읽기 마감을 검증했다. 실제 물리 readback 검사기는 아니다.
- 합성 모듈32개가054 공동 fit와 같은 바이트다. 기존13866LE/948LAB/26M9K,**LAB15개 여유**를 재사용한다. 새 fit/STA나 새 보드 통과가 아니다.
- 056은 materialized044 뒤에 SD 읽기 전용·GPIO 소유권·USB IRQ 보호·실패 복구를 연결했다. 호스트26 lifecycle/18입력 거부, 실제 C250kHz 파형의29024응답 비트/256핀 쓰기, ARM 전체 링크가 통과했다. 물리 STM32/SD 실행은 아니며 메뉴 호출·START는 없다. 미호출 함수를 ELF에 유지했다.

## 다음 구현 순서

1. 승인된 ROM의 CHR16/32KiB 형상을 한곳에 고정해 SPI BEGIN 길이와 코어 CHR 마스크를 함께 설정한다. 056은 첫 경로만 연결했고 공동 top은 별도 ext_chr_32k를 받는다. reset을 유지한 채 물리 메모리 무결성을 확인하고 공통 reset/049 scrub·실제 NES 클록을 연결한다. CRC8/CRC32/loaded를 PSRAM readback으로 간주하지 않는다. SNES_SYSCLK/PIN_A9는 주파수·지역·라우팅 미확인 후보다.
2. 보드 클록/소비자가 남은15LAB에 들어가는지 공동 예산부터 확인한다. 필요한 최적화는 동등성 회귀를 동반한다. 실제 SNES 소비자/frame deadline/복구·핀/PLL 공동 fit·외부 IO/CDC/STA가 끝나기 전 새 실기 이미지를 만들지 않는다.
3. 위 경계가 갖춰진 별도 RUN/메뉴 진입점을 만들고 적재 진행·명확한 종료 결과를 표시한다. 056 적재 전용 진입점은 END 후 STOP/기본 FPGA 복구로 ROM을 폐기하며, true 반환도 적재 성공이 아닌 메뉴 재로딩 안전성을 뜻한다. 호출자가 지정할 승인된056 FPGA 이미지는 아직 없고 stock044로 대체할 수 없다. 80KiB 약45.5초/96KiB 약54.7초에 SD/CPU 시간이 추가된다. 기존044 메뉴 hook을056 호출 완료로 세지 않는다.

044 화면 순환/RESET 복구·GBC 보고,041 실패,043/044 SDF 실패,050/051 지연 대조,053/054 실패와055 초기 full-count ready 기대 오류를 보존한다.055는 고정053 export를 새 폴더에서 변환하며 원본 checkpoint는 수정하지 않는다. RUN 이후60ms 수집과150ms 실행 watchdog,별도1초 적재 watchdog을 구분한다. 기존 개별 읽기 마감을 늘리지 않는다.

[과거 주의사항](history/AGENTS-053.md), [공개/로컬 재현 구분](REPRODUCING.ko.md), [주요 진전 커밋·PR 규칙](../../docs/development/MILESTONE-WORKFLOW.ko.md)을 따른다.056의 SCK 복원 후 보조 query 실패와 Make 첫 dependency 중단을 보존한다. GPIO 반환·기본 FPGA 검사·원래 USB IRQ 상태 보존을 유지한다. 기본 FPGA 복구 실패 시 RESET/IRQ 보호를 풀지 않는다.
