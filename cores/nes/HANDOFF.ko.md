# NES 다음 작업 인계 — 061 이후

현재 **NES-BOARD-DIAGNOSTIC-061**. [결과](../../analysis/BOARD-DIAGNOSTIC-RESULT.ko.md), [계약·재현](../../docs/nes-board-diagnostic-contract.md).044 실기와GBC를 유지한다.061은 설치 후보가 아니며 새 SD 이미지가 없다.

## 완료한 경계

- PR14의060은 병합됐다. 승인된 SD 적재/재읽기/CRC·close 뒤 FINISH/STOP·base 복구와미호출 ARM 진입점은 그대로다. 재전송 금지·복구 실패 시 RESET/USB 보호를 유지한다.
-061은 CPU/PPU 없이135개 물리 핀,8MHz 입력/84MHz PLL,PSRAM을 연결한다. 메모리만8MHz:3클록 읽기/쓰기375ns,hold125ns. 실제 NES 실행 경로를 늦추지 않는다.
- START parser는항상오류8,boot start도0. protocol59,F0=A5/F1=44 유지,별도CF=61. CF 확인은 아직 MCU 미연결이다.
- C GPIO 적재29024비트/256핀바이트,비교43288비트/256ACK,SD 오류STOP 통과. 비교96KiB 준비는testbench loader→핀 쓰기이며전체 C SPI 적재가아니다. 디지털 PLL stub,70ns/35ns/350ns 모델을 실제 부품 사양으로 부르지 않는다.
- PLL loss에서각영역이비동기assert/자기클록release한다. 두클록정지·쓰기중abort에서비선택/고임피던스과복구를검사했다. abort된ROM은폐기한다. 잘못된84MHz/두START방어제거3대조가정확한assertion에서실패한다.
- fit03:2386LE/186LAB/1458registers/44M9K/135physical/0virtual/PLL1.3corner30개내부slack최소0.131ns. 외부54입력/49출력포트는미제약. 전체코어의059959LAB/4여유·마지막8프레임은별도근거다.

## 다음 구현 순서

1. 실제 사용 보드/PSRAM 부품과규격·회로의전압/ZZ·CE/lane배선을확인하고외부IO min/max/turnaround를닫는다. 사용자에게제품명/리비전/부품명을문의했으며확인된답은아직없다. 기존70ns표기나동작중인GBC를근거로사양을추정하지않는다. 이정보가없어도메뉴/복구의host개발은진행할수있다.
2.060을CF61 확인과동기메뉴흐름에연결한다. 읽을수있는후보/대기/성공·실패/로그·취소·재진입을준비한다. RESET유지중표시방법,fpga_pgm panic/timeout,base복구실패시보호를검증한다. 추가CHECK68.3/82초는계산값이지실기측정이아니다.
3. 같은후보MCU/FPGA쌍,해시·backup/rollback·관측절차후제한된실기로간다. 일반게임성공으로확대하지않으며완성NES소비자를기다릴필요는없다.
4. 전체코어resource/consumer/CDC/STA는4LAB여유아래별도로진행한다. CPU감속/프레임드롭으로통과시키지않는다.

061 실패를보존한다:fit01 변환중복assertion,fit02 lock_release84→verified8 hold−0.487ns,수정fit03. wave01은이전reset연결,최종wave02는fit03과SV해시일치. 첫fast-memory는예상Fatal을냈지만exit0이라수집기가실패했고두번째에원인문자열로판정했다. 정상시험도exitcode만보지않는다. 한FLOAT seat를순차사용했고wrapper가모두종료했다. 과거동결finalizer를재실행하지않는다.
