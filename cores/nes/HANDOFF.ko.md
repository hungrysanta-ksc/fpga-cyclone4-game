# NES 다음 작업 인계 — 062 이후

현재 **NES-MENU-DIAGNOSTIC-062**. [결과](../../analysis/MENU-DIAGNOSTIC-RESULT.ko.md), [계약·재현](../../docs/nes-menu-diagnostic-contract.md), [전체 공정 가이드](../../docs/development/NES-HARDWARE-READINESS-REVIEW.ko.md). PR15는2026-10-07T00:51:01Z 병합, master `39e831aaf045fd0f668f8b30b0482dbded2558fb`에서 진행했다. 044 실기/GBC를 보존한다. 새 설치 SD 이미지나 물리 실행은 없다.

## 완료한 경계

- `NES VERIFY 062 80.nh1`/`NES VERIFY 062 96.nh1`은 고정 승인 SD 진단을 선택한다. 044 표식과 이미지 경로를 분리하고 NH1 autoboot NACK을 유지한다. 표식/헤더 형상이 다르면 설정 전에 거부한다.
- 새SD함수는 CF61/F0A5/F144/protocol59와idle/count0을 확인한 후 BEGIN한다. 060 CRC/close/전체 비교/순서ACK/FINISH/STOP/base 보호와 재전송 금지를 보존한다. 실제C host41SD/18입력 거부/16메뉴 세션 및2검사 제거 대조가 통과했다.
- 파일 선택/최근/즐겨찾기의3메뉴가 새함수를 호출한다. 최종ARM disassembly로 실제호출을 확인했다. 단순미호출symbol유지가 아니다. menu size/SRAM 검사 뒤 RESET해제를 허용하고 실패 시 fail closed한다.
- UART 안내/최종결과와안전복구 후별도SD로그를 추가했다. 로그4오류는복귀를막지않고USBIRQ원래상태를복원한다. base실패 시보호유지/SD쓰기금지. PREPARED와RELEASE경계는실제화면복귀관측과다르다.
- C→061 보드top: 적재29032응답비트/256핀바이트,비교43288비트/256ACK,SD오류STOP. CHECK96KiB 준비는TBloader핀쓰기다. START이중방어·PLLloss검사 유지. 한FLOAT wrapper정상종료/listener0.
- 061 합성SV동일성으로fit03재사용:2386LE/186LAB/1458regs/44M9K/135핀/PLL1,내부최소0.131ns. 외부54입력/49출력미제약.059전체코어959LAB/4여유·마지막8프레임과구분한다.

## 다음 구현·검증 순서

1. RESET유지 중 가능한 실제관측 수단을 정하고 읽을수있는 실행전 안내/결과를 연결한다. 지금은UART/SD로그뿐이며화면/진행률/취소입력은없다. 기존fpga_pgm panic/FatFS블로킹호출의종료·보호·재시작정책을구현/시험한다. 외부RESET/패드가구별된다고가정하지않는다.
2. **FXPAK Pro / Mk.III, STM32 + EP4CE15F17C8은 README/등록부에 이미 고정된 대상**이다. 제품명을 다시 질문하지 않는다. 과거 계약의 Rev.D와 실제 revision 관측은 구분한다. 기존 PSRAM 총16MiB/16비트/70ns 표기와 두 CE/ZZ 핀은 확인했으며, 정확한 부품·speed grade 및 tOE/tWP/tDS/tDH/tHZ min/max/BOM·회로 대응은 자료가 부족하다. [가이드의 대상 사양](../../docs/development/NES-HARDWARE-READINESS-REVIEW.ko.md#확정된-개발-대상과-추가-확인-항목)을 먼저 확인하고 기존 hwinfo/로그·upstream 자료를 조사한 뒤 부족한 항목만 문의한다. 외부 IO min/max/turnaround를 닫으며 70ns 모델이나 GBC 실기를 전체 사양 증명으로 쓰지 않는다.
3. 최종C와보드top에서80/96KiB 전체SPI DATA→CHECK→마지막ACK/FINISH/status→STOP 성공을실행한다. 현재전체C성공은host모형이고보드파형은bounded오류회복이다. 이를합쳐전체실기성공으로쓰지않는다.
4. 최종FPGA ASM·압축roundtrip·ARM과짝manifest,현재SD해시/백업/rollback/재진입/GBC복귀관측표를고정하여제한된실기로진입한다. CF61은바이너리SHA확인을대신하지않는다. 일반게임소비자완성을선행조건으로추가하지않는다.

최초실기준비12항목은완료4/부분6/미완료2이며일정/공수/제품비율이아니다. H11은호출되는ARM완료로부분완료가되었지만쌍패키지는없다. SPI지연합113.9/136.6초는전체실측/timeout상한이아니다. 전체NES resource/consumer/CDC/STA는4LAB여유아래별도로계속한다.

## 증거와 보존

062 원시근거는로컬 `probes/nes-menu-diagnostic-062/`의309파일manifest. 첫host루프변환assertion,첫candidate대조수집target오류,첫menu대조미사용인자compile실패,초기finalizer syntax실패를보존했다. 최종host/ARM 생성C가같으며061생산SV해시가일치한다. `probes/finalize_nes062.py`와status갱신을동결archive에다시실행하지않는다. 044–061 원시근거·manifest·과거finalizer도변경하지않는다.
