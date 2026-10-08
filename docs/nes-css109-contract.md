# NES109 재현 계약

고정104/108을 읽기 전용 입력으로 사용하고 매 실행마다 새 출력 디렉터리를 지정한다. 공개 clone만으로 private 원시 자료까지 재현할 수 있다고 주장하지 않는다.

```text
python -B tools/test_nes_css109.py --evidence104 <frozen104> --evidence108 <frozen108> --gcc <host-gcc> --out <new-normal>
python -B tools/test_nes_css109.py --evidence104 <frozen104> --evidence108 <frozen108> --gcc <host-gcc> --out <new-96> --geometry96
python -B tools/test_nes_css109.py --evidence104 <frozen104> --evidence108 <frozen108> --gcc <host-gcc> --out <new-fault> --cases 1,2,3,4,5,6,7,8,9,10,11,12,20,21,22
```

대조는 --mutation begin/end/nconfig/sticky에 --cases 20/0/4/4를 각각 전달한다. expected assertion이 있어야 통과하며 원시 compile/case 로그를 보존한다. 실제 CSS source는 변하지 않고 대조 출력의 복사본만 바뀐다.

새 조합 준비는 통합 결과 디렉터리 normal02/fat32-96-01/fault03/negative-{begin,end,nconfig,sticky}-01을 계약상 입력으로 받는다. 새 실행을 사용할 경우 실행 출력 이름을 이 계약에 맞춘다. 입력 로그 digest,108 source 및105/108 archive를 확인한다.

```text
python -B tools/prepare_nes_pair109.py --evidence105 <frozen105> --evidence108 <frozen108> --integration <integration-parent> --out <new-pair>
python -B tools/test_nes_pair109.py --review <new-pair> --out <new-pair-tests>
python -B tools/verify_nes_css109.py --evidence <frozen109>
```

NMI longjmp는 호스트 종료 경로를 검사하기 위한 seam이다. 이후 호출은 테스트의 재진입/고장 유지 검사이며 실제 NMI가 일반 코드로 복귀한다는 뜻이 아니다. 표준 출력은 호스트 fprintf, 제품 UART는 실제 억제 경로로 분리한다. RCC/핀 초기값은 부팅 이후 전제이며 실측이 아니다. 정상 완주와 sampled fault 지점을 모든 IRQ/ARM interleaving으로 확장하지 않는다.

E1/E2, installable/hardware_trial/start/both_clock_halt_safe는 false를 유지한다. 이번에는 실제 파일 조합을 식별할 뿐 SD 복사·설치·게임 START를 하지 않는다. 105 pair나044–109 archive/finalizer 재작성 금지.
