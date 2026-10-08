# NES103 오류 관측·UART 재현 계약

동결102 evidence와 동일 mini를 사용하고 모든 출력은 새 디렉터리에 만든다. 기존 증거를 덮어쓰지 않는다.

```text
python -B tools/prepare_nes_observer103.py --evidence102 <102-evidence> --out <new-arm>
python -B tools/test_nes_observer103.py --arm <new-arm> --evidence102 <102-evidence> --gcc <gcc> --out <new-unit>
python -B tools/test_nes_observer103_main.py --arm <new-arm> --evidence102 <102-evidence> --gcc <gcc> --out <new-main>
```

단위 driver의 `--mutation baseline|observer|uart|flush|scope|order`는 각각 새 경로에서 실행하고 예상 assertion 실패를 보존한다. main은 별도 경로로 `--geometry96`와 `--uart-stall`도 실행한다. 최종17+21+16/대조6을 구분한다.

`build_nes_lower100_arm.ps1`와 고정 mini를 재사용한다. SourceRoot/ArmBin/HostGcc/Make/UnixBin/MiniImage는100 계약과 동일하다. 역사적 obj-nes-100 출력명이 남으나 VERSION은CF86-OBS103이다. 새 fit/ASM은 실행하지 않는다.

```text
python -B tools/check_nes_observer103_arm.py --arm <new-arm> --evidence102 <102-evidence> --unit <new-unit> --main <new-main> --objdump <objdump> --out <check.json>
python -B tools/verify_nes_observer103.py --evidence <103-evidence>
```

제품 함수 추출/formatter 이름 변경/매크로 래퍼/BSRR·RCC 효과를 원문과 분리해 보존한다. ARM 검사는 실제 분기의 종료 위치와 helper의 MMIO 쓰기를 대조한다. stdout 로그 자체는 제품 UART와 별개다. 전체 TIM2/SysTick/LED/CIC/RESET 입력은 아직 모델이며 물리 차단 시간·ARM 실행·설치 승인을 주장하지 않는다. recoverable report.error와 공유 fault를 합치거나 예산을 초기화해 통과시키지 않는다.
