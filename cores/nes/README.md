# NES 개발 현황

**NES는 진행 중이며 추가 완료 코어가 아니다.** 현재 PC에서474/475 기준 성능 개발을 재개했다. [전체 현황](../../docs/PROJECT-STATUS.ko.md) · [현재 인계](HANDOFF.ko.md) · [새 PC 재개](../../docs/development/RESUME.ko.md)

## 현재 실기 기준

- 조합: ARM476-02 / FPGA471-04 byte 재사용 / 자체 이동 NROM scene02.
- 1회60.07초/1432최종 표시, **평균23.84fps**, 정상 구간 약24fps. 이전474 2회는23.59fps였다.
- 수신 포함15.65ms로 줄었지만 SEAL/소비/최종ACK 대기가19.58ms로 늘어 전체 표시율은 거의 같다.
- CRC/driver 오류0, START·STOP·base 복구·메뉴 복귀 정상. deadline 마지막 프레임의4packet은 취소됐고 표시로 세지 않았다.
- OBJ0, warm mapdirty0, BG27/28group 재사용의 가벼운 장면이다. 실제 게임·SMB3 성능이나30/60fps를 대표하지 않는다.
- 문양은 회귀용으로 유지한다. 다음은 게임 대표 입력과 MMC3/SMB3의 source·loader·WRAM·IRQ·ROM 경쟁·전체 비용 관문이다.

[실기477·시험 대표성](../../docs/nes-receive477-hardware.ko.md) · [수치](../../analysis/receive477-hardware.json) · [476 소스/해시](../../analysis/receive476-verification.json) · [설치 명세](../../analysis/receive476-package.json)

## 소스와 기록

- 연결 RTL/firmware: `src/nes`, SNES 관련 소스: `snes/video_probe`, 생성/분석 도구: `tools`.
- 실제 선택 소스와 로컬 입력은 [재현 범위](REPRODUCING.ko.md)에 구분한다. `src/nes`의 파일을 임의로 모아 현재 보드 이미지를 만들지 않는다.
- [PR별 진척](../../docs/progress/README.md): 최근129–135와 전체 병합 색인.
- [이전 문서 원문](../../docs/progress/archive/README.md): 과거 Current/NEXT는 당시 기록이다.

재개 시에는 수신·CRC 비용과 이미 존재하는 capture/export/표시 중첩 일정을 먼저 확인한다. 자세한 예산·보존 조건·완료 조건은 현재 인계에서 관리한다.

478에서 기존 SMB3 기록71개가 현재 ARM에서 동등하게 처리됐고 MMC3 복원 후보가15266/15408LE로 배치됐다. [게임 진입 관문](../../docs/nes-game478-feasibility.ko.md). 새 loader/profile·실제 core/ROM 경쟁·게임 표시/복구 검증 전이므로 설치본은476을 유지한다.
