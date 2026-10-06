# H1 037 외부 버스 검토와 실기 진입 범위

037은 RTL/MCU/ROM 수정 없이 035 MCU + 036 FPGA의 실기 묶음을 만든다.
[시험 안내](nes-h1-bringup-test.ko.md), [결과](../analysis/H1-BRINGUP-RESULT.ko.md).

## 확인한 설계 조건

고정한 sd2snes upstream cf7e21d7a5978fcd74981d71c3cfbf6e982a4dd1의
verilog/sd2snes_base/main.v 1189–1219와 비교했다. OE는 active-low,
DIR=0은 SNES→FPGA, DIR=1은 FPGA→SNES이며 IRQ의 비활성 출력은 0이다.
H1 top은 같은 극성과 기존 GBC135핀 배치를 사용한다. 외부 ROM/RAM의 쓰기·선택은 비활성이다.
원문 발췌와 파일 해시는 local-h1-bringup-037/stock-pad-*에 보존했다.
이 비교로 실제 Mk.III 트랜시버 부품·전파 지연을 알아낸 것은 아니다.
구형 RevF 회로의 부품을 현 보드 부품이라고 가정하지 않았다.

STOP 또는 raw PLL lock 상실은 SNES 출력 허용을 끊는다. 클록이 정지한 상태의 lock 상실도
036 및 이번 RTL 시험에 포함한다. MCU는 설정/ARM까지 실제 SNES RESET을 유지하도록 구현됐다.
물리 RESET의 최초 동작, PLL lock 아날로그 특성, warm 복귀는 이번 실기에서 관찰한다.

## 추가 실제 Questa 실행

036과 바이트 해시가 같은 boundary를 사용했다. 84MHz에 대해 시작 위상 0…11ns를
1ns씩 바꾸고 두 조건을 각각 실행했다(24회, 각 6조건).

|모델 조건|주소 setup|RD/WR low|주소 hold|idle gap|수신 지연|
|---|---:|---:|---:|---:|---:|
|기존 폭 + 실제 수신 허용|20ns|180ns|20ns|100ns|0ns|
|좁힌 폭 + 데이터 해제|0ns|120ns|0ns|48ns|15ns|

FPGA 쓰기 입력은 OE 수신 허용 중에만 보이며 종료 후 Z가 된다. 쓰기 데이터는 처음에는
다른 값이고 마지막60ns에 올바른 값으로 바꿔, 처음 값이 아닌 마지막 안정 값을 받는지 검사했다.
모든 회차에서 ROM512바이트, payload8192바이트, ARM/STOP, ROMSEL 제외,
세대/재진입, 정지 클록의 PLL loss를 확인했다. 합계 ROM12288/payload196608바이트 exact.
원본 시험에서 물려받은 CASE 이름에는 full_64KiB가 남지만 이번 반복 수는512다.
전체65536바이트 검증은036의 기존 결과이며 이번 결과와 합쳐 재실행이라고 부르지 않는다.
첫 컴파일은 시험대 신호 선언 순서 오류로 실패했다. 첫 driver/compile.log를 보존하고 수정했다.

이 수치는 시험 입력이다. 실제 SNES CPU/DMA의 최소 펄스나 트랜시버 최대 지연으로 쓰지 않는다.
게이트/SDF 지연, 데이터 비트별 skew, metastability, 경합 전류를 모델링하지 않았다.
주소/데이터는 bundled 샘플이며 일반 비동기 다중 비트 전송의 안전성을 증명한 것이 아니다.

## 물리 타이밍의 남은 범위와 결정

036 최종 배치 Slow1200mV85C의 inventory는 raw SNES→OE/DIR/data24.278ns,
SNES→register12.663ns, register→SNES18.091ns다. 서로 다른 경로의 최댓값을
임의로 더해 setup slack 또는 전체 보드 응답 상한이라고 부르지 않는다.
38입력/11출력 미제약은 남는다. 실제 RD release→다음 host drive 간격과
트랜시버 disable/enable/DIR skew가 없으므로 break-before-make를 수치로 보장할 수 없다.
OE/DIR을 동시에 바꾸는 raw 논리는 디지털 회귀 통과와 별개로 이 검토를 필요로 한다.
SDC, false-path, 배치, 이미지에는 이번에 변경이 없다. 정확한 회로/부품과 계측을 얻으면
그 근거로 IO delay·turnaround·CDC 제약을 정하고 다시 검증한다.

사용자의 실기 우선 요청에 맞춰 다음 단계는 기존에 GBC가 동작한 동일 대상에서
백업 가능한 짧은 H1 진입/화면/RESET 실험으로 정한다. 패키지 준비 완료와 전기적 signoff를
분리한다. 미확인 타이밍을 통과로 처리하거나 실기 첫 관찰을 무기한 기다리는 전제조건으로
두지 않는다. 실패하면 즉시 원복하고 관찰된 실패 구간을 다음 수정의 근거로 삼는다.

## 설치 도구 검증

고정 세 경로만 변경한다. 기존 C44 firmware.stm/GBC 해시를 확인하고 원본 백업 및 읽기검증을
완료한 뒤 FPGA→표식→MCU 순서로 쓴다. 복원은 MCU부터 처리하고, 예상과 다른 현재 파일은
덮어쓰지 않는다. symlink/reparse 경로와 SD 내부 백업은 거부한다. 자동 드라이브 선택은 없다.
기본 FPGA·GBC·메뉴·세이브는 교체 대상이 아니며 base/GBC/menu 해시는 유지 여부를 검사한다.

실제 파일시스템의 합성 SD 폴더에서12조건 통과: 읽기만 검사, 추가/기존 파일 원복,
반복 복원, FPGA 복사 뒤 설치 중단, 알 수 없는 펌웨어, SD 내부/기존 백업,
설치 후 대상 변경, 손상 백업, 다른 SD 경로, base 변경, 패키지 변조.
기존 C44 데이터만 fixture와 해당 해시 상수로 대체했으며 설치 후보의 실제 바이트·해시와
도구 파일시스템 동작은 그대로다. 실제 SD 쓰기·전원 손실·실물 MCU 부팅 시험은 아니다.
