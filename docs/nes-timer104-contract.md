# NES104 타이머·IRQ 재현 계약

고정103 evidence와 동일 mini를 사용한다. 모든 출력은 새 디렉터리로 만들고 이전 증거를 덮어쓰지 않는다.

```text
python -B tools/prepare_nes_timer104.py --evidence103 <103-evidence> --out <new-arm>
python -B tools/test_nes_timer104.py --evidence103 <103-evidence> --arm <new-arm> --gcc <gcc> --out <new-main>
```

별도 출력 경로에 `--units`, `--geometry96`, `--timer-stall ticks`, `--timer-stall frozen`을 실행한다. `--mutation baseline|timer-bound|timer-cleanup|card-state|reset-invert|cic-threshold` 여섯 대조도 각각 실행한다. 최종60+23+2와 예상 실패6을 구분한다. 원본과 실제 추출 함수, 레지스터 모델, 실행 driver를 모두 보존한다.

`build_nes_lower100_arm.ps1`과 고정 mini를 재사용한다. SourceRoot/ArmBin/HostGcc/Make/UnixBin/MiniImage는100 계약을 따른다. obj-nes-100은 역사적 출력명이며 VERSION은CF86-IRQ104이다. 같은 FPGA fit/ASM을 다시 만들지 않는다.

```text
python -B tools/check_nes_timer104_arm.py --arm <new-arm> --evidence103 <103-evidence> --host <new-main> --objdump <objdump> --out <check.json>
python -B tools/verify_nes_timer104.py --evidence <104-evidence>
```

실제 timer/SysTick/LED/CIC/RESET 함수 실행과 TIM2/핀/시간 모델을 구분한다. 실제 SysTick을 UART40개 지점에 주입한 결과를 exhaustive IRQ/MCU 시간 증명으로 확대하지 않는다. card-state 대조는 반드시 DISK_OK에서 시작해야 하며 이미 CHANGED인 상태로 대조하지 않는다. unit watchdog은 제품 poll budget이 아니다. active 진단만 ISR 출력을 생략하고 카드 상태 갱신은 유지한다.
