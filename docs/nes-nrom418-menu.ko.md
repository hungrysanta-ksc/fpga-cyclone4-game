# NES418: 제한 NROM 메뉴와 자체 부트 fixture

407 후보 loader의 실기 진입을 위한 별도 227 메뉴 소스를 만들었다. 호출 경로는 `/sd2snes/nes/nrom16.nes`와 `/sd2snes/fpga_nrom16.bi3`이며 fixed NROM16 수평·ID78 후보 전용이다. 원본 227 파일을 바꾸지 않고 `probes/nes-nrom418/menu01`에 생성한다. 자체 제작 24,592B iNES fixture는 16KiB PRG와 8KiB CHR-ROM을 가지며 reset/IRQ/NMI 벡터를 합법적인 부트 무한 루프로 지정한다. 이 fixture는 화면·입력·음성을 증명하지 않는다.

`arm01`은 227 firmware source 사본, 407 loader 및 위 메뉴 source로 증분 전체 링크를 통과했다. ELF text 200,061B, data 10,040B, BSS 18,076B. 링크된 ELF에서 새 NROM 두 경로의 존재와 기존 227 두 경로의 부재를 확인했다. 이 결과는 실행 시험이 아니다. 새 이름의 FPGA 이미지와 65816 artifact는 아직 패키지되지 않았고 실제 메뉴 선택·보드 display·STOP/base 복구·Lite FIT/STA는 미검증이다. production227 및 기존 복구 자료는 그대로 둔다.

전체 411 시뮬레이션은 별도로 readback 진행 중이며 이 메뉴 변경은 포함하지 않는다. 다음은 same-source 보드 image와 65816의 실제 paired artifact·identity 확인, 의미 있는 표시·입력 fixture 준비, 단일 Lite FIT/STA 및 대표 observer 시험이다. 이 중 어떤 것도 이 문서로 완료된 것으로 취급하지 않는다.
