# NES 다음 작업 인계 — 063 이후

현재 **NES-BOARD-SESSION-063**. [전체 세션 결과](../../analysis/BOARD-SESSION-RESULT.ko.md), [계약·재현](../../docs/nes-board-session-contract.md), [공정 가이드](../../docs/development/NES-HARDWARE-READINESS-REVIEW.ko.md). PR16은2026-10-07T01:28:46Z 병합됐고 master `b8e22a3c1df168708a071c0ce29b909c73cf6bdb`에서 진행했다. 044 실기/GBC 기준을 보존한다. 실제 STM32·SD 실행이나 설치 쌍은 아직 없다.

## 완료한 경계

- 062 실제 수동 메뉴 C에서80/96KiB 파일을 읽어 전체 DATA→CHECK→마지막 ACK→FINISH→STOP와 base 복구까지 통과했다. 활성 SPI 프레임의 GPIO 전환·샘플 시점을 검사한 압축 트랜잭션 기록을 보존한다. 프레임 바깥 GPIO 복원과 base 설정/메뉴 복구는 host 모형이며 보드 재생은 STOP 후 진단 top에서 끝난다.
- 이 기록을 061 보드 top의 물리 핀 모형에 재생했다. 총180,224 핀 바이트 쓰기/읽기/ACK,50,464,224응답 비트가 일치했다. 초기화하지 않은 RAM에 SPI DATA로만 적재하고 모든 주소/chip/쓰기 lane/읽기 word enable 및 최종 RAM 내용을 확인했다. CPU/PPU와 START는 없다.
- 8MHz SPI decoder와 PSRAM 클록은 전체 시간 동안 동작했고 C의2µs 지연을 단축하지 않았다. 디지털84MHz 미사용 legacy/H1 영역은 ID3개 확인 뒤 테스트에서 멈췄다. 원래 클록64프레임/29핀바이트와 legacy를 멈추지 않은8,192프레임 대조를 기록했다. 전체 보드 클록/아날로그 PLL 검증으로 확대하지 않는다.
- 생산 RTL14개는061fit03과 같다. ARM062 overlay10개와 공개 기준 헤더3개도 같다. 새 fit/ARM 실행 없이2386LE/186LAB/1458regs/44M9K/135핀/PLL1·내부 최소0.131ns 및 호출되는062 ARM을 재사용한다. 062의 bounded CHECK/STOP·START 방어/PLL-loss·host 실패 회귀도 같은 생산 소스에 한정해 재사용한다.
- 062 표식 `NES VERIFY 062 80.nh1`/`NES VERIFY 062 96.nh1`, CF61/F0A5/F144/protocol59,3개 메뉴 호출·준비 guard·늦은 UART/SD 로그는 그대로다. 새063 설치 표식을 만들지 않았다. PREPARED/RELEASE 코드 경계는 실제 화면 복귀 관측과 다르다.

## 다음 구현·검증 순서

1. 관측·정지 복구를 실제 하위 호출까지 연결한다. 고정 STM32 소스에 ready/read/write LED와 API가 있지만 panic은 반복 루프이며 CLI를 호출한다. `fpga_pgm`은 일부 오류에서 panic하고 SD `wait_busy()`에도 반환 상한이 없다. 함수 바깥 timeout만 추가하지 않는다. 진단 전용 복구 가능한 설정 경로·SD 대기 상한과 오류 전달·RESET/USB/SD 보호·LED/UART 단계 표시를 설계하고 시험한다. RESET 중 패드/외부 RESET 입력을 구별할 수 있다고 가정하지 않는다.
2. **FXPAK Pro / Mk.III, STM32 + EP4CE15F17C8은 README/등록부에 이미 고정된 대상**이다. 제품명을 다시 질문하지 않는다. 과거 계약의 Rev.D와 실제 revision 관측은 구분한다. 기존 PSRAM 총16MiB/16비트/70ns 표기와 두 CE/ZZ 핀은 확인했으며, 정확한 부품·speed grade 및 tOE/tWP/tDS/tDH/tHZ min/max/BOM·회로 대응은 자료가 부족하다. [가이드의 대상 사양](../../docs/development/NES-HARDWARE-READINESS-REVIEW.ko.md#확정된-개발-대상과-추가-확인-항목)을 먼저 확인하고 기존 hwinfo/로그·upstream 자료를 조사한 뒤 부족한 항목만 문의한다. 외부 IO min/max/turnaround를 닫으며 70ns 모델이나 GBC 실기를 전체 사양 증명으로 쓰지 않는다.
3. 부품·외부 IO 검토를 닫은 뒤 최종 ARM/FPGA ASM·압축 roundtrip·쌍 manifest·SD 원본 백업과 rollback을 묶는다. 소스/제약이 바뀌면 필요한 영향 검사와 최종 동일 후보 검증을 수행한다. CF61만으로 파일 동일성을 판정하지 않는다.
4. 가독성 있는 관측표로 제한된 적재/비교/STOP/base·메뉴 복귀/재진입/RESET·전원/GBC 복귀를 실제 기기에서 확인한다. 일반 게임 소비자 완성을 이 진단의 선행 조건으로 추가하지 않는다.

현재 점검표는 완료5/부분5/미완료2다. H10은 현재 소스의 디지털 적재 전용 통합 범위에서 완료됐으며 최종 변경의 영향을 다시 확인한다. 일정·공수·제품 완성률이 아니다. 관측/종료H08과 외부 IO H06는 미완료다. 전체 NES의959LAB/4여유,소비자/CDC/STA와 마지막8프레임은 별도 상태다.

## 증거와 보존

063 로컬 원시 근거는 `probes/nes-board-session-063/`의 동결 manifest다. 첫 clock input force의 공유 net 영향, 첫 전체 시험의 잘못된 읽기 lane 기대값을 보존했다. prefix 대조는 읽기 monitor 수정 전이며 해당 prefix에는 읽기가 없었다. 반복 입력 trace는 동일 해시의 host02 원본 한 벌과 명시적 link 기록으로 보관했다. 첫 ARM 재사용 검사에서 overlay archive에 없는 기준 헤더3개를 찾던 오류는 archive 생성 전에 수정했다.

`probes/finalize_nes063.py`와 status 갱신을 동결 archive에 다시 실행하지 않는다. 044–062 원시 근거·manifest·과거 finalizer도 변경하지 않는다. FLOAT는 기존 wrapper를 순차 사용하며 라이선스 smoke나 inherited uncounted 경로를 반복하지 않는다.
