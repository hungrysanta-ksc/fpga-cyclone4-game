# RTC099 재현 계약

고정098 증거에서 새 private 작업 디렉터리를 만든다. 완료된044–098 자료와 finalizer를 수정하거나 다시 실행하지 않는다.099 완료 후에도 새 출력 경로로만 재현한다.

```text
python -B tools/prepare_nes_rtc099_arm.py --evidence098 <098-evidence> --out <new-arm>
python -B tools/test_nes_rtc099.py --evidence098 <098-evidence> --arm <new-arm> --gcc <gcc.exe> --out <new-unit> --unit
python -B tools/test_nes_rtc099.py --evidence098 <098-evidence> --arm <new-arm> --gcc <gcc.exe> --out <new-main>
python -B tools/test_nes_rtc099.py --evidence098 <098-evidence> --arm <new-arm> --gcc <gcc.exe> --out <new-96> --geometry96
```

각각 새 디렉터리로 `--unit --mutation poll|time|cleanup|fault|baseline`을 실행한다. baseline은 기존098의 종료 없는 루프가 외부 모델 감시에 걸리는 반례이며 나머지 네 개는 새 보호의 검출력을 확인한다.

`build_nes_rtc099_arm.ps1`의 SourceRoot/ArmBin/HostGcc/Make/UnixBin/MiniImage를 지정한다. MiniImage는 고정098의 검증된 mini를 재사용한다. 사용하지 않는 W:/V: 임시 매핑만 사용하고 종료 시 해제한다. 최종 ELF는 `check_nes_rtc099_arm.py --arm ... --host <main-run> --evidence098 ... --objdump ... --out ...`로 확인한다. 이 checker는 해당 GNU ARM 출력의 구체적인 정리 분기를 검사하며 다른 툴체인의 코드 모양 차이는 별도 검토해야 한다.

동결 확인은 `python -B tools/verify_nes_rtc099.py --evidence <099-evidence>`다. 공개 Git에는 소스 adapter/시험/요약/해시만 있으며 원본 의존성과 ROM·펌웨어·로그·사용자 자료는 private에 있다.

VERSION은 `CF86-RTC099`; 수동 표식/보고 파일/CF86 세션 ID는094를 유지한다.097의 동일086 fit ASM 이미지를 재사용하며 새 FPGA 빌드를 하지 않는다.099 ARM은 compile-only이고 설치 가능한 파일 쌍이 아니다.

읽기/쓰기 준비 한도는 로컬100tick/100,000poll과 현재 공유 예산 중 먼저 끝나는 조건이다. 공유 오류가 있으면 후속 RTC 접근을 시작하지 않는다. 설정 중 실패한 경우에만 INIT=0/WPR lock 정리를 허용한다. tick 진행을 가정한 명목 시간과 정지 tick의 반복 한도를 구분한다. CPU 자체/MMIO 버스가 멈추는 고장의 종료 보장은 포함하지 않는다.
