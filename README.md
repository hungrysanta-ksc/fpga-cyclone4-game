# Cyclone IV 코어 이식 연구 / FXPAK Pro GBC

이 공개 저장소는 두 가지를 위해 운영합니다.

1. **진행 중인 FXPAK Pro GBC 프로젝트의 근거와 작업을 보관·지원**합니다. 기존 하드웨어를 개조하지 않고 원본 `.gbc`를 실행하는 FPGA 코어·MCU 펌웨어·SNES 표시 경로를 다룹니다. 게임 ROM을 SNES ROM으로 변환하지 않습니다.
2. **다른 게임기 코어를 Cyclone IV로 이식할 때 참고할 방법과 계약**을 남깁니다. 보드 핀·클록·메모리·CDC·검증 범위를 새 대상에 다시 대조하도록 합니다. GBC 전용 수치가 다른 코어에도 성립한다고 가정하지 않습니다.

## 시작점

- [실행 계획과 완료 기준](docs/EXECUTION-PLAN.ko.md)
- [FPGA 방법론 검토와 발견 사항](docs/FPGA-METHODOLOGY-REVIEW.ko.md)
- [현재 진행·미결 gate](docs/PROJECT-STATUS.ko.md)
- [P0 인터페이스·클록·리셋 감사](docs/INTERFACE-CLOCK-RESET.ko.md), [타이밍 예외 판정](docs/TIMING-EXCEPTIONS.ko.md), [검증 행렬](docs/VERIFICATION-MATRIX.json)
- [P1 초기 예산](docs/SYSTEM-BUDGET.ko.md)
- [다른 코어 이식 참고 절차](docs/PORTING-PLAYBOOK.ko.md)
- [저장소 관리 규칙](docs/REPOSITORY-POLICY.ko.md), [기여·등록 절차](CONTRIBUTING.md), [의존성 등록부](docs/DEPENDENCY-REGISTER.ko.md)
- [보고서 감사 도구](tools/audit_fpga_signoff.py)

2026-09-23 현재, 기본 게임 실행·음향·조작 및 K141 기준 저장/로드 교차 검증은 이전 G12 후보에서 실기 확인했습니다. 간헐적 점멸/리셋 후 재실행 문제, G13 영상 확장의 고부하 처리량, 보드 전체 타이밍 검증은 미완료입니다. G13은 실험 단계이며 배포 가능한 완제품이 아닙니다.

먼저 인터페이스·클록·리셋·제약 감사를 수행하고, 자원/처리량 예산 → 근거 있는 수정 → 통합 검증 → 실기 → 미니게임/전투 평가 순서로 진행합니다. 원본 화소·색·CPU 속도·프레임 순서를 희생하는 전환은 승인되지 않았습니다.

## 이 공개 저장소의 범위

현재는 계획·감사·예산·관리 문서와 자체 작성 감사 도구를 등록합니다. RTL/펌웨어는 출처·라이선스·필수 의존성을 확인한 뒤 단계적으로 등록합니다. **현재 저장소만으로 제품을 빌드할 수 없습니다.** 문서에 언급한 과거 로컬 보고서/실험 파일은 대부분 포함되지 않았으며, 경로와 해시는 근거 식별용입니다.

도구 자체 검사는 외부 FPGA 도구나 ROM 없이 실행할 수 있습니다.

```sh
python tools/audit_fpga_signoff.py --self-test
python tools/audit_fpga_signoff.py /path/to/quartus-report-directory
```

두 번째 명령에는 `pin.sta.summary`, `pin.sta.rpt`, `pin.fit.summary`, `pin.fit.rpt`가 필요합니다. 이 도구는 적용된 제약의 슬랙과 미제약/자원 항목을 분리해 보고하며 보드 signoff나 출하를 승인하지 않습니다. 출력에는 로컬 경로가 포함되므로 공개 전 검토해야 합니다.

상용 ROM·사용자 세이브·실기 덤프·라이선스 키·설치 도구·미검증 bitstream/ZIP은 등록하지 않습니다. 원본 시험 자료는 독립 로컬 사본에만 유지합니다.

P1 계산 도구 `tools/p1_budget_calc.py`는 로컬 동결 보고서가 있어야 실행됩니다. 저장소 단독 실행용 CI 대상으로 취급하지 않습니다. 코드·문서 전체에 적용할 공개 재사용 라이선스는 의존성 출처 검토와 소유자 결정 후 명시합니다. 라이선스가 정해지기 전에는 단순 공개를 재배포 허락으로 해석하지 않습니다.

```sh
python tools/p1_budget_calc.py --snapshot /path/to/private/local-snapshot
```
