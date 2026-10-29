# 다른 PC·새 작업에서 재개하기

이 문서는 채팅 기억과 이전 PC의 Downloads 없이 현재 작업을 파악하기 위한 진입점이다. **성능 개발은 재개했으며 현재 PC를 계속 사용한다.** PC 이전 작업을 우선하지 않고482 실기 기준·485 비교본의 전체 시간 관문을 따른다.

## 1. 상태를 읽는다

1. [루트 README](../../README.md) → [프로젝트 현황](../PROJECT-STATUS.ko.md).
2. [NES 현재 인계](../../cores/nes/HANDOFF.ko.md) → [PR136](../progress/pr-136.md).
3. 수정할 경계의 상세 계약/검증만 연다. 과거 누적 AGENTS/HANDOFF를 처음부터 읽거나 그 안의 NEXT를 현재 지시로 쓰지 않는다.

GB/GBC만 추가·공개 완료다. 현재 NES 게임 기준은 MMC482 실기1회60.06초/877최종 표시·평균14.60fps·50ms READY·STOP/base/메뉴 복귀 정상이다. 문양NROM476의23.84fps는 별도 회귀로 보존한다.60fps·전 게임/매퍼·capture/전체 CDC/IO 승인은 미완료다.

## 2. Git 기준을 확인한다

```text
git status --short
git remote -v
git branch --show-current
git log -5 --oneline
```

먼저 로컬 변경을 보존한다. 필요할 때 remote를 fetch하고 실제 병합 상태·base·master 도달 관계를 확인한다. PR135는948a2e9bc6542aaec7737e28f4431cb0c0350f6d로 master에 병합됐으며, 현재 브랜치는 `codex/nes-game-plan-supply-484`다. 새 PC에서 무조건 master로 바꾸거나 reset/pull로 덮지 않는다.

474 구현 고정 commit은 `06c71479e82a4fa1d76cddb810ea751b71d89880`,475 결과는 `06b4b579fc28c8aa9d750f7e772f6d146efeb2e5`다. 현재 문서 commit이 더 최신이어도 이 선택 산출물의 hash는 바뀌지 않는다. 병합 후 새 구현 작업은 사용자 지시에 따라 새 `codex/` 브랜치/PR에서 시작한다.

## 3. 환경과 자료를 나눈다

| 항목 | 준비/주의 |
|---|---|
| 문서·JSON 검사 | Python3, Git. 특정 사용자 홈 경로 불필요 |
| ARM | GNU Arm13.3.Rel1 계열·make·필수 유틸과 대상 config. 기존 빌더의 절대 경로를 먼저 확인 |
| FPGA | Quartus **Lite**를 기본 사용. 현재482 RTL/bitstream을 유지할 때 변경 없는 전체 합성을 반복하지 않음 |
| Questa | 설치된 Starter FLOAT1좌석으로 순차 실행. 해당 PC의 유효한 권한과 wrapper를 준비하며 원본 signed license는 Git에 저장하지 않음 |
| 에뮬레이터 | 필요한 경계에서만 Mesen/.NET 준비. 모델/CPU 실행과 전체 실기 시간을 구분 |
| 로컬 source/로그 | [NES 재현 범위](../../cores/nes/REPRODUCING.ko.md)의 빠진 입력을 먼저 복구. `probes`/`.tools`/Downloads가 clone에 포함된다고 가정하지 않음 |
| 실기 | 사용자가 ZIP을 SD에 복사하고 TXT를 반환한다. 보드·SD를 PC에 연결하라고 다시 요구하지 않음 |

기존 PC의 경로와 라이선스를 다른 PC에서 그대로 사용할 수 있다는 뜻이 아니다. 라이선스 키/host ID/서버 로그, ROM·개인 save·영상은 별도 관리한다. 현재 저장소만으로 전체 NES474 재빌드가 가능한 것은 아니며, **현재 판단/다음 순서와 그 이식성 부채를 저장소에 남긴 상태**다.

## 4. 개발 재개 후 순서

1. [실기483 분석](../nes-mmc483-hardware.ko.md)·[485 계약](../nes-supply485-contract.ko.md)·[다음 계획](../nes-game484-next-plan.json)을 읽는다. 실기482와 미실기485를 구분한다. 문양476은 별도 원복/회귀다.
2. G2B는 연결·기능 시험을 통과했다. candidate03/ARM03/armguard07/live02/trial02가 선택이다. 초기 busy-spin 후보는 전달하지 않는다. credit 수령·실제 ACK·staging 해제를 구분한다.
3. **다음은485 로그 수신(G4→G2C)**이다. [실기 안내](../nes-mmc485-trial.ko.md)의 새3TXT를 실제 ARM/SPI/IRQ/ROM 전체 DWT 비용으로 비교한다. 그 뒤 입력17ms/SEAL18ms를 포함한G3를 정한다. Flash232B/RUN31848B/154LE와 BSS+20B·stack 미증명 범위를 보존한다.
4. 독립 검사·STOP·최종 ACK·4credit·메뉴 복귀를 유지한다. RTL이 실제로 바뀔 때만 같은 source의 Lite 전체 비용/관련 timing을 다시 확인한다.
5. 의미 있는 변경이 검증된 뒤 새 번호·marker·로그·원복으로 동일 ROM/입력 조건의 하드웨어를 비교한다.482 한 회 성공을480의 단일 물리 원인·전 게임/매퍼·60fps 증명으로 승격하지 않는다.

## 5. 기록을 남긴다

- 현재 판정은 PROJECT-STATUS/코어 인계/registry에서 교체한다. README는 의미 있는 진척·정정 시에만 갱신한다.
- 이번 PR의 목표·작업내용·성과·후속작업은 `docs/progress/pr-NNN.md` 한 파일에 정리한다.
- 근거는 기존 `analysis/`/상세 계약에 연결한다. 루트 README에 PR 요약을 덧붙이지 않는다.
- `.github/PULL_REQUEST_TEMPLATE.md`를 사용하고 게시된 PR도 네 항목인지 확인한다.
- `python tools/check_repository_docs.py`로 진입 문서의 링크·형식·등록부·보존물을 검사한다. 이는 하드웨어 회귀가 아니다.
