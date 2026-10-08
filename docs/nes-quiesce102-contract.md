# NES102 정지 경로 재현 계약

고정101 evidence를 읽고 새 출력 경로에 준비한다. 과거/완료된 동결 archive를 수정하지 않는다.

```text
python -B tools/prepare_nes_quiesce102.py --evidence101 <101-evidence> --out <new-arm>
python -B tools/test_nes_quiesce102.py --arm <new-arm> --evidence101 <101-evidence> --gcc <gcc> --out <new-pins>
python -B tools/test_nes_quiesce102_main.py --arm <new-arm> --evidence101 <101-evidence> --gcc <gcc> --out <new-main>
```

각각 새 출력 경로로 pins driver의 `--mutation cs|clock|miso|reset|order|call|baseline`을 실행한다. main driver는 별도 출력으로 `--geometry96`도 실행한다.1024+21 정상/오류 사례와 보호제거6/원본1의 실제 assertion 실패 로그를 보존한다.

고정 `build_nes_lower100_arm.ps1`와 검증된 mini를 재사용한다. SourceRoot/ArmBin/HostGcc/Make/UnixBin/MiniImage는100 계약을 따른다. 새 fit/ASM 없이 ARM만 링크한다. obj-nes-100/보조100 이름은 빌드 도구의 역사적 이름이며 실제 VERSION CF86-STOP102와 파일 해시를 기준으로 구분한다.

```text
python -B tools/check_nes_quiesce102_arm.py --arm <new-arm> --pins <new-pins> --main <new-main> --evidence101 <101-evidence> --objdump <objdump> --out <check.json>
python -B tools/verify_nes_quiesce102.py --evidence <102-evidence>
```

정리 함수의 레지스터 쓰기 뒤 계측 step을 넣어 BSRR/RCC 모델 효과와 순서를 관찰한다. 제품 함수/매크로 원문과 이 치환을 분리해 저장한다. ARM 검사는 실제 straight-line 명령의 MMIO 주소/값/배리어를 독립 기대값과 비교한다. 상태 입력·버스·GPIO·RESET/IRQ 효과는 모델이며 전기적 핀 정착이나 실측 시간 보장이 아니다. 최초 오류부터 blocked 진입까지의 전체 observer/UART/하위 경로는 별도다. 설치false를 유지한다.
