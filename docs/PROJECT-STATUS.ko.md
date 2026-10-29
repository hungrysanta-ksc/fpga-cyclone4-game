# 프로젝트 현황

기준일: 2026-10-29. 목표는 **sd2snes Cyclone IV 멀티 코어 확장**이다. 사용자 지시로 성능 개발을 재개했다. PC는 유지하며474/475 기준 수신·CRC/record와 실제 캡처·표시 일정부터 검토한다.

## 코어별 판정

| 코어 | 판정 | 근거와 범위 |
|---|---|---|
| GB/GBC | 추가 성공·제품 공개 | G13C44 / sd2snesHST 0.9.0, [기준선](../cores/gbc/README.md)·[호환성](COMPATIBILITY.ko.md) |
| NES | 개발 중, 제품 미포함 | 제한 자체 NROM의 표시·A 입력·STOP·메뉴 복귀 확인, 지속60fps·일반 게임/매퍼 확장 미완료 |
| PC Engine | 조사 대기 | 구현·실기 성공 없음 |

확인된 보드: FXPAK Pro / Mk.III, FPGA EP4CE15F17C8, MCU STM32F401RCT6, PSRAM IS66WVE4M16EBLL-70BLI 두 개. 다른 보드 지원이나 전체 외부 IO timing 승인을 뜻하지 않는다.

## 최신 NES 실기 기준

선택 구성은 **ARM474-02 / byte 동일 FPGA471-04 / 자체 이동 scene02**다. PR134가93bb8f715914da12d46f1d5c8262d6e8b10d3362로 master에 병합된 것을 확인했다. 과거 연구 후보338/355/402 등은 현재 설치 조합이 아니다.

| 관측 | 471 | 474 1회차 | 474 2회차 |
|---|---:|---:|---:|
| 측정 구간 | 60.07s | 60.07s | 60.07s |
| 최종 표시 완료 | 1178 | 1417 | 1417 |
| 평균 표시율 | 19.61fps | **23.59fps** | **23.59fps** |
| 계획·준비 포함 시간 | 13.63ms | 6.09ms | 6.07ms |

동일한 이동 장면에서 관측 처리율은20.29% 증가했고 정상 구간은 약24fps다. 과거 정적428의14.97fps와 직접 비율을 비교하지 않는다. FPS는 최종 표시 ACK를 확인한 완료율이며 NES 내부 실행속도나 무손실 capture를 입증하는 수치가 아니다.

두 회차 모두 CRC/전송 오류0,384KiB 적재/readback·START·STOP·base·메뉴 복귀 정상이다. 마지막 미완료1packet은 예정된 deadline에서 취소됐고 표시로 세지 않았다. 새 영상 없이 사용자의 동일 동작/메뉴 복귀 보고와 TXT를 확인했다.

- [실기475 해석](nes-nrom475-hardware.ko.md), [동결 수치](../analysis/nrom475-hardware.json).
- [474 기술·모델 범위](nes-nrom474-contract.ko.md), [선택 소스/해시](../analysis/nrom474-verification.json), [설치본 명세](../analysis/nrom474-package.json).
- [현재 NES 인계](../cores/nes/HANDOFF.ko.md), [원래 개발 계획과 최근 순서](nes-replan472.json).

## 비용과 남은 조건

| 항목 | 현재 값/판정 |
|---|---|
| FPGA Lite 전체 | 14740LE /13672comb /8063FF /185824RAM bits,474는471 bitstream 재사용 |
| 관련 timing | nominal setup+0.081ns/hold+0.143ns; 강화 배치 예산−0.036ns와 raw reset/CDC/미제약IO 미완료 |
| ARM | text202569/data10040/bss18552B; Flash 파일 후미380B, 큰 RUN frame 뒤 산술 RAM4984B는 전체 callchain/IRQ proof가 아님 |
| 다음 중간 목표 | 평균30fps까지 추가9.06ms/표시 단축 필요 |
| 최종 목표 | 지속60Hz까지 평균25.73ms/표시 격차; cadence·capture miss/repeat·p95·VBlank 검증 필요 |
| 일반 NES/MMC4·5 | 미완료; 제한 NROM 성과를 그대로 확장하지 않음 |

재개 후 우선순위는 수신·CRC·record hot path와 기존 capture/export·SEAL/최종ACK 일정의 분리다. 기존 회로는 export COMMIT 뒤 다음 capture를 이미 시작한다. 이 기능을 새로 구현하는 성과로 계산하지 않는다. 4credit 부족 대기는 이번 자료에서 거의 없었다.

## 현재 요청과 기록 위치

성능 개발을 재개했지만 최신 실기 기준은474/475 그대로다. 새 후보의 모델/명령 수를 새 실기 FPS로 표시하지 않는다. PR별 목표/작업내용/성과/후속작업은 [progress](progress/README.md)에 둔다. 원본 누적 문서와 오래된 등록부는 [archive](progress/archive/README.md)에 보존한다. 다른 PC는 [재개 안내](development/RESUME.ko.md)에서 시작한다.

다음 실기 후보476은 고정 SPI replay의 실제 M4 수신 명령506568→309481(−38.91%), 같은 상태/거래를 확인했다. 전체 ARM text+28B·RAM/stack 동일, FPGA 재사용이다. CRC/bitmap·8fault·native C/RTL/65816 연결을 통과했으며 새 실기 FPS로 계산하지 않는다. [476 근거](nes-receive476-contract.ko.md) · [설치·비교](nes-receive476-trial.ko.md).
