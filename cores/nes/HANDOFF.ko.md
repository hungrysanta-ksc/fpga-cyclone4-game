# NES 다음 작업 인계 — 059 이후

현재 후보는 **NES-SPI-READBACK-059**. [결과](../../analysis/SPI-READBACK-RESULT.ko.md)와 [59 프로토콜 계약](../../docs/nes-spi-readback-contract.md)을 먼저 읽는다. 실기044·056 SD 복구 경로는 유지하며 새 SD 이미지는 없다.

## 완료한 경계

- 058 reader를 공유하는 SPI CHECK/READ/ACK/FINISH와 held data/tag를 구현했다. 한 번에 하나의 요청과 순서별 ACK만 허용한다. STATUS 수신 offset으로 tag를 대체하지 않는다. 미검증 START는 오류다. CHECK 종료 뒤 별도 START 프레임까지 reader 공통 reset 구간이 있다.
- MCU가 승인 입력 callback과 실제 반환 바이트를 모두 비교하고 tag/timeout/상태를 검사한다. host 두 전체 길이180224바이트와10오류 시험,비교 제거 mutation 예상 실패가 확인됐다. source 오류 시 STOP 확인이 안 되면 caller가 기존 base 복구 보호를 유지해야 한다.
- 149제어 검사/18오류와 실제 C GPIO5656응답 비트/32바이트/오류 STOP이 통과했다. 파형용80KiB 준비는 loader 입력 stimulus로 실제 핀 쓰기이며 SPI DATA 적재가 아니다. 전체 SPI DATA/CHECK는 별도 실제 코어 회귀에서96/80KiB 모두 실행했다.
- 실제 코어2종8프레임/491520픽셀/packet과 모든 S/E/F/D trace가057과 사례별 상수 시각 차이로 일치한다. RUN4클록 응답 마감은 유지한다. testbench만 reset-held host/queue 클록을 마스킹하며 제품 클록 gate는 없다.
- 새 공동14180LE/959LAB/5203레지스터/26M9K,963LAB 중4여유다.288가상핀/22미배치/PLL0이며 전체 보드/STA 통과가 아니다.
- ARM 전체 링크에 두 새 함수가 남아 있지만 **미호출**이다.056의54 SD 경로는59 검증 함수를 호출하지 않는다. 컴파일 전용 이미지를 SD에 설치하지 않는다.

## 다음 순서

1. SD 승인 source callback과59 load/query를 묶는다. 기존056 CRC/파일 검증과 GPIO·USB·RESET 보호를 보존하고 load→verify→STOP/복구를 host/C GPIO로 검사한다. 원본 재읽기는 버퍼링하고 헤더·크기·전체 CRC·close 성공까지 승인한 뒤에만 FINISH하도록 한다. 변경된 SD 내용을 새 승인 원본으로 오인하지 않는다. 길이 완료를 물리 무결성 완료로 표시하지 않는다. 응답이 불확실한 DATA/ACK를 무조건 재전송하지 않는다.
2. CPU/PPU RUN 없는 자체 load/verify/STOP 진단을044 기반 실제 보드에 연결한다. 해당 범위의 핀·클록·PSRAM 타이밍·전체 physical fit/복구를 검증하고 새 MCU/FPGA 쌍·표식·로그·rollback을 준비한다. 이 진단은 전체 NES 소비자 구현을 기다리지 않으며, 통과해도 일반 게임 실행 성공이 아니다. 기존044와 GBC를 보존한다.
3. 전체 코어 보드 자원·클록·핀과 SNES 소비자 경계를 구체화한다.4LAB만 남으므로 추가 비용을 실제 공동 fit로 확인하고 필요하면 의미가 같은 면적 개선을 차등 검증한다. SNES_SYSCLK/PIN_A9는 여전히 미확인 후보다. 소비자/프레임 마감/CDC/STA 뒤 전체 RUN 실기 단계로 넘어간다.

두 실기 경로 모두 메뉴 진행·취소·종료 이유와 복구를 명확히 한다. 현재 byte별 검증의 추가 시간은80KiB 약68.3초/96KiB 약82.0초로 추정되므로 사용자에게 무응답 화면을 남기지 않는다. 추정값은 실기 측정이 아니다.

044 실기와 GBC 및 과거 원시 근거는 보존한다.059 초기 literal·선언 순서 컴파일 실패,성능 조정용 수동 중지,Make dependency 최초 실패도 지우지 않는다. 한 FLOAT seat를 순차 사용하고 wrapper가 종료하게 한다. [재현](REPRODUCING.ko.md)과 [주요 진전 관리](../../docs/development/MILESTONE-WORKFLOW.ko.md)를 따른다.
