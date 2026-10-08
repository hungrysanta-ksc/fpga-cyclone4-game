# SPI101 재현 계약

고정100 evidence를 읽고 새로운 출력 디렉터리에 준비한다.044–100과 완료된101 증거/finalizer는 수정·재실행하지 않는다.

```text
python -B tools/prepare_nes_spi101.py --evidence100 <100-evidence> --out <new-arm>
python -B tools/test_nes_spi101.py --arm <new-arm> --gcc <gcc> --out <new-phase>
```

별도 출력에 `--mutation sync|exchange|reverse|fault|baseline-sync|baseline-exchange`를 각각 실행한다. baseline 두 경우는 `--evidence100 <100-evidence>`도 지정한다. 실제 실패 assertion과 원시 로그를 보존한다.

기존 `test_nes_lower100.py`를 수정하지 않고 같은 `<new-arm>`·고정099 evidence에 적용한다. 기본18, `--unit`13, `--geometry96`3경우를 새 출력에 실행한다. `build_nes_lower100_arm.ps1`도 그대로 재사용한다. SourceRoot/ArmBin/HostGcc/Make/UnixBin/MiniImage는100 계약과 같다. 기존 mini만 재사용하며 새 Quartus 작업은 필요 없다. 산출물은 기존 `obj-nes-100` 이름이지만 VERSION CF86-SPI101이며 설치 패키지가 아니다.

기존 `check_nes_lower100_arm.py`의 원문/호출 연결 검사 후 다음을 실행한다.

```text
python -B tools/check_nes_spi101_arm.py --arm <new-arm> --phase <new-phase> --evidence100 <100-evidence> --objdump <objdump> --out <check.json>
python -B tools/verify_nes_spi101.py --evidence <101-evidence>
```

상태 샘플 모델과 실제 ARM 타이밍·FPGA RTL·핀 전압/에지는 다르다. blocked 본문 검사는 취소 미구현의 증거이며 보호 통과로 분류하지 않는다. 두 대기별25tick/1Mpoll 및 공유 예산은 유지한다. 진단 소유권 밖 IRQ/DMA 동시 접근은 이번 검증 범위가 아니다. 강제 중단·주변장치 통합·최종 쌍/복원/외부IO·공통고장 승인 전 installable=false를 유지한다.
