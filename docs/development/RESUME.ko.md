# 다른 PC·새 작업에서 재개하기

이 문서는 채팅 기억과 이전 PC의 Downloads 없이 현재 작업을 파악하기 위한 진입점이다. **성능 개발은 재개했으며 현재 PC를 계속 사용한다.** PC 이전 작업을 우선하지 않고[감사499](../nes-audit499.ko.md)와[새 계획 A1–A4](../nes-audit499-plan.json)를 따른다. MMC509 실기 측정을 기준으로 A2 출력·전송 예산을 갱신하며 기존498 NEXT를 그대로 재개하지 않는다.

## 1. 상태를 읽는다

1. [루트 README](../../README.md) → [프로젝트 현황](../PROJECT-STATUS.ko.md).
2. [NES 현재 인계](../../cores/nes/HANDOFF.ko.md) → [PR140](../progress/pr-140.md).
3. 수정할 경계의 상세 계약/검증만 연다. 과거 누적 AGENTS/HANDOFF를 처음부터 읽거나 그 안의 NEXT를 현재 지시로 쓰지 않는다.

GB/GBC만 추가·공개 완료다. 현재 NES는 MMC509 60.08초770회 최종 표시/**12.82fps**, 실행·메뉴 복귀 정상이며 사용자는 체감 개선이 크지는 않다고 보고했다. 이전502/10.59fps와 동선이 달라 인과적 개선율·레벨별FPS는 미확정이다. [510 근거](../nes-hardware510-results.ko.md)를 따른다. 이후 시험판도 RESTORE 폴더를 생략하고502 백업을 보존한다.

## 2. Git 기준을 확인한다

```text
git status --short
git remote -v
git branch --show-current
git log -5 --oneline
```

먼저 로컬 변경을 보존한다. PR139 merge `46c0cc962397b3e757c838164b70b75fe73090a6` 뒤 `codex/nes-bandwidth-dma-budget-504`/PR140에서 진행 중이다. [509 구현](../nes-service509-contract.ko.md), [510 실기 결과](../nes-hardware510-results.ko.md)를 읽는다. 실기 로그 수신은 끝났고 다음은43.17ms 출력 구간 분리와 A2 본문 예산이다. 새 PC에서 무조건 master로 바꾸거나 reset/pull로 덮지 않는다.

474 구현 고정 commit은 `06c71479e82a4fa1d76cddb810ea751b71d89880`,475 결과는 `06b4b579fc28c8aa9d750f7e772f6d146efeb2e5`다. 현재 문서 commit이 더 최신이어도 이 선택 산출물의 hash는 바뀌지 않는다. 병합 후 새 구현 작업은 사용자 지시에 따라 새 `codex/` 브랜치/PR에서 시작한다.

## 3. 환경과 자료를 나눈다

| 항목 | 준비/주의 |
|---|---|
| 문서·JSON 검사 | Python3, Git. 특정 사용자 홈 경로 불필요 |
| ARM | GNU Arm13.3.Rel1 계열·make·필수 유틸과 대상 config. 기존 빌더의 절대 경로를 먼저 확인 |
| FPGA | Quartus **Lite**를 기본 사용. 현재489 RTL/bitstream을 유지할 때 변경 없는 전체 합성을 반복하지 않음 |
| Questa | 설치된 Starter FLOAT1좌석으로 순차 실행. 해당 PC의 유효한 권한과 wrapper를 준비하며 원본 signed license는 Git에 저장하지 않음 |
| 에뮬레이터 | 필요한 경계에서만 Mesen/.NET 준비. 모델/CPU 실행과 전체 실기 시간을 구분 |
| 로컬 source/로그 | [NES 재현 범위](../../cores/nes/REPRODUCING.ko.md)의 빠진 입력을 먼저 복구. `probes`/`.tools`/Downloads가 clone에 포함된다고 가정하지 않음 |
| 실기 | 사용자가 ZIP을 SD에 복사하고 TXT를 반환한다. 보드·SD를 PC에 연결하라고 다시 요구하지 않음 |

기존 PC의 경로와 라이선스를 다른 PC에서 그대로 사용할 수 있다는 뜻이 아니다. 라이선스 키/host ID/서버 로그, ROM·개인 save·영상은 별도 관리한다. 현재 저장소만으로 전체 NES474 재빌드가 가능한 것은 아니며, **현재 판단/다음 순서와 그 이식성 부채를 저장소에 남긴 상태**다.

## 4. 개발 재개 후 순서

1. [510 실기 분석](../nes-hardware510-results.ko.md)으로509와502의 측정·한계를 확인한다. 현재 소스와 [509 패키지](../../analysis/service509-package.json)는 고정한다.
2. 출력·최종ACK43.17ms를 일반 packet·복원·DMA·독립 검사·VBlank로 분리한다. planner/SEAL 대기 위치 변경과 op/quiet 중첩을 계산 절감으로 중복하지 않는다.
3. 조회 제외 wire16.25ms와 수신19.88ms를 함께 줄일 본문·프레이밍 후보를 비교한다. 잠정12ms wire, 전체16.67ms, 실제 ARM/IRQ/ROM과 Flash36B/FPGA244LE 잔여를 함께 본다.
4. 독립 검사·STOP·ACK/EA·VBlank·queue4/bulk2를 유지한다. 변경 없는 FIT를 반복하지 않고, 의미 있는 후보만 고유 이름으로 실기 전달한다. E8/phase/seed 미세조정은 동결한다.

## 5. 기록을 남긴다

- 현재 판정은 PROJECT-STATUS/코어 인계/registry에서 교체한다. README는 의미 있는 진척·정정 시에만 갱신한다.
- 이번 PR의 목표·작업내용·성과·후속작업은 `docs/progress/pr-NNN.md` 한 파일에 정리한다.
- 근거는 기존 `analysis/`/상세 계약에 연결한다. 루트 README에 PR 요약을 덧붙이지 않는다.
- `.github/PULL_REQUEST_TEMPLATE.md`를 사용하고 게시된 PR도 네 항목인지 확인한다.
- `python tools/check_repository_docs.py`로 진입 문서의 링크·형식·등록부·보존물을 검사한다. 이는 하드웨어 회귀가 아니다.
