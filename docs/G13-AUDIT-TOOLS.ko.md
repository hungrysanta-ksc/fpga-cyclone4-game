# G13 과거 후보 분석 도구

PR #1의 도구 사용법을 보존합니다. 아래 snapshot 경로는 당시 동결 G13 후보용이며 C44 최신 빌드 절차가 아닙니다. C44 재현은 [빌드 안내](BUILD-C44.ko.md)를 사용합니다. 명령은 저장소 루트에서 실행합니다.

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

동결된 G13 후보의 타이밍 범위를 다시 확인할 때는 개인 snapshot에서만 다음 명령을 실행합니다. 첫 명령은 새 Quartus fit/STA DB와 원본 제약의 보고서를 개인 snapshot 안에 생성하며 bitstream을 만들지 않습니다. 생성 디렉터리가 이미 있으면 중단합니다. 두 번째 명령은 공개 가능한 집계만 표준 출력으로 냅니다.

```sh
python tools/run_sta_coverage.py --snapshot /path/to/private/local-snapshot --quartus-bin /path/to/quartus/bin64
python tools/summarize_sta_coverage.py /path/to/private/local-snapshot/probes/full-core-link/results/p0-g13-sta-coverage-v1
```
