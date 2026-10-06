# 개발 문서 안내

현재 상태와 과거 실험 기록을 이 안내에서 구분합니다. C번호는 개발 후보이며 앞으로 사용자 제품 버전과 별도로 관리합니다.

## 현재 개발·운영

- [현재 상태](PROJECT-STATUS.ko.md)
- [GBC 이식 회고와 재사용 경계](development/GBC-PORTING-LESSONS.ko.md)
- [NES 착수 인계](../cores/nes/HANDOFF.ko.md)
- [코어별 현황](../cores/README.md)
- [개발 구조·공통 경계](development/ARCHITECTURE.ko.md)
- [두 저장소 운영·버전 규칙](distribution/REPOSITORIES.ko.md)
- [sd2snesHST 0.9.0 공개 계획](distribution/0.9.0-PLAN.ko.md)
- [GBC 빌드](BUILD-C44.ko.md), [검증 범위](RELEASE-C44.ko.md)
- [소스·라이선스](DEPENDENCY-REGISTER.ko.md), [공개 정책](REPOSITORY-POLICY.ko.md)

## 사용자 문서의 원본

[사용 가이드](USER-GUIDE.ko.md)와 [호환성 기록](COMPATIBILITY.ko.md)은 개발 기준 원본입니다. 제품 배포 시 확정 버전으로 정리한 사본을 사용자 저장소에 제공합니다. [배포 저장소 초안](../distribution/sd2snesHST/README.md)은 0.9.0 공개 계획을 검토하기 위한 초안으로 보존합니다. 0.9.0은 공개됐으며 실제 제품 문서는 [배포 저장소](https://github.com/hungrysanta-ksc/sd2snesHST)의 확정본이 기준입니다.

## 새 코어 조사에 재사용할 문서

- [코어 제안서](../cores/CORE-PROPOSAL.ko.md)
- [포팅 절차](PORTING-PLAYBOOK.ko.md)
- [FPGA 방법론 검토](FPGA-METHODOLOGY-REVIEW.ko.md)
- [인터페이스·클록·리셋](INTERFACE-CLOCK-RESET.ko.md)
- [시스템 예산](SYSTEM-BUDGET.ko.md)
- [타이밍·예외 검토](TIMING-EXCEPTIONS.ko.md)

위 수치 문서는 당시 GBC 후보의 분석입니다. 새 코어에 수치·제약을 그대로 복사하지 않습니다.

## 과거 기준선

[초기 실행 계획](EXECUTION-PLAN.ko.md), [초기 검증 표](VERIFICATION-MATRIX.json), C43 설치·빌드·릴리스 문서는 역사적 기록입니다. 이전의 “실기 대기”, 자원 수치, 배포 보류 문구는 당시 상태를 뜻합니다. 원본 기록과 재현 경로를 유지하기 위해 이번 정리에서 파일을 옮기거나 삭제하지 않았습니다.

PR #1에서 보존한 기록과 도구:

- [2026-09-24 상태 원문](PROJECT-STATUS-20260924.ko.md)
- [확장 STA 경로 감사](P0-STA-COVERAGE.ko.md)
- [출력 종단·반복 표시 진단](P1-ENDPOINT-BACKLOG.ko.md)
- [G12S2 실기 기준선 시험](HARDWARE-BASELINE-TEST.ko.md) — 당시 설치판 전용 절차
- [과거 후보 분석 도구 사용법](G13-AUDIT-TOOLS.ko.md)

## 코어별 주요 진전 관리

[작업·커밋·PR 운영 규칙](development/MILESTONE-WORKFLOW.ko.md)을 따릅니다. 매 작업 호출마다 커밋할 필요는 없으며, 검증된 큰 진전마다 코어별 현황과 공통 교훈을 정리하고 커밋·PR을 만듭니다.
