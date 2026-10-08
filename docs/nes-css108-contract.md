# NES108 CSS/NMI 검증 계약

```text
python -B tools/prepare_nes_css108.py --evidence104 <frozen104> --out <new-arm-source>
python -B tools/test_nes_css108.py --arm <new-arm-source> --gcc <host-gcc> --out <new-host-output>
python -B tools/test_nes_css108.py --arm <new-arm-source> --gcc <host-gcc> --out <new-control-output> --mutation <nconfig|sticky|disarm|nmi-owner>
```

ARM 빌드는 기존 tools/build_nes_lower100_arm.ps1에 새 source와 고정 mini를 전달한다. obj-nes-100이라는 디렉터리 이름은 공용 builder의 역사적 이름이며 실제 VERSION은 CF86-CSS108이다. 새 FPGA 빌드나 라이선스 smoke test는 필요하지 않다.

```text
python -B tools/check_nes_css108_arm.py --arm <linked-arm> --host <host-output> --objdump <arm-objdump> --out <new-arm-check>
```

고정104의 manifest/전체 준비 소스와 이번 public source를 검사한다. private frozen104가 필요하므로 공개 clone만의 완전 재현이라고 주장하지 않는다. 원래 archive에 덮어쓰지 않는다. MinGW DLL 오류는 기존처럼 허용된 실행 환경에서 처리하고 원시 실패를 보존한다.

63개 검증은 실제 CSS/runtime C 및 return predicate/reset 본문을 사용한다. 다른 FatFS/file 함수는 제외했다. 이벤트 주입은 활성화11개·해제6개 MMIO 경계 전후34건이며 모든 ARM instruction 경계의 NMI 증명은 아니다. 호스트 seam은 MMIO/NVIC/CSSF/terminal loop만 모델링한다. 생산본에는 store/read 매크로가 직접 MMIO로 전개된다. NMI first fault는 report가 아니라 별도 정렬32비트 scalar이며 이전 return reset으로 해제되지 않는다.

arm-check04는 동일 unit 소스와 최종 ARM의 강한 NMI 심볼, firmware offset0x208 vector word, stop의 직접 store/장벽/무호출/무복귀 및 lifecycle call 순서를 확인했다. 숫자를 MCU 시간으로 환산하지 않는다. 최종63/4/ARM 연결을 전체 native 세션 또는 실기 성공으로 대체하지 않는다.

다음 통합에서는 기존 native 모델의 config pin/READY 별칭을 실제 PA1/PB8과 혼동하지 말고 변환 근거를 기록한다. 새 CSS 때문에 기존 모델에 필요한 상태를 무조건 참으로 덮어쓰지 않는다. 활성화/해제·정상 반환·진입 거부·늦은 고장을 구분한다. ARM108로 pair를 갱신할 때 기존105의104 해시를 수정하지 말고 새 조합을 만든다.
