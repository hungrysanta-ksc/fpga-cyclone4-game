# 문서 안내

## 현재 작업을 이어갈 때

1. [프로젝트 현황](PROJECT-STATUS.ko.md): 완료 코어, 최신 NES 실기 수치와 미완료 항목.
2. [재개 안내](development/RESUME.ko.md): 브랜치·환경·로컬 자료·다음 순서.
3. [NES 인계](../cores/nes/HANDOFF.ko.md): 선택 구성과 보호해야 할 경계.
4. [PR별 진척](progress/README.md): 과거 판단이 필요한 PR만 선택한다.

루트 README와 인계에 실험/PR 결과를 계속 붙이지 않는다. 이전 누적 본문은 [원문 이력](progress/archive/README.md)에 보존한다.

## 코어와 빌드

- [GB/GBC 완료 기준](../cores/gbc/README.md), [C44 빌드](BUILD-C44.ko.md), [호환성](COMPATIBILITY.ko.md), [사용 가이드](USER-GUIDE.ko.md).
- [NES 현황](../cores/nes/README.md), [현재 재현 범위](../cores/nes/REPRODUCING.ko.md), [실기474 안내](nes-nrom474-trial.ko.md), [실기475 비교](nes-nrom475-hardware.ko.md).
- [PCE 조사 범위](../cores/pce/README.md).

## 운영과 공통 설계

- [기여 규칙](../CONTRIBUTING.md), [PR·기록 운영](development/MILESTONE-WORKFLOW.ko.md), [PR 양식](../.github/PULL_REQUEST_TEMPLATE.md).
- [공통 구조](development/ARCHITECTURE.ko.md), [포팅 절차](PORTING-PLAYBOOK.ko.md), [GBC 이식 교훈](development/GBC-PORTING-LESSONS.ko.md).
- [하드웨어 기준](development/FXPAK-HARDWARE-REFERENCE.ko.md), [보드/클록 확인 근거](development/NES-HARDWARE-READINESS-REVIEW.ko.md).
- [공개 정책](REPOSITORY-POLICY.ko.md), [의존성·라이선스](DEPENDENCY-REGISTER.ko.md), [C44 대응 소스](SOURCE-BUNDLE.ko.md).

## 과거 근거 읽기

`docs/nes-*.md`와 `analysis/*.json`은 당시 후보의 상세 계약·검증이다. 파일 숫자가 가장 크다는 이유만으로 현재 기준으로 선택하지 않는다. 먼저 현재 현황/인계가 지목하는 근거를 읽는다. 오래된 문서 속 다음 작업·실기 대기·제약값을 새 실행 지시로 해석하지 않는다. 기존 상세 파일은 링크와 해시 보존을 위해 일괄 이동하지 않았다.
