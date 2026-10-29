# NES 개발 현황

**NES는 진행 중이며 추가 완료 코어가 아니다.** 사용자 요청으로 성능 개발은 중지했다. [전체 현황](../../docs/PROJECT-STATUS.ko.md) · [현재 인계](HANDOFF.ko.md) · [새 PC 재개](../../docs/development/RESUME.ko.md)

## 현재 실기 기준

- 조합: ARM474-02 / FPGA471-04 byte 재사용 / 자체 이동 NROM scene02.
- 두 회차 모두60.07초/1417최종 표시, **평균23.59fps**, 초기 이후 약24fps.
- 동일 장면의471 평균19.61fps 대비20.29% 향상. 계획·준비13.63→6.09/6.07ms.
- CRC/전송 오류0, START·STOP·base 복구·메뉴 복귀 정상.
- 범위는 NROM16 수평 mirroring·CHR-ROM8KiB 자체 장면이다. 일반 NES·SMB3 지속 플레이·30/60fps·MMC4/5 완료를 뜻하지 않는다.

[실기475](../../docs/nes-nrom475-hardware.ko.md) · [수치](../../analysis/nrom475-hardware.json) · [474 선택/해시](../../analysis/nrom474-verification.json) · [설치 명세](../../analysis/nrom474-package.json)

## 소스와 기록

- 연결 RTL/firmware: `src/nes`, SNES 관련 소스: `snes/video_probe`, 생성/분석 도구: `tools`.
- 실제 선택 소스와 로컬 입력은 [재현 범위](REPRODUCING.ko.md)에 구분한다. `src/nes`의 파일을 임의로 모아 현재 보드 이미지를 만들지 않는다.
- [PR별 진척](../../docs/progress/README.md): 최근129–134와 전체 병합 색인.
- [이전 문서 원문](../../docs/progress/archive/README.md): 과거 Current/NEXT는 당시 기록이다.

재개 시에는 수신·CRC 비용과 이미 존재하는 capture/export/표시 중첩 일정을 먼저 확인한다. 자세한 예산·보존 조건·완료 조건은 현재 인계에서 관리한다.
