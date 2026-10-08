# 실제 하위 SPI100 재현 계약

고정099 증거를 새 디렉터리에 복사한다. 완료된044–099 자료와 finalizer는 수정하거나 재실행하지 않는다.100 완료 후에도 재현에는 새 출력 경로를 사용한다.

```text
python -B tools/prepare_nes_lower100.py --evidence099 <099-evidence> --out <new-arm>
python -B tools/test_nes_lower100.py --evidence099 <099-evidence> --arm <new-arm> --gcc <gcc.exe> --out <new-unit> --unit
python -B tools/test_nes_lower100.py --evidence099 <099-evidence> --arm <new-arm> --gcc <gcc.exe> --out <new-main>
python -B tools/test_nes_lower100.py --evidence099 <099-evidence> --arm <new-arm> --gcc <gcc.exe> --out <new-96> --geometry96
```

각각 새 출력 경로로 `--mutation select|async|budget|drain|ready|baseline`을 실행한다. 다섯 보호 제거 대조와 원본 반례가 독립 프로세스에서 실패해야 한다. 실제 함수 원문/호스트 MMIO 치환/모델/컴파일·실행 로그를 따로 저장한다.

ARM은 `build_nes_lower100_arm.ps1`에 SourceRoot/ArmBin/HostGcc/Make/UnixBin/MiniImage를 지정한다. 검증된 기존 mini를 재사용하고 새 Quartus 빌드를 하지 않는다. 사용하지 않는 W:/V: 임시 매핑만 사용하고 종료 시 해제한다. `check_nes_lower100_arm.py --arm ... --host <main-run> --evidence099 ... --objdump ... --out ...`로 실제 호출과 원문 연결을 확인한다.

동결 검사는 `python -B tools/verify_nes_lower100.py --evidence <100-evidence>`다. 공개 Git은 소스 adapter/시험/요약/해시만 포함하며 ROM·펌웨어·사용자 자료·라이선스는 포함하지 않는다.

VERSION `CF86-IO100`, 수동 표식/보고 파일/CF86 세션094는 유지한다.097의 동일086 fit ASM 이미지를 재사용한다.100 ARM은 compile-only이며 설치 가능한 파일 쌍이 아니다.

CS LOW 차단은 공유 오류 이후의 새 선택을 막는다. 기존 선택의 CS HIGH는 정리로 허용한다. DR 읽기/쓰기와 선택 횟수는 바이트 모델의 관측값이다. 검출 전 이미 시작된 비트의 종료/SCK·SPE·GPIO 상태, 전기적 IO, 실제 시간 상한은 별도 검증해야 한다. 진단 비활성 DMA/전체 게임 경로는 이번 시험의 실행 범위가 아니다.
