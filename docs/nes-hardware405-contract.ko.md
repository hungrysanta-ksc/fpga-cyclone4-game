# NES405: production227 조사와 제한 NROM 실기 진입 경계

PR132 병합 `935b7bf4b4243c8881fb443a732ba167ce82fce4`가 origin/master에 반영된 뒤 시작한 조사다. 실제 파일을 읽고 해시를 대조한 결과이며 새 비트스트림, 실기 실행, mapper 구현이나 새 60fps 측정은 없다. 목표는 제한 NROM과 지속 60fps를 구분해 다음 구현의 판정 경계를 만드는 것이다.

## 가장 중요한 정정: 227은 이미 SMB3 실기 기록이 있다

PR132 회고의 “실기 성공을 가정하지 않는다”는 확인 전 지침이었다. 확인 결과 **227은 사용자의 실기에서 SMB3 실행·화면·소리·조작·메뉴 복귀가 관측됐다.** 60.06초에 최종 표시 ACK 465회, 전체 구간 평균 7.74회/초였다. 스크롤 구간의 정확한 FPS나 60fps는 아니다. 로그상 ROM 393,216B 적재/비교, RUN, STOP, base 복원과 메뉴 준비가 통과했고, 종료의 receiver24는 마감 전후 어느 D2 구간인지 원시 응답 부족으로 확정하지 않는다. 원본 3개 로그는 [실기 분석](../analysis/game227-hardware01-verification.json)의 해시와 일치한다. 확인된 사용자 보고의 범위를 과장해 무결성·장시간 플레이·모든 게임을 승인하지 않는다.

[로컬 ZIP](../../probes/nes-repeat227/release01/NES227-SMB3-OAMREPEAT.zip)은 기존 release JSON의 SHA-256 `ff115bcc57f6019e8b73fe824967f3a7bb5ec283117769fb18101f532a7ccd76`와 일치한다. ZIP 안 paired `firmware.stm` 209,828B (`b8adf26e…ffd0eca`)와 `fpga_n227.bi3` 361,663B (`f26d7e6d…e5a9586`)는 각각 실제 `arm01`/`asm02` 빌드와 바이트 해시가 같다. 164 복원 firmware·FPGA와 base도 기록된 해시와 일치한다. 게임 ROM bytes는 읽어 공개·복사하지 않는다. ZIP 속 롬의 적법한 보유와 배포 범위는 이 감사가 판정하지 않는다.

227은 224 routed DB의 **ROM 내용 갱신**과 ARM 변경이다. 기존 224 전체 FIT 보고서는 EP4CE15F17C8, **15,249/15,408 LE, 961 LAB, 47 M9K**다. 227 archive의 FIT summary는 224와 바이트 동일하며 227에서 새 FIT/STA를 한 것이 아니다. 224의 3코너 setup 최소 +0.276ns, hold +0.147ns 및 조건부 IO/CDC 감사는 [224 계약](nes-counter224-contract.ko.md) 범위의 기존 증거다. 완전 전기·MTBF signoff가 아니고, 새 NROM이나 402의 타이밍 증거로 전용하지 않는다. 기존 기록에 Standard가 사용됐지만 앞으로의 신규 작업은 사용자 지시대로 **Quartus Lite**다. Standard 재시도나 구매는 하지 않는다.

## NROM 제한 시험은 새로운 구현이 필요하다

실제 227 build의 `cart_nrom.sv`는 이름과 달리 MMC3를 `flags(32'd4)`로 고정한다. 227의 실제 game loader는 iNES header PRG16/CHR16·flags `42 00`, 총 `0x60000`B와 특정 CRC를 요구하며 메뉴는 `game227.nes` 경로를 고정한다. **이것으로 mapper0 NROM을 실행할 수 없다.** 기존 unit fixture에서 “NROM”이라는 이름을 쓴 사실도 paired 보드·firmware 경로의 NROM 지원을 뜻하지 않는다.

첫 구현은 공개적으로 사용 가능한 소규모 자체 테스트 ROM의 정확한 범위와 입수·생성 경로를 먼저 고정한다. 추천 범위는 **iNES1 mapper0, PRG 16 또는 32KiB CHR-ROM 8KiB, trainer/battery/NES2 거부, 고정 미러링, CHR-RAM은 첫 범위 밖**이다. PRG16 mirror와 PRG32 주소, PPU CHR/nametable mirroring, interrupt/reset vector 및 정확한 ROM 길이/overrun을 실제 mapper·loader·메모리 배치에서 검증한다. 227의 고정 384KiB layout/service를 바꿀지 padding 할지는 실제 대조 구현과 비용으로 결정하며 CRC/identity 검사·source immutable epoch·읽기 검증을 약화하지 않는다. 보드 mapper 선택/loader/ROM service/plan의 같은 버전 결합, SRAM 주소 소유권, STOP·늦은 DONE·메뉴 복귀와 227/GBC 복원 경계를 확인한다.

타당성 검사는 다음 순서로 한다.

1. 227의 이미 검증된 실제 보드·firmware·65816 짝을 기준으로 NROM을 추가한 경계를 고정한다. FPGA mapper0 연결·loader header/length·PRG/CHR mapping과 재시작을 실제 C/RTL에서 검증하고 고정 MMC3/header가 남으면 실패다. 사용자 게임 ROM을 Git·PR에 포함하지 않는다.
2. 실제 SNES 경로에서 몇 프레임의 표시, controller 변경, audio의 지원/미지원 상태, STOP·menu 복귀를 관측할 수 있는 시험 payload와 출력/오류 계측을 정한다. 입력만 필요한 자체 NROM과 음성 시험을 구분한다. 표시 ACK는 물리 화면 검증의 대체물이 아니다.
3. 같은 candidate의 새 paired ARM/FPGA/65816 package, 정확한 build source·hash·memory/stack, SPI/ROM 소유권, reset·CDC·핀/IO, 실제 Lite FIT 및 STA를 확인한다. 기본/164 복구 파일을 따로 보존하고 사용자 데이터·save SRAM을 수정하지 않는 복구 절차를 명시한다. FIT/STA는 전체 CDC/외부 전기적 signoff와 구별한다.
4. 위 조건이 충족된 후보로 제한 실기에서 boot·그림·입력·음성 해당 여부·STOP/재시작·menu·복구 및 capture/display ID를 기록한다. 227을 똑같이 다시 실행하라는 요구는 없다. 제한 smoke는 미완료 60fps·MMC4/5를 승인하지 않는다.

실제 사용자의 현재 물리 보드/SD에 어떤 버전이 설치돼 있는지는 이 로컬 정적 감사만으로 알 수 없다. 실기 준비 당시 보드 식별자, 지역/클록, backup 및 대응 이미지 확인은 미결이다. 새 NROM hardware-ready=false.

## 60fps 후보: 전체 경계에서의 공정한 비교

| 후보 | 확인된 시간·영역 | 실제 비용/미확인 | 다음 판정 실험 |
|---|---|---|---|
| A: 402 공동 RAM record 실행기 + source/plan/SPI·raster/lease 본체 교체 | 402 모델 12 ACK·908..917 캡처 시작, 914/915 각각 1.401853/0.460335ms 추가 선행 필요. 전체 20,199LE/16,508C | 요구 deletion·새 2클록/포트 제어 미구현. 403 2,094C/1,120FF는 예산일 뿐 합성 결과가 아님 | 실제 header→record→staging→read/receipt→credit의 소유권과 VM/IO 삭제를 함께 연결. STOP·독립 검사 후 동일 위상 실제 ARM/IRQ/ROM 시간 및 전체 Lite MAP |
| B: ARM이 최종 DMA job/layout을 생산하고 FPGA는 압축 수신·검사·고정 staging, SNES는 순차 DMA | 관련 ABI 검토·부분 구현의 증거는 있으나 A와 같은 최종 경계의 새 complete 비용 없음 | 추가 ARM instructions/stack, SPI bytes·credit, 65816 setup, 고정 RAM ports와 독립 expected 생성은 공짜가 아님. 예전 구현의 MAP을 새 구조의 면적으로 사용 금지 | 402와 같은 입력의 한 완결 경로를 실제 ARM→receiver→65816→receipt/ACK로 연결하고 CRC/STOP·cold/warm/2slot 경쟁 측정 |
| C: SNES/ARM이 화면 전체를 매번 재생성·SPI로 전송 | 256×224×4bpp 28,672B를 2.625MHz SPI로 보낸다면 wire만 약 87.381ms | 압축·delta를 사용하지 않는 전제의 계산. direct FPGA나 sparse delta 전체의 불가능성 증명 아님 | full-frame 직렬안은 60fps 후보에서 제외; delta/타일 캐시는 실제 데이터·CPU 비용을 따로 측정 |
| 기존 227 | SMB3 실기 표시 ACK 465/60.06초, 당시 2.625MHz D1 payload만 평균 17.88ms/완료 | 402 모델과 시기·프레임·회로가 달라 직접 개선률을 산출할 수 없음. 장면별 비용·음성 포함 범위 차이 | paired 227을 실기 기준/복원점으로 보존, 같은 시험 반복 대신 새 후보가 생겼을 때 같은 workload와 장비로 대조 |

동일 구현·동일 source start/ROM 위상에서 초기·warm/cold·VBlank gate·다음 capture·backlog를 함께 관측한다. 914 회복시 915의 목표도 이동한다. 402 MAP의 4,791 LE 초과는 조합 함수 차이만으로 설명하거나 15,253C 달성만으로 FIT를 보장할 수 없다. A와 B 모두 새 **전체** 비용·실제 ARM/SPI/IRQ/SNES 시간은 미측정이다. 판정력이 없는 독립 FF/FSM/opcode 튜닝이나 동일 227/044 반복 실기 대신, 한쪽 후보의 실제 경계 교체가 credit과 전송 시각을 바꾸는지 우선 확인한다. 면적·기한 중 하나라도 크게 남으면 구조/기능 범위/장치 용량을 재검토한다.

## MMC4·MMC5와 ROM 경쟁: 표본 계획

376의 실제 경계 시험을 재사용한다. MMC4는 **mapper10**, SMB3의 mapper4는 MMC3다. 현재 13bit physical tile tag/128KiB CHR 및 immutable ROM 전제에서 실제 latch/core는 연결되지 않았다. MMC4의 PPU fetch 순서와 latch 전후 bank를 실제 코어에서 기록해야 하며 선행 ROM read가 mapper latch를 다시 건드려서는 안 된다.

MMC5는 mapper5다. 현재 13bit tag로 최대 1MiB CHR의 16bit tile tag를 표시할 수 없다. 376의 조합 자극에서 tag8192는 명시 거절, 224행 split 자극은 현재 128예외를 초과해 거절했다. 모든 MMC5 게임에 같은 문제가 발생한다는 증거는 아니다. ExRAM/CHR-RAM의 mutable 출처·epoch, expanded attribute/split, IRQ·audio·PRG RAM을 분리해 실제 지원해야 한다. 1056 cell에서 15,840→19,008 logical bits, bitmap 1,024→8,192B는 표현의 산술이며 물리 RAM·whole-board 증가량이 아니다.

첫 표본은 (1) MMC3 402 참조와 NROM 후보, (2) MMC4 latch 직전/직후 다른 physical bank, (3) MMC5 고위 tag/ExRAM 변경/빈번한 split 및 IRQ/audio 동시 요청을 고정한다. 실제 mapper와 CPU/PPU 요청을 연결하고 capture/plan/ARM prefetch와 ROM arbiter의 grant·대기·queue를 timestamp로 기록한다. speculative request의 source identity·latch side effect·epoch·STOP을 검사하고, 동일 start/ROM 위상 및 추가 위상, 입력 중과 출력 중, cold/warm을 비교한다. **현재 MMC4/5 추가 시간·SPI·ARM·회로 비용은 모두 미측정(null)**이다. 402의 ROM 71,964쌍 중 입력 중 17,378쌍은 해당 fixture의 실제 연결 기록이지 MMC4/5 최악치가 아니다. 실기 보드의 `native_fill_slot`과 `native_core_safe` 허용조건도 실제 mapper/core에서 충족해야 한다. 자세한 이전 반례는 [376 계약](nes-mapper376-contract.ko.md)이다.

## 현재 결정

227의 SMB3 실기 결과와 복원 자료는 **이미 존재**한다. 새로운 제한 NROM 경로는 아직 구현·FIT·실기 검증되지 않았다. 402는 지속 60fps와 보드 수용 모두 미달한다. 우선 NROM loader/mapper의 작은 실제 통합 경계와 두 60fps 구조 후보의 삭제·유지·추가 비용을 고정한 뒤, 같은 소스의 기능·Lite 전체 비용을 측정한다. MMC4/5 표본은 위 경로와 병행할 수 있으나 완전한 mapper 지원으로 취급하지 않는다. 구매·배포·머지는 자동으로 하지 않는다.
