# NES061 물리 진단 경계 결과

**CPU/PPU 없는 적재·읽기 비교 진단을 실제135개 핀과 보드 클록에 연결했다.** 현재 후보는 NES-BOARD-DIAGNOSTIC-061이며 설치 이미지는 없다. [계약·재현](../docs/nes-board-diagnostic-contract.md), [실행 해시 요약](board-diagnostic-verification.json).

## 구현과 시험

044 SNES 경계의84MHz PLL을 보존하고 SPI/PSRAM만 실제8MHz 입력 클록에 연결한다. 모델에서3클록 읽기/쓰기는375ns이며1클록 쓰기 hold는125ns다. 기존25ns 모델보다 느린70ns access/35ns output-disable/최소350ns write 모델을 사용했다. 실제 장착 메모리 사양을 확인한 것은 아니다. 일반 NES 실행을 느리게 한 변경이 아니며 CPU/PPU는 아예 포함하지 않는다.

START는 verified 상태와 무관하게 오류8로 거부하고 boot start도0으로 고정한다. CF=61 물리 후보 ID를 추가하며 F0=A5/F1=44/protocol59는 유지한다. 기존060 C·메뉴 코드는 변경하지 않았다.

| 증거 | 결과와 범위 |
| --- | --- |
| C GPIO 적재 → 실제 top RTL |33184샘플/29024응답 비트 일치,256바이트 핀 쓰기,SD 오류→STOP |
| C GPIO 비교 → 실제 top RTL |49472샘플/43288응답 비트 일치,256 READ/ACK,SD 오류→STOP |
| 비교 입력 준비 |96KiB를 testbench loader 입력으로 실제 메모리 모델 핀에 기록. 전체 C SPI 적재 재생은 아님 |
| 복구/격리 |두 START 방어,PLL lock idle/쓰기 중 상실,두 클록 정지에서 핀 고임피던스·비선택,상태 폐기와재취득,CF/F0/F1·주변장치 idle |
| 잘못된 설계 대조 |84MHz 오접속→write pulse 실패,START parser 허용→거부 검사 실패,boot start 재연결→Unexpected RUN 실패 |
| 물리 fit |2386 LE,186/963 LAB,1458 registers,44/56 M9K,135실제 핀/0가상핀,PLL1 |
| 내부 STA |두 클록·3corner의 setup/hold/recovery/removal/pulse-width30검사 모두 양수.최소setup2.301ns/hold0.131ns/recovery4.946ns/removal1.124ns/pulse5.607ns |
| 외부 타이밍 |입력54포트/744경로,출력49포트/1337경로 min/max 미제약. 외부 IO signoff 미완료 |

최종fit03과wave02의 합성 대상 SV 해시가 일치한다. 실제 FPGA PLL은 fit에 포함하지만 RTL 파형 시험은 디지털 PLL stub을 쓴다.044 frontend/transport와과거 소스·GBC 해시는 보존한다. 이번에는 ARM을 다시 빌드하지 않았고060의미호출 진입점 근거를 유지한다.059 전체 코어959LAB/4여유 및마지막8프레임 근거는 별도이며061 작은 진단 fit와합산/대체하지 않는다.

## 보존한 실패와 다음 경계

초기fit01은 생성 변환의 중복 start 문자열 assertion에서 중단되어 Quartus를 실행하지 않았다. fit02는 배치 성공 뒤84MHz lock-release FF→8MHz verified 경로에 hold−0.487ns가 있었다. 원시 실패를 보존하고각영역 독립 리셋 해제로 수정한fit03을 검사했다. 도구 exit0을 STA 통과로 간주하지 않는다. wave01은 이전 reset 연결,최종wave02는수정된연결이다.

첫 fast-memory 대조는 의도한 write-pulse assertion을 실제로 발생시켰지만 Questa가 exit0으로 끝나 결과 수집기가 이를 처리하지 못했다. 로그의 원인 assertion을 확인하도록 수정한두번째 실행과첫실패를 모두 보존한다. 정상 시험은 Fatal/Error transcript와완료 marker를함께검사한다.

실기진입 전에 실제 보드/PSRAM 규격·외부 IO 타이밍을 확인하고,CF61 확인·메뉴 표식·대기/결과/로그·취소/재진입·base 복구와짝맞는MCU/FPGA 패키지를 마쳐야 한다. RESET 유지 중표시 방법과기존fpga_pgm panic도남아있다. ASM/설치파일을 만들지 않았고044/GBC를 그대로 유지한다.
