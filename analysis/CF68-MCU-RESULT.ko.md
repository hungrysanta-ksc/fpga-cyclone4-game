# NES069 CF68 MCU 연결 결과

**이번 범위인 CF68 MCU 승인·초기 READY·오류 보호 연결과 C/ARM 검증을 달성했다.** MCU069는 변경 없는 FPGA068/CF68을 대상으로 한다. 실기 설치 준비 전체는 아직 부분 상태다.

- READY를 제한 시간·반복 한도로 기다린 뒤 GPIO와 CF68 검사로 진행한다. 이전 CF61/67/60/44/0 조합은 BEGIN 전에 거부한다. READY/shared-peripheral fault에서는 RESET·USB 보호를 유지하고 추가 base/SD 복구를 막는다.
- 하위95검사, 상위41실행·18입력 거부·16메뉴 및 추가ID2/READY1/native2, 인과 대조7개가 통과했다. 새로운069 C의 bounded physical replay72320응답 비트가068 RTL과 일치했다. load256 pin bytes와 TB96KiB 준비 후 CHECK256 bytes이며 전체 SPI 재생이 아니다.
- 전체 C80/96KiB 캡처180224bytes/901152frames를 새로 생성했다.065와 첫 CF 응답61→68만 달라지고 나머지 필드·시간은 같다. READY 대기 mock의 실제 시간·실기 SD/MCU 동작으로 확대하지 않는다.
- ARM 전체 링크와 실제3 marker/1 shared run+2 branch/2 checked programming/READY-before-GPIO/CF68 비교/오류 보호가 통과했다. 최종179336bytes SHA `268bc38df477516cbcee19f17b192151b79c6e011dc801756d1ad02fc0262499`는 compile-only다. 이전 빌드와 timestamp 기반 헤더4바이트만 다르고 나머지는 동일하다.
- 생산 RTL이068 fit03와 일치해 내부 fit/STA를 재사용했다. 새 Quartus/ASM은 없다. 최종965파일 증거 감사가 통과했으며 GBC/기존 NES와044–068 근거는 보존한다.

초기 생성기 구문·mock header·marker 기대·trace_frames 치환 실패, 첫 Make dependency 실패/재시도, 두 archive 수집 누락을 보존했다. 최종 freeze는 별도 evidence-complete이며 초기/중간 archive를 수정하지 않았다.

준비도5완료/6부분/1미완료를 유지한다. 실제 PCB/전압·SPI/SNES·클록 정지 감지/차단, 최종 전체 물리 SPI 재생, 새 ASM/ARM 쌍, 실제 SD 백업·복원·화면/GBC 관측이 남는다. 다음은069 전체 C 캡처를068 물리 top에 재생해 마지막 ACK/FINISH/status/STOP까지 통과시키는 작업이다.

[계약·재현](../docs/nes-cf68-mcu-contract.md) · [기계 요약](cf68-mcu-verification.json) · [현재 인계](../cores/nes/HANDOFF.ko.md).
