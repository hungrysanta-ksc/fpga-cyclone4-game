# FXPAK Pro GBC / Cyclone IV

기존 FXPAK Pro 하드웨어를 개조하지 않고 원본 GBC ROM을 실행하기 위한 FPGA 코어·펌웨어·SNES 표시 경로 연구 프로젝트입니다. 게임 ROM을 SNES ROM으로 변환하는 방식이 아닙니다.

## 시작점

- [실행 계획과 완료 기준](docs/EXECUTION-PLAN.ko.md)
- [FPGA 방법론 검토와 발견 사항](docs/FPGA-METHODOLOGY-REVIEW.ko.md)
- [자료 등록 규칙](CONTRIBUTING.md)
- [보고서 감사 도구](tools/audit_fpga_signoff.py)

2026-09-23 현재, 기본 게임 실행·음향·조작 및 K141 기준 저장/로드 교차 검증은 실기에서 확인했습니다. 간헐적 점멸/리셋 후 재실행 문제, G13 영상 확장의 고부하 처리량, 보드 전체 타이밍 검증은 미완료입니다. G13은 실험 단계이며 배포 가능한 완제품이 아닙니다.

먼저 인터페이스·클록·리셋·제약 감사를 수행하고, 자원/처리량 예산 → 근거 있는 수정 → 통합 검증 → 실기 → 미니게임/전투 평가 순서로 진행합니다. 원본 화소·색·CPU 속도·프레임 순서를 희생하는 전환은 승인되지 않았습니다.

## 이 초기 등록의 범위

계획·검토 문서와 자체 작성 보고서 감사 도구만 등록했습니다. RTL/펌웨어는 출처·라이선스·의존성을 확인하여 후속 등록합니다. **현재 저장소만으로 제품을 빌드할 수 없습니다.** 문서에 언급한 과거 로컬 보고서/실험 파일은 아직 저장소에 포함되지 않았습니다.

도구 자체 검사는 외부 FPGA 도구나 ROM 없이 실행할 수 있습니다.

```sh
python tools/audit_fpga_signoff.py --self-test
python tools/audit_fpga_signoff.py /path/to/quartus-report-directory
```

두 번째 명령에는 `pin.sta.summary`, `pin.sta.rpt`, `pin.fit.summary`, `pin.fit.rpt`가 필요합니다. 이 도구는 적용된 제약의 슬랙과 미제약/자원 항목을 분리해 보고하며 보드 signoff나 출하를 승인하지 않습니다. 출력에는 로컬 경로가 포함되므로 공개 전 검토해야 합니다.

상용 ROM·사용자 세이브·실기 덤프·라이선스 키·설치 도구·미검증 bitstream/ZIP은 등록하지 않습니다. 원본 시험 자료는 독립 로컬 사본에만 유지합니다.
