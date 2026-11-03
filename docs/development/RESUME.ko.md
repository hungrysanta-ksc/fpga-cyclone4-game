# 다른 PC·새 작업에서 재개하기

이 문서는 채팅 기억과 이전 PC의 Downloads 없이 현재 작업을 파악하기 위한 진입점이다. 현재 PC를 계속 사용한다. 마지막 회고499 이후의 진행을 [579 회고](../nes-retrospective579.ko.md)로 재평가했다. 실행 순서는 [579 계획](../nes-retrospective579-plan.json) 하나를 기준으로 삼으며 499/504의 오래된 NEXT를 그대로 재개하지 않는다.

## 1. 상태를 읽는다

1. [루트 README](../../README.md) → [프로젝트 현황](../PROJECT-STATUS.ko.md).
2. [NES 현재 인계](../../cores/nes/HANDOFF.ko.md) → [PR150](../progress/pr-150.md).
3. 수정할 경계의 상세 계약/검증만 연다. 과거 누적 AGENTS/HANDOFF를 처음부터 읽거나 그 안의 NEXT를 현재 지시로 쓰지 않는다.

GB/GBC는 추가·공개 완료, NES는 MMC577 실기13.95fps/5–55초13.86fps다. 실행·메뉴 복귀 정상이며 전체60Hz·capture무손실·외부IO sign-off는 미완료다. [578 실기 기록](../nes-hardware578-results.ko.md)

## 2. Git 기준을 확인한다

```text
git status --short
git remote -v
git branch --show-current
git log -5 --oneline
```

PR150 병합588fa177ed1a82056a5cc86813506c3f2024cc70 확인 뒤 `codex/nes-whole-budget-580`에서 R1을 진행한다. [580 결과](../nes-whole580-results.ko.md)와 [선택 manifest](../../analysis/whole580-manifest.json)가 최신이다. 기존자료 분석과 로그 오류 수정만 했으며 제품 구현은 시작하지 않았다. 선택 산출물과 실측은 MMC577을 유지한다.

474 구현 고정 commit은 `06c71479e82a4fa1d76cddb810ea751b71d89880`,475 결과는 `06b4b579fc28c8aa9d750f7e772f6d146efeb2e5`다. 현재 문서 commit이 더 최신이어도 이 선택 산출물의 hash는 바뀌지 않는다. 병합 후 새 구현 작업은 사용자 지시에 따라 새 `codex/` 브랜치/PR에서 시작한다.

## 3. 환경과 자료를 나눈다

| 항목 | 준비/주의 |
|---|---|
| 문서·JSON 검사 | Python3, Git. 특정 사용자 홈 경로 불필요 |
| ARM | GNU Arm13.3.Rel1 계열·make·필수 유틸과 대상 config. 기존 빌더의 절대 경로를 먼저 확인 |
| FPGA | Quartus **Lite**를 기본 사용. 선택576 RTL/bitstream을 유지할 때 변경 없는 전체 합성을 반복하지 않음 |
| Questa | 설치된 Starter FLOAT1좌석으로 순차 실행. 해당 PC의 유효한 권한과 wrapper를 준비하며 원본 signed license는 Git에 저장하지 않음 |
| 에뮬레이터 | 필요한 경계에서만 Mesen/.NET 준비. 모델/CPU 실행과 전체 실기 시간을 구분 |
| 로컬 source/로그 | [NES 재현 범위](../../cores/nes/REPRODUCING.ko.md)의 빠진 입력을 먼저 복구. `probes`/`.tools`/Downloads가 clone에 포함된다고 가정하지 않음 |
| 실기 | 사용자가 ZIP을 SD에 복사하고 TXT를 반환한다. 보드·SD를 PC에 연결하라고 다시 요구하지 않음 |

기존 PC의 경로와 라이선스를 다른 PC에서 그대로 사용할 수 있다는 뜻이 아니다. 라이선스 키/host ID/서버 로그, ROM·개인 save·영상은 별도 관리한다. 현재 선택 MMC577의 clean-clone 전체 재빌드가 완료된 것은 아니며, **현재 판단/다음 순서와 그 이식성 부채를 저장소에 남긴 상태**다.

## 4. 개발 재개 후 순서

1. [579 계획](../nes-retrospective579-plan.json)의 R1 기존자료 분석은580에서 완료했다. 다음은 선택 fixture의 section별 바이트/변경량과 generation/준비/SEAL/ACK 연결을 확인하는 한 차례의 제한 조사다. 계측 overhead를 산정하고 물리 ROM/capture/입력 지연 결측을 숨기지 않는다. 전체분석/같은FIT를 다시 돌리지 않는다.
2. R2에서 본문 전송 감소·전체 critical path·실제 삭제·자원 예산을 함께 통과한 후보만 R3 구현으로 진행한다. 양수 timer/epoch/seed 및 국소 DMA/poll 반복은 재개하지 않는다.
3. R4는 의미 있는 후보만 실기 전달한다. 5–40/40–55초 완료 집계와 독립 검사·STOP·최종ACK·VBlank·메뉴복귀를 유지하며 시작 실패는 별도 보존한다.
4. 각 단계 완료 때 579 계획의 상태·증거·예산·다음 한 단계를 함께 갱신한다. 오래된 계획의 미완료 상태를 방치하지 않는다.

## 5. 기록을 남긴다

- 현재 판정은 PROJECT-STATUS/코어 인계/registry에서 교체한다. README는 의미 있는 진척·정정 시에만 갱신한다.
- 이번 PR의 목표·작업내용·성과·후속작업은 `docs/progress/pr-NNN.md` 한 파일에 정리한다.
- 근거는 기존 `analysis/`/상세 계약에 연결한다. 루트 README에 PR 요약을 덧붙이지 않는다.
- `.github/PULL_REQUEST_TEMPLATE.md`를 사용하고 게시된 PR도 네 항목인지 확인한다.
- `python tools/check_repository_docs.py`로 진입 문서의 링크·형식·등록부·보존물을 검사한다. 이는 하드웨어 회귀가 아니다.
