# NES106 외부 예산 재현

```text
python -B tools/assess_nes_trial106.py --evidence086 <frozen086> --out <new-output>
python -B tools/verify_nes_trial106.py --evidence <frozen106>
```

086manifest와원시TSV·두budget 해시를 검사한다. 기존 calculate의16조건/3corner/3168경로를 유지하고20/60ns 시나리오의 전체JSON을 재현한다. 양수 경계 계산은1ps 정수 산술이며 추가5ns/동일두leg 가정에서52.282ns가+1ps,52.283ns가−1ps다. 이것은 권장 물리 한계가 아니다.

외부 전기적 범위·공통고장 처리의실기조건은 docs/nes-trial106-decision.json을 따른다. 현상태는미승인이다.600초 관측한도는사람의운영정책이며MCU완료보장/8µs차단/저장완료보장이아니다. 제품변경/새fit/실기실행없이 기존증거를 재사용한다. 완료archive를덮어쓰지않는다.
