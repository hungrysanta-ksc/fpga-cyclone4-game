# FPGA Core Development — sd2snesHST

**sd2snesHST의 개발 저장소**입니다. FXPAK Pro의 코어 구현, 재현 빌드, 검증 근거와 이식 경험을 관리합니다.
제품 이름의 **HST는 HungrySanTa = 제작팀 이름**을 뜻합니다.

일반 사용자 안내는 [sd2snesHST](https://github.com/hungrysanta-ksc/sd2snesHST)에서 제공합니다. **sd2snesHST 0.9.0 = 검증된 GBC C44**를 [공개했습니다](https://github.com/hungrysanta-ksc/sd2snesHST/releases/tag/v0.9.0). 다음 작업은 NES 코어 이식이며, [GBC 회고](docs/development/GBC-PORTING-LESSONS.ko.md)와 [NES 인계 계획](cores/nes/HANDOFF.ko.md)에서 시작합니다.

## 어디서 시작하나요?

| 목적 | 문서 |
| --- | --- |
| 사용자 배포와 개발의 역할·버전 관리 | [두 저장소 운영 계획](docs/distribution/REPOSITORIES.ko.md) |
| 0.9.0 준비·발행 순서 | [0.9.0 공개 계획](docs/distribution/0.9.0-PLAN.ko.md) |
| 배포 저장소 첫 화면 초안 | [sd2snesHST](distribution/sd2snesHST/README.md) |
| 코어 현황·NES/PCE 후속 작업 | [코어 로드맵](cores/README.md) |
| 새 코어 조사 시작 | [코어 제안서](cores/CORE-PROPOSAL.ko.md) · [이식 절차](docs/PORTING-PLAYBOOK.ko.md) |
| 공통 구현과 코어 경계 | [개발 구조](docs/development/ARCHITECTURE.ko.md) |
| 모든 현재 문서와 과거 기록 | [문서 안내](docs/README.md) |

## 개발 기준선

| 구성 | 현재 상태 | 소스·재현 |
| --- | --- | --- |
| GB/GBC | C44 실기 확인, 0.9.0 공개 완료 | [GBC 개발 안내](cores/gbc/README.md) |
| NES | 119 실기·122 기능 기준 유지;123 PLL/PSRAM핀 배치 성공,교차클록/reset 타이밍 연결 진행 | [NES 개발 안내](cores/nes/README.md) |
| PC Engine | 조사 대기; HuCard 범위를 우선 검토 | [PCE 조사 범위](cores/pce/README.md) |

현재 구현 대상은 **FXPAK Pro / Mk.III, STM32 + EP4CE15F17C8**입니다. 제품 이름이 바뀌어도 보드 지원 범위가 넓어지는 것은 아닙니다. NES/PCE의 동작 가능성·일정은 아직 확정하지 않았습니다.

이 보드·MCU·FPGA 대상은 [등록부](cores/registry.json)와 [NES 실기 준비 가이드의 하드웨어 기준](docs/development/NES-HARDWARE-READINESS-REVIEW.ko.md#확정된-개발-대상과-추가-확인-항목)에 고정합니다. 기존에 적힌 제품 정보를 반복해서 질문하지 않습니다. PSRAM IS66WVE4M16EBLL-70BLI 두 개와 MCU STM32F401RCT6도 사진으로 확인했습니다. 추가 확인은 실제 배선 지연·외부 타이밍 등 아직 확인되지 않은 항목으로 한정합니다.

검증된 GBC 입력 경로 `src/fpga`, `src/firmware-overlay`, `src/renderer`는 유지합니다. 코어별 안내·등록부로 구분하고, 실제 공통 코드 추출은 두 번째 코어의 요구가 확인된 뒤 별도 검증으로 진행합니다.

주요 진전마다 [코어별 기록·커밋·PR 절차](docs/development/MILESTONE-WORKFLOW.ko.md)에 따라 정리합니다. NES의 [공개 재현 시험](cores/nes/REPRODUCING.ko.md)과 전체 코어/실기 검증 범위는 구분합니다.

## 기록과 배포 원칙

- 구현 변경·upstream 출처·가설·실패 결과·재현 가능한 검증은 이 저장소에서 관리합니다.
- 사용자용 저장소에는 제품 안내와 릴리스만 정리합니다. 코드를 두 저장소에서 따로 수정하지 않습니다.
- 제품 버전, 코어 후보, 개발 커밋, 바이너리 해시, 세이브/상태 형식을 연결합니다.
- 상용 ROM·BIOS·개인 세이브·덤프·비밀 정보는 공개하지 않습니다.
- [라이선스](LICENSE.md) · [대응 소스 묶음](docs/SOURCE-BUNDLE.ko.md)
- [기여 규칙](CONTRIBUTING.md), [소스 고지](docs/DEPENDENCY-REGISTER.ko.md), [공개 정책](docs/REPOSITORY-POLICY.ko.md)을 따릅니다.
