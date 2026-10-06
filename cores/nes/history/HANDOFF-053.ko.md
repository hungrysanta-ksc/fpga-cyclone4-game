> 공개 이력: 원래 053 상태 설명. 위치 이동에 따른 상대 링크와 라이선스 식별자만 정리했다. 현재 지시는 [NES 현황](../README.md)을 따른다.

2026-10-06 개발053: **ROM 핀 적재 후 실제 코어 실행 — 실기044 유지.**

360505단위 검사/180226바이트 읽기 확인,8오류 시나리오,2종8프레임491520픽셀 일치. 패킷 내용은 같고 공개 tick 차이는 {'banks32': [-4, -4, -4, -4], 'fine_x': [1, 1, 1, 1]}로 기록했다. 공동13612LE/929LAB/26M9K,34LAB여유. MCU SPI/보드 클록/소비자/실제 타이밍은 미완료, 새 SD 이미지 없음. [결과](../../../analysis/ROM-BOOT-RESULT.ko.md), [계약](../../../docs/nes-rom-boot-contract.md).

아래는 이전 단계의 결과와 이력이다.

2026-10-06 개발052: **읽기 전용 PSRAM 핀 제어기와 NES/메모리 CDC 연결 — 실기044 유지.**

2종 실제 코어8프레임의491520픽셀·16064바이트·진행 기록이051과 같다. 최종16위상/203392검사,8400완료/208리셋취소, 왕복4NES클록. 공동13547LE/925LAB/26M9K,38LAB여유.25ns핀 모델 가정이며 실제 부품/CDC 배선/PLL/로더/소비자/STA는 다음 관문이다. 전체 코어 실행 소스와 최종 소스의 속성·상수폭 표기 차이는 검증기에 명시했다. 새 SD 이미지 없음. [결과](../../../analysis/ROM-PHYSICAL-RESULT.ko.md), [계약](../../../docs/nes-rom-physical-contract.md).

아래는 이전 단계 결과와 이력이다.

2026-10-06 개발051: **현재 코어 주소를 이용한 조기 ROM 읽기 —2·3·4클록 응답 통과. 실기044 유지.**

각 지연에서8프레임491520픽셀·16064바이트·진행 기록이050과 같다.624788요청,4168단위 검사.기존050의2클록 실패와051의8클록 실패를 결정 시점 기록으로 보존했다.공동 fit13420LE/935LAB/26M9K,LAB28개 남음.다음은 실제 메모리·빠른 클록/CDC·보드 공동 자원 검증이다.새 SD 이미지 없음. [결과](../../../analysis/ROM-EARLY-RESULT.ko.md), [계약](../../../docs/nes-rom-early-contract.md).

아래는 이전 단계의 결과와 이력이다.

2026-10-06 개발050: **공유 ROM 중재·읽기 마감 감시 검증 완료. 실기044 유지.**

동기식1클록 응답 모델에서624618요청,8프레임491520픽셀·16064바이트·전체 기록이049와 같다.2클록 응답 모델은 두 ROM에서 PPU 마감 초과를 검출했다.4148단위 검사 통과.공동 fit13538LE/928LAB/26M9K,LAB35개 남음. 실제 PSRAM/클록 경계·로더·SNES 소비자·보드 오류 복구는 다음 단계이며 새 SD 이미지 없음. [결과](../../../analysis/ROM-SERVICE-RESULT.ko.md), [계약](../../../docs/nes-rom-service-contract.md).

아래는 이전 단계의 결과와 이력이다.

2026-10-06 개발049: **12KiB 내부 RAM·초기화 통합 검증 완료. 실기044 유지.**

실제 코어와 fit에 같은 RAM을 연결했다. 초기화8192클록(약0.381ms),153604단위 검사,8프레임491520픽셀 일치. 이전048 대비 시간 기록만4클록 이동했다. 최종13477LE/920LAB/26M9K이며 외부 ROM은 아직 이상적/가상이다. 매 RESET PRG RAM 초기화는 진단 정책이므로 저장 게임에 그대로 적용하지 않는다. [결과](../../../analysis/LOCAL-MEMORY-RESULT.ko.md), [계약](../../../docs/nes-local-memory-contract.md). 다음은 외부 ROM 서비스·보드 클록/로더·SNES 소비자와 공동 fit/STA다. 새 SD 이미지 없음.

아래는 이전 단계의 결과와 이력이다.

2026-10-06 개발048: **OAM 쓰기 구조 최적화 —870 LE 절감, LAB 여유10→37. 실기044 유지.**

채택 경로는 `tools/nes_oam_compact.py`다. 원본과216362클록의 상태/메모리 비교를 통과했고, 수정 코어8프레임의16064바이트·491520픽셀 및 진행 기록이047과 같았다. 최종13283LE/926LAB/26M9K. 묶음 분리만 한 첫 시도는 자원이 늘어 미채택했다. [결과](../../../analysis/OAM-BANKED-RESULT.ko.md), [계약](../../../docs/nes-oam-banked-contract.md). 다음은 실제 메모리/클록/소비자 공동 통합이며, 완성 보드 fit/STA는 미확인이다. 원본 OAM 평가 카운터의 초기화/RESET 범위도 별도 확인한다. 새 SD 이미지 없음.

아래는 이전 단계의 결과와 이력이다.

2026-10-06 개발047: **실제 NES 코어→PPU 감시→NCR1→044 전송 통합 검증. 실기 기준044 유지.**

새 코어 실행8프레임에서131104 BG fetch,16064전송 바이트,491520복원 픽셀이 실제 PPU 출력과 일치했다. PPU 감시20항목 통과. 진단 ROM 범위의 통합 fit는14153LE/953LAB/26M9K이며 LAB 여유10개뿐이다. 다음 우선순위는 보드 자원 예산·동등성 회귀를 동반한 여유 확보, 실제 메모리/로더와 SNES 런타임 연결이다. [결과](../../../analysis/NCR1-LIVE-RESULT.ko.md), [계약](../../../docs/nes-ncr1-live-contract.md). 전체 STA/게임/실기 통과로 확대하지 않는다. 새 SD 이미지 없음.

아래는 이전 단계의 결과와 이력이다.

2026-10-06 개발046: **순차 BG fetch→NCR1 생성→045→044 전송 경로 검증 완료. 실기 기준044 유지.**

기록된 NES fetch131104개를 원래 간격으로 입력해16항목/18072바이트를 검증했다. 최종 인코더는672LE/2M9K/전체118LAB이며, 배치 후 기능 넷리스트에서도3프레임6024바이트가 일치했다. [결과](../../../analysis/NCR1-ENCODER-RESULT.ko.md), [계약](../../../docs/nes-ncr1-encoder-contract.md). 실제 PPU/매퍼 tap·모드 감시, 공동 배치, SNES 런타임 소비자는 다음 단계다. 과거 입력 기록의 재생을 새 NES 코어 실행이나 실기 검증으로 부르지 않는다. 새 SD 이미지 없음.

아래는 이전 단계의 결과와 이력이다.

2026-10-06 개발045: **메모리 패킷 생산기 구현·RTL 회귀와 단독 fit 완료. 실기는044 유지.**

완성된 참조 패킷8개를 가변 지연 메모리에서 읽어044 전송부로 전달했다.3클록 조합×17항목, 총57459바이트 일치. 최종416LE/155레지스터/0M9K/전체61LAB이며 epoch 래치 추론을 수정했다. 실제 NES 인코더·물리 메모리 서비스·공동 배치·SNES 런타임 소비자는 다음 연결 대상이다. [결과](../../../analysis/PACKET-MEMORY-RESULT.ko.md), [계약](../../../docs/nes-packet-memory-contract.md). 새 SD 교체는 없다.

아래044 실기 성공 기록과 이전 이력을 유지한다.

2026-10-06 현재: **044 H1 기본 실기 통과 — 정상 화면 순환과 RESET 복구, GBC 정상 플레이 보고**.

사용자가 자동 종료 없이 LINK SCREEN1→2→3→1 반복 및 GBC 정상 플레이를 확인했다. 첨부 로그는 프로토콜0x44, status03(오류 없음), RESET_ASSERTED, start/stop0, base_restored1이다. 약19.54초는 설정을 포함한 세션 기록이며 정확한 화면 표시 시간은 아니다. 새 영상이나 SD 읽기 해시는 제공되지 않았다.

[실기 결과](../../../analysis/H1-HARDWARE-044-RESULT.ko.md)를 최신 근거로 삼는다. 044 이미지와 기존 실패 증거는 그대로 보존한다. H1 재진입·장시간 반복은 미확인으로 남기고 실제 NES 생산자/메모리/소비자 통합 계약을 다음 개발 단계로 진행한다. 진단 통과로 R2/R4 전체나 전기 타이밍을 완료 처리하지 않는다. 현재 증상은 이번044 실행에서 재현되지 않았으며041의 정확한 물리적 원인까지 확정한 것은 아니다.

아래는 이전 단계 당시의 판단을 보존한 이력이다.

2026-10-06 현재: **NES-H1-SAMPLING-044 제한된 실기 진단 시험 준비**.

입력 샘플링·공유 오류 기록을 유지하고 주소 비교의 X 재결합 문제를 이진 동등식으로 수정했다. RTL, MCU 파형, 실제 fit/내부 STA, 설치·복원8조건을 통과했다. 원래 SDF는126바이트에서 실패하며 그대로 보존했다. 별도 첫단 해소 가정의 old/new/mixed 모델은 각각512바이트를 통과했다. 이는 전기적 타이밍 통과나 실기 원인 확정이 아니다.

[검증 결과](../../../analysis/H1-SAMPLING-RESULT.ko.md), [시험 안내](../../../docs/nes-h1-sampling-test.ko.md), [입력 계약](../../../docs/nes-h1-sampling-contract.md).
다음은041 백업 후044 MCU/FPGA 쌍으로1→2→3 순환·RESET·재진입과 로그044를 확인하는 것이다. 실제 최신 관측은 여전히041 자동 복귀 실패다. GBC/H0 기록을 유지한다.

아래는 이전 단계의 당시 판단을 보존한 이력이다. 최신 지시는 위044 안내를 따른다.

2026-10-06 최신: **NES-H1-TIMING-042 조사**, 새실기이미지 없음.

## 최신043 상태 (2026-10-06)

입력 샘플링과 단일 등록 오류 이벤트를 구현했다. 정상936/실제 오류504건, 보드9항목, MCU SPI 및 실제 fit/STA는 통과했다. SDF에서는91바이트 뒤 불확정값이 남아 실기 패키지는 보류한다. 기존041을 반복하지 않는다. [검증 결과](../../../analysis/H1-QUALIFIED-RESULT.ko.md)와 [입력 계약](../../../docs/nes-h1-qualified-contract.md)을 기준으로 첫 불확정값 전달과0/1 상대 샘플 지연을 먼저 검증한다.
[분석 결과](../../../analysis/H1-TIMING-RESULT.ko.md).
실제041 프로토콜확인,동일실패. 집계frontend1과원인0x20(예상frontend2)이상충하므로순서오류로단정하지 않는다.
실제041 배치넷리스트: SDF적용227바이트뒤실패/617타이밍위반,지연없는동일대조512바이트통과.
첫단 비동기샘플/X모델의한계와내부최적화Z별칭을포함하므로실기원인확정으로부르지 않는다.
다음:일관된입력샘플·단일등록오류event와공유기록설계/회귀후새실기후보.현재041반복시험 요청없음.
아래는 과거 단계 기록이다.

2026-10-06 최신: **NES-H1-EDGE-041** frontend 최초 원인 계측 쌍 준비.
[결과](../../../analysis/H1-EDGE-RESULT.ko.md), [설치 안내](../../../docs/nes-h1-edge-test.ko.md).
040 재시험 실패:화면 미완성 후 자동 복귀,frontend1/stage0/producer0,ROMSEL낮음/40:80E0.
040 RTL 결함 수정만으로 실기는 해결되지 않았다.041은040 동작을 유지하며 정확한 원인·상태·읽기 길이를 계측한다.
실제RTL 정상156/오류84·카운터교정·보드9·MCU파형704/328·ARM/full fit/STA/ASM·MCU decode218719·복원8조건 통과.
**041 MCU+FPGA 둘 다 설치,프로토콜0x41/로그041. 실행표식037/화면034 유지.**
다음:한 번 재현하고 nes-h1-last-041.txt 회수.041은 진단용이며 실기 해결 주장이 아니다.
아래는 과거 단계 기록이다.

2026-10-06 최신: **NES-H1-RELEASE-040** 정상 읽기 종료 오검출 수정 FPGA 준비.
[결과](../../../analysis/H1-RELEASE-RESULT.ko.md), [설치 안내](../../../docs/nes-h1-release-test.ko.md).
039 실기 frontend1/stage0/producer0. 정상 RD/ROMSEL 종료로 같은 오류 상태를 실제 RTL에서 재현했다.
수정본 정상156·실제오류72·전체보드9·MCU파형448/200·full fit/STA/ASM·MCU decoder223004바이트·설치9조건 통과.
**040 FPGA 하나 교체,039 MCU 유지. 실행표식037/화면034/로그039 유지.**
다음:040 실기1→2→3 순환/RESET/재진입/GBC 확인. 수정040 실기 미실행,전기타이밍 미검증.
아래는 과거 단계 기록이다.

2026-10-06 최신: **NES-H1-FAULT-039** 최초 오류 스냅샷 진단 쌍 준비.
[결과](../../../analysis/H1-FAULT-RESULT.ko.md), [설치 안내](../../../docs/nes-h1-fault-test.ko.md).
038 실기 로그:F2_STATUS/07,초기진입/STOP 성공,base복구 완료. 실제 하위 오류는 미확정이다.
039는 MCU+FPGA 모두 변경하며 프로토콜39다. 이전036 FPGA와 섞지 않는다. 화면034/실행표식037 유지.
ARM·호스트15·실제RTL파형448/200비트·보드9조건·full fit/STA/ASM·실제MCU decode·설치8조건 통과.
다음:한 번 재현 후 sd2snes/nes-h1-last-039.txt 회수. 진단 보강이며 실제 순환 문제 해결 주장이 아니다.
아래는 과거 단계 기록이다.

2026-10-06 최신: **NES-H1-RUNTIME-038** 자동 복귀 사유 기록용 MCU 준비.
[결과](../../../analysis/H1-RUNTIME-RESULT.ko.md), [실기 안내](../../../docs/nes-h1-runtime-test.ko.md).
사용자037 실기:LINK SCREEN1 뒤 조작 없이 메뉴로 복귀. 순환 실패/원인 미분류이며 성공 처리하지 않는다.
038은 FPGA036 그대로, MCU 종료 원인만 SD 텍스트로 기록한다. 원인 수정/실기 통과 주장이 아니다.
기존 NES H1 037.nh1로 한 번 재현한 뒤 sd2snes/nes-h1-last-038.txt를 확인한다.
ARM 빌드,호스트15조건,실제RTL파형224샘플/88비트,MCU 교체·복원8시험 통과.
아래는 이전 단계 기록이다.

2026-10-06 최신: **NES-H1-BRINGUP-037** 복구 가능한 실기 묶음 준비 완료.
[결과](../../../analysis/H1-BRINGUP-RESULT.ko.md), [실기 안내](../../../docs/nes-h1-bringup-test.ko.md).
035 MCU+036 FPGA 바이트 그대로. 화면 제목은 NES H1 034. 이번 실제 Questa24회와 설치/복원12시험 통과.
다음은 동일한 기존 정상 보드에서 짧은 화면→RESET→재진입→GBC 복귀 실험이다.
패키지는 analysis/local-h1-bringup-037/NES-H1-BRINGUP-037.zip. SD 쓰기/실기 실행은 아직 없다.
38입력/11출력 미제약·전기 타이밍 unknown 유지; 묶음 준비를 full electrical signoff로 부르지 않는다.
이하 과거 단계 기록은 해당 시점의 결과다.

2026-10-06 최신: **NES-H1-SPI-036** SPI 통합 결함 수정·full FPGA image 완료.
[결과](../../../analysis/H1-SPI-RESULT.ko.md), [계약](../../../docs/nes-h1-spi-contract.md).
중요:034 원본 FPGA+035 MCU는 +2us 읽기에서 ID A5가4B로 밀린다. tools/nes_h1_spi.py의 파생 수정본을 사용한다.
036은 MISO를 하강에서 갱신해 high 구간 유지. C 파형224읽기/유효응답88비트,보드6조건 회귀 완료.
실제fit1302LE104LAB44M9K/내부STA/ASM 완료. BI3는 실제 MCU decoder209988바이트 exact.
TEMP/nes-h1-spi-fit-036-01 및 analysis/local-h1-spi-036/resource/에 최종 이미지가 있다.
MCU는035 최종 바이너리 그대로며 조합은 hardware-candidate-files.json에 기록했다.
RLE 끝의 증명된 FF1바이트 중복만 제거. encoder-original.bi3와 최초 실패를 보존한다.
다음:SNES/DMA/보드 외부 IO/CDC/turnaround 요구 검토→복구 설치묶음→RESET/재진입/GBC 전환 실기.
38입력/11출력 미제약,FPGA실물실행 없음.H0 기본 육안통과·032코어40LAB 여유·HDL hold는 유지한다.

2026-10-06 최신: **NES-H1-FIRMWARE-035** 전체 ARM 빌드/호스트11시험 완료.
[결과](../../../analysis/H1-FIRMWARE-RESULT.ko.md), [계약](../../../docs/nes-h1-firmware-contract.md).
실제 바인딩은 src/nes/firmware/nes_h1_stm32.c. 기존034세션과 FPGA는 보존한다.
파생펌웨어만 .nh1 수동진입3개/자동부팅NACK를 추가한다. GPIO SPI<=250kHz,USB OTG IRQ 보호,
RESET→STOP→GPIO/SPI복원→base FPGA검증→원래메뉴재적재 경로다.실패하면 RESET 유지.
최종 빌드는 TEMP/nes-h1-firmware-035-02,기록 analysis/local-h1-firmware-035/arm-final 및 host-04.
첫 ARM은 USB 보호 전이므로 최종용으로 사용하지 않는다.
다음: 034 배치의 IO/CDC 요구·turnaround 검토,같은후보 ASM/RBF/BI3와 복구가능 실기묶음.
38입력/11출력 미제약을 임의 false-path로 지우지 않는다.035는 실물 MCU/GBC 회귀 통과가 아니다.
H0 기본 육안통과/032 NES코어40LAB여유/HDL hold/정확성 미해결은 유지한다.

2026-10-06 최신 **NES-H1-BOARD-034**: [결과](../../../analysis/H1-BOARD-RESULT.ko.md).
실제135핀/virtual0/PLL1,8MHz→84MHz H1 top+compact SNES ROM24KiB+SPI ARM/STOP 구현.
Questa6조건 ROM65536B/payload8192B exact.읽기중STOP,세대1→2→3,클록정지PLL loss/rearm 통과.
Mesen034 epoch1/2 각각7화면 총856576화소 exact.명시적 장치모델이며 실제RTL 동시연결 아님.
실제fit1298LE/110LAB/44M9K;내부STA setup+2.724 hold+0.161 recovery+6.976 removal+0.518ns.
입력38/804경로·출력11/933경로 미제약,MTBF/IO미검토이므로실기signoff금지.
MCU session C모듈 host7조건 /W4 /WX 통과,STM32 callback/menu미연결.풀firmware/asm/배포없음.
다음:실제SNES/SPI timing/합성CDC endpoint→250kHz MCU binding/메뉴복원→전체후보검증→실기묶음.
SPI E8 A5 5A ARM /E9 A5 5A STOP,F0A5/F134/F2status/F3F4epoch.원본ROM은600B/C세대조회.
기존033생산기/031transport/GBC/core014/upstream보존. H1은NES없는진단이며032잔여40LAB와별도.
실패원문:compile hex ternary/예약어;fit NCEO설정누락F16충돌→원본QSF설정복구후성공.
원시analysis/local-h1-board-034;전033manifest138항목검증/상태8파일baseline보존.
아래는 과거 기록이다.

2026-10-06 최신 **NES-H1-PATTERN-033**: [결과](../../../analysis/H1-PATTERN-RESULT.ko.md).
자체6144B ROM producer+031 transport와 실제65816 MMIO/PPU DMA client 구현.
Questa3×5조건43,008B exact. Mesen 정상6DMA12,288B 및 미응답/길이오류에서 DMA0,
11화면673,024화소 exact. LINK WAIT,1/2/3순환,LINK ERROR가 읽을 수 있음.
Mesen은 실제RTL바이트를 공급하는Lua장치모델이며 실시간 RTL 공동실행/물리 응답 검증 아님.
H1전용fit1144LE/104LAB/20M9K;producerROM8+queue8+stage4M9K 보존.
032 core 공동fit923LAB/잔여40LAB는 별도 유지. 합산/전체NES완료 주장 금지.
다음: 실제 보드PLL/reset/pins/Quartus CDC제약/ROM공급/MCU로더·세대·복귀→동일후보fit/STA→실기.
epoch1 cold reset 가정이며 warm 세대 전달 미구현.65535 boundary 구현·실행 미검증.
무료FLOAT재사용,원시 local-h1-pattern-033,기존031 RTL/GBC/upstream 보존.
실패:초기누락글꼴수정;Mesen DMA8/48리프레시간격 감사기수정,원시/ROM변경없이 재감사.
이전032의71항목 hash 검증과 상태8파일 baseline 보존. 아래는 과거 기록이다.

2026-10-06 최신 **NES-R1-JOINT-RESOURCE-032**: [결과](../../../analysis/JOINT-RESOURCE-RESULT.ko.md).
코어018(RDY014)+기본12KiBRAM+전송부031을동일소스로공동배치하여13,417LE/923LAB/24M9K 성공.
별도LAB합992>963의우려를공동배치로해소.남은LAB40,LE1991,M9K32;내부LE13000목표는417초과.
CPU/PPU/APU/MMC3및CPU/CIRAM/PRG/queue/stage메모리보존검증. 기능/STA/물리IO완료아님.
생산기입력은external virtualpin이므로NES영상→packet통합이라고표현하지않는다.
다음:H1자체패턴producer/실제SNESPPUDMA→보드PLL/reset/pins/IO/CDC/loader·복귀→동일후보fit/STA→실기.
현재fit성공만으로OAM기능수정은하지않는다.추가비용을측정하고필요하면동등성회귀를갖춘절감을추진.
원시analysis/local-joint-resource-032/run,실행TEMP nes-joint-resource-032-01.최초map/fit통과,추가seed/완화없음.
이전031manifest157항목검증·상태8개baseline-status보존.GBC/core014/031RTL/upstream불변.
이번Questa/Mesen/STA/실기추가실행없음.H0기본영상확인통과는유지.

2026-10-06 최신 **NES-H1-SNES-FRONTEND-031**: [결과](../../../analysis/SNES-FRONTEND-RESULT.ko.md).
사용자030정상보고+5.27초영상의11표본에서읽을수있는제목·1/2/3반복확인,H0기본육안통과. RESET/장시간/NESFPGA미검증.
031 pin frontend→029stage→RAMvariantCDC/queue 연결.Questa3×13조건19,218B exact.
기존027RAM의Quartus추론실패를031별도동기RAM으로수정,원래14조건38,510cycle외부출력동등성통과.027/028원본은불변.
최종전송부목표FPGA실제fit1,139LE/111LAB/12M9K.133virtualpin,2미할당clockpin,STA/실기후보아님.
018과LAB단순합992>963:다음에전체코어+전송부jointfit으로판정해야한다.별도fit합으로불가능확정은금지.
H1자체producer/PPU DMA와보드PLL/핀/IO/CDC/로더·복귀도진행.H1패키지는아직없음.
원시analysis/local-snes-frontend-031:compile-failure-01,initial-pass-02,test-failure-03,resource-failure-01,run,resource,hardware-video및프레임.
최종QuestaTEMP031-04,resourceTEMP031-02.14case동등성+3×13case통합과map/fitPASS;과거실패보존.
무료FLOAT재사용.GBC/upstream/core014/030ROM보존.현재상태8개는baseline-status보존,이전030manifest61항목검증.

2026-10-06 최신 **NES-H0-VISUAL-030**: [결과](../../../analysis/VISUAL-H0-RESULT.ko.md).
사용자가029 H0의3ROM 모두 정적인 글리치형 무늬이고 구별/판정이 무의미하다고 보고함.
실기 실행됨/정상 판정 불가이며 통과나 고장으로 확정하지 않는다.029 재시험 대신030한ROM을 제공.
큰 NES H0 030 제목,GRID/BARS/CROSS가60프레임마다 순환.실제 Mesen7화면428,288화소 exact/4DMA 확인.
초기auditor의224/239캡처 크기 오류와원본을보존하고7+224+8전체비교로수정,같은 실행 재검증.
[새 실기 절차](../../../docs/nes-visual-h0-test.ko.md), ignored analysis/local-visual-h0-030/NES-H0-VISUAL-030.zip.
030실기 결과 대기. 마지막NES trace replay025/RTL029/CPU017/자원018/core014유지.
AGENTS에 수동 진단 가독성·진행 표시 규칙 추가. H1 물리bus/PPUDMA·동일후보fit/STA/복귀 작업 계속.

2026-10-05 최신 **NES-R2-HOST-STAGE-029**: [결과](../../../analysis/HOST-STAGE-RESULT.ko.md).
실제 Questa3클록×10조건,28,431바이트 exact.027/028 보존, 원본 host stage3KiB 추가.
정규화 host strobe까지만 검증, 물리 SNES bus/fit/STA 미완료.
사용자 요청으로 실기 진입을 앞당긴다. H0 자체 SNES ROM3개 패키지가 analysis/local-host-stage-029/NES-H0-029.zip 에 준비됨.
[H0 절차](../../../docs/nes-hardware-first-test.ko.md)대로 기존 일반 SNES 경로에서 시험 가능. NES FPGA 교체 없음, 실제 실기 결과 미수신.
다음은 H1 자체 패턴→029→물리 SNES→PPU DMA와 같은 후보 fit/STA/IO/복귀 묶음.
H1은 전체SMB3/DMC 완료를 기다리지 않는다. 기존 제품 관문은 유지.
028manifest55항목 검증/상태6개는029/baseline-status 보존.새 Mesen/Quartus 실행 없음.
무료 FLOAT 재사용, 원시 로그 private/ignored 분리. GBC/core014/027/028/upstream 변경 없음.

# 현재 이어받기 지시 — PACKET-CDC-028

[README](../README.md) → [계획](../PROPOSAL.ko.md) → [관문 JSON](../../../docs/nes-development-plan.json).
후보028/core014,실제SNES025,CPU기능017,자원018유지.
src/nes/nes_packet_cdc.sv는027큐를 변경 없이 감싼1outstanding consumer request/response bridge다.
queue_clk는producer/027RAM,host_clk는cmd_valid/ready 및rsp_valid/ready.
요청/응답bundle은handshake기간고정,control toggle2단sync. queue등록명령1cycle/결과capture후ack.
host_read_owned는논리상태이며SNES DMA허가아님. rsp_data_valid는rsp_valid와함께해석.

공통async reset/local2edge release+peerup동기화. queue는release전sync reset.
클록정지중reset/재개검증. 독립endpointreset미지원. externalreset_epoch fresh/stable필수.
물리heldbus도착/skew/MTBF/reset제약미검증,async_reg만으로안전판정금지.

Questa3조합10/14nsphase3,14/10nsphase1,10/22nsphase9각13casepass.
각6405readbytes/6426Hresponses/4commit,합19215B일치.
각6428requests중reset취소2개,그중이미queue에서읽은1B보류응답취소.
응답acceptedlatency min/median/max84/98/182,90/100/160,110/132/264ns.
testbackpressure/요청간격포함,실제SNES성능아님.
첫compile은TB receive9인수/8형식오류.초기TB/log보존,마지막인수삭제후RTL미변경으로3runpass.

**다음: SNES host MMIO명령/상태+read staging/prefetch,ready대기와고정시간DMA read연결**.
현재직접SNES bus,CPU polling,PPUcommit,외부메모리,NES assembler는미연결.
026clock전략,025CHR/023OBJ충돌,024patch결합,018자원확대도유지.

tools/nes_packet_cdc.py,run_nes_packet_cdc.ps1,verify_nes_packet_cdc.py.
tests/nes-functional/packet_cdc_tb.sv. 기존FLOAT RunOnly/서버private유지.
증거analysis/local-packet-cdc-028/{run,compile-failure-01};결과PACKET-CDC-RESULT.ko.md.
이전027의54hash/status6보존. GBC/upstream/기존도구/core014/027큐 보존.
DMC/SMB3/전체fit·STA/실기/HDLhold 미완료.

아래는 과거 기록이다. 당시 최신/다음 지시는 위 현재 계획보다 우선하지 않는다.

---

# 현재 이어받기 지시 — PACKET-QUEUE-027

[README](../README.md) → [계획](../PROPOSAL.ko.md) → [관문 JSON](../../../docs/nes-development-plan.json).
후보027/core014. 실제SNES025,CPU기능017,자원018 유지.
원본MIT src/nes/nes_packet_queue.sv:singleclk3KiB×2slot FREE→WRITING→READY→READING→FREE.
순차write완료 전publish차단,READY전acquire대기,순차read완료+commit전free차단.
epoch/sequence/length 검증. 외부reset_epoch는새값이어야하며동일epoch재사용/롤오버정책미구현.
동기reset은RAM지우지않고metadata/상태무효화. seq0예약/65535뒤세대전환필요.
invalid command는payload/ownership보존. opaque packet이며header/CRC파싱없음.

실제Questa14case pass:10492write/10460read전부일치/68commit/2008동시edge.
reset시험의미소비32B취소는정상frame삭제정책아님.10ns단일시험clk,CPU/PPU/CDC/PPUDMA실행아님.
Python검증기초기fixture2앞3B기대오류수정;RTL/TB/raw실행변경없고초기실패보존.

clock audit:pin.sdc8MHz,gbc_pll151/36,busPLL21/2,PHI2는2단sync비동기입력.
NES core12/4CE,기존testbench46.560846ns.실제NES보드클록동기화미구현/026drift미해결.
GBC클록/소스/제약변경없음.

**다음: CDC와SNES ready-gated frontend,reset세대/순번/길이/commit전달 및소비지연 실측**.
아직메모리모듈과단일clock서비스만있다. 실제SNES bus/MMIO와PPUcommit에붙이지않았다.
이후025CHR/023OBJ VRAM충돌,024patch결합,018자원확대.
source scratch/metadata/CDC비용미포함;3KiB2slot을제품최종FIFO로확정하지않는다.

tools/nes_packet_queue.py,run_nes_packet_queue.ps1,verify_nes_packet_queue.py.
tests/nes-functional/packet_queue_tb.sv. 기존FLOAT RunOnly를사용하며서버로그private유지.
증거analysis/local-packet-queue-027/run,결과PACKET-QUEUE-RESULT.ko.md,계약nes-packet-queue-contract.md.
이전026의140hash/status6보존. GBC/upstream/core014/원본probe유지.
DMC/SMB3/전체fit·STA/실기/HDLhold 미완료.

아래는 과거 기록이다. 당시 최신/다음 지시는 위 현재 계획보다 우선하지 않는다.

---

# 현재 이어받기 지시 — PACKET-PACING-026

[README](../README.md) → [계획](../PROPOSAL.ko.md) → [관문 JSON](../../../docs/nes-development-plan.json).
분석026/구현014. 실제 SNES025, CPU기능017, 자원018 유지. 이번 새 에뮬레이터/RTL/Questa/Quartus 없음.
022..025 raw phase/packet/frames를 고정 manifest와 대조한 파라미터 시간 모델이다.
NES anchor=line0dot5 tick-20, 마지막BG read offset326984; 관측 period357364/357368.
실제 NES/SNES 절대위상이나 보드ppm은 미측정이다. 두 실행의 절대tick을 동기화하지 않는다.
가정 encode1024/CDC8/link2또는4ticks/B,poll112,짧은frame끝4guard.
slot claim은 마지막fetch, free는SNEScommit. producer frame 조립scratch는 미포함.
split aligned 생산·전달 예산7588:2ticks/B pass,4ticks/B late2756.
지연1/2slots263위상 표본 통과,nominal60000frames pass. 장기 실제 화면실행 아님.
±100ppm 모델: +100은frame9350 slot부족,-100은frame10053 deadline.
무손실/정상속도 위해 실제clock/enable 동기화 조건을 확인해야 한다. 버퍼만으로 해결 주장 금지.
독립tick oracle300+경계13pass. 초기phase357363/lag1 실패 기대가 잘못되어 통과로 수정,
phase1900/1901 경계 추가. 방정식은 완화하지 않았고 초기test/rawfailure/설명을 보존했다.

**다음: 실제 보드 clock/enable 경로 확인 및 packet 소유권·ready-gated consumer 구현**.
FREE→WRITING→READY→READING→FREE, 길이/세대/sequence,commit뒤반환,reset시 stale무효화.
아직 모델이며 실제CDC나메모리서비스 보장 아님. 이후joint renderer VRAM/018자원 확대.
025CHR word2000..5fff와023OBJ word4000 겹침,024patch 별도 문제도 남는다.

tools/nes_packet_pacing.py, test_nes_packet_pacing.py.
analysis/PACKET-PACING-RESULT.ko.md, docs/nes-packet-pacing-contract.md.
최종 model-audited.json/tests-final.json in analysis/local-packet-pacing-026.
이전025의224hash/status6보존. 새 source/status/입력/증거 manifest는packet-pacing-artifacts.json.
GBC/upstream/기존도구/core014보존. DMC/SMB3/전체fit·STA/실기/HDLhold 미완료.

아래는 과거 기록이다. 당시 최신/다음 지시는 위 현재 계획보다 우선하지 않는다.

---

# 현재 이어받기 지시 — CHR-RESIDENCY-025

[README](../README.md) → [계획](../PROPOSAL.ko.md) → [관문 JSON](../../../docs/nes-development-plan.json).
후보025/구현014. CPU기능017, 자원018 유지.
021 banks32의 immutable32KiB 전체를 startup VRAM word2000..5fff에 적재했다.
현재 frame의 tile//1024가 하나인지 검사, map은tile%1024, packetbyte7 window0/1, BG1CHRbase=2+2*window.
실제window1,0,0,1. 미래frame 사용집합을 preload 선택에 쓰지 않는다.
NCR1 packet2008B/stride2048B, PPU DMA1988B, max19732clocks/minmargin10166.
banks32 top/bottom 및 fine-X1 각4frame 화소차이0, bank반전/window2 오류 검출, software23negative.
두viewport union240줄245760화소; 동시 출력239줄. 새 SNES5실행, RTL/Questa/Quartus 없음.

VRAM map8KiB+CHR32KiB=40KiB, 미배정24KiB. 023OBJ word4000과 충돌한다.
sprite와024patch는 별도 경로. 한frame 두window/큰ROM/CHR RAM/일반화 지원으로 해석하지 않는다.
매frame cold4096B+map1988B DMA의 payload하한48672clocks>rawblank30008; 산술분석이며 실패실행 아님.
기존 실제packet 최대2328B: 데이터2slot 최소4656B,1KiB단위6144B,2의거듭제곱8192B.
M9K6/8은1024x8 가정 산술값이며 metadata/CDC/scratch/backlog미포함, queue 깊이 채택 아님.

**다음: producer release→packet 완료/전달 지연→queue/pacing 연결**.
이어 memory/CDC 인터페이스·joint renderer VRAM 소유권과018 자원 확대 측정.
완성 packet ROM 공급과 source frame 전체 관측 조건은 유지; live deadline/실기 미검증.

도구 tools/{build,run,verify}_nes_chr_residency.py, 관측 snes/video_probe/capture_chr_residency.lua.
결과 analysis/CHR-RESIDENCY-RESULT.ko.md, 계약 docs/nes-chr-residency-contract.md.
증거 analysis/local-chr-residency-025/{top,bottom,fine_x,bank,window}/{build,capture}.
024의199hash와 상태6파일을 먼저 검증/보존했다. GBC/upstream/core/기존 도구 보존.
DMC/SMB3/전체fit·STA/실기/HDLhold 미완료.

아래는 과거 기록이다. 당시 최신/다음 지시는 위 현재 계획보다 우선하지 않는다.

---

# 현재 이어받기 지시 — BANK-PATCH-024

[README](../README.md) → [계획](../PROPOSAL.ko.md) → [관문 JSON](../../../docs/nes-development-plan.json).
후보024/구현014. CPU기능017, 자원018 유지.
021 split frame6..9에서 cell(7,13..32)20개의 plane별 읽기값을 합성한2bpp 타일로 재생했다.
현재 frame에서 원래 전체 타일과 일치하는 cell은 유지, 나머지는 예약slot256..287에 배정한다.
일반 참조가 예약 영역에 있거나32patch 초과면 거부한다. 다음 frame을 참조하지 않는다.
NBP1 header20+main1920+edge60+palette8+patch320=2328B, ROMstride4096B.
4DMA2308B/frame, max22788clocks/minmargin7130; startupCHR16KiB.
split top/bottom 및 별도fine-X1 각4frame 일치; patch 소거/count33 오류 검출, software23negative.
두viewport union240줄245760화소 일치; 동시 출력239줄. 023sprite 동시 결합은 없다.

**다음:021 banks32의 큰 CHR residency와 packet 저장 경계 검증**.
이후 live producer release/메모리/queue/CDC/pacing과018 자원 확대 측정.
예약32slots는 이 표본의 제약이다. 임의 게임/32patch 최대부하나 live producer 기한을 주장하지 않는다.
source frame 전체를 모아 packet을 만든 뒤 ROM에 넣었고 host guard도 생성4frames에 특화되어 있다.

도구 tools/nes_bank_patch_packet.py, build_nes_bank_patch.py, run_nes_bank_patch.py, verify_nes_bank_patch.py.
기존 capture_fine_scroll.lua를 변경 없이 재사용.
결과 analysis/BANK-PATCH-RESULT.ko.md, 계약 docs/nes-bank-patch-contract.md.
증거 analysis/local-bank-patch-024/{top,bottom,fine_x,patch,count}/{build,capture}.
023의224hash와 상태6파일을 먼저 검증/보존했다. 새 SNES5실행, RTL/Questa/Quartus 재실행 없음.
GBC/upstream/기존 도구/core014 보존. DMC/SMB3/전체fit·STA/실기/HDLhold 미완료.

아래는 과거 기록이다. 당시 최신/다음 지시는 위 현재 계획보다 우선하지 않는다.

---

# 현재 이어받기 지시 — SPRITE-REPLAY-023

[README](../README.md) → [계획](../PROPOSAL.ko.md) → [관문 JSON](../../../docs/nes-development-plan.json).
후보023/구현014. CPU기능017,자원018유지.
021sprite의CPUOAM=[79,1,0,40]·physicaltile257의16reads를확인해nativeSNES OBJ로변환했다.
위표현의뜻: sourceOAMy79/tile1/attr0/x40 → SNES x40/y80/tile0/priority3,palette0.
하위2planes interleave+상위0으로4bpp32B,OBJword4000/CGRAM128/OAM0.
NSP1=022BG2008B+OBJ32B+palette8B+OAM4B=2052B,ROMstride4096B.
6DMA 2032B/frame,max21470clocks/minmargin8444;startup BG16384+hiddenOAM544=16928B.
sprite top/bottom/fine-X1-no-sprite각4frames정상;hide/obj/count3fault예상대로검출.
software13negative;두viewportunion240줄245760화소일치,동시출력239줄.
front8x8onefixedOAM/no flip/palette0/unclipped범위. scrolling+visible sprite동시참조는없다.

**다음:021 split의cell내CHR bank변경patch표현과actualSNES예산검증**.
그뒤큰CHRresidency/2052Bpacket경계,liveproducer/queue/CDC/pacing와018자원.
sprite정확도검사만확대하며통합관문을뒤로미루지않는다.
full16KiBBGstartup/완성packetROM조건;release tick은metadata이며live기한미검증.

tools/nes_sprite_packet.py,build_nes_sprite_replay.py,run_nes_sprite_replay.py,verify_nes_sprite_replay.py.
관측snes/video_probe/capture_sprite_replay.lua.
결과analysis/SPRITE-REPLAY-RESULT.ko.md,계약docs/nes-sprite-replay-contract.md.
증거analysis/local-sprite-replay-023/{top,bottom,fine_x,hide,obj,count}/{build,capture}.
초기negative palette0->0 mutation과배경동색노출로화면변화없던단일bitfixture를수정,
초기verifier2개와설명보존.실제capture/decoder미변경.
이전022의218hash/status6보존. 새SNES Mesen6실행,RTL/Questa/Quartus재실행없음.
기존022도구/core/GBC/upstream/원본보존;DMC/SMB3/전체fit·STA/실기/HDLhold미완료.

아래는 과거 기록이다. 당시 최신/다음 지시는 위 현재 계획보다 우선하지 않는다.

---

# 현재 이어받기 지시 — FINE-SCROLL-022

[README](../README.md) → [계획](../PROPOSAL.ko.md) → [관문 JSON](../../../docs/nes-development-plan.json).
후보022/구현014. CPU기능기준017,자원018유지.
021 actual NES fine-X1의33번째열을dot245/247fetch에서추가해240줄golden일치.
NFX1 header20B+main1920B+edge60B+palette8B=2008B/ROMstride2048B.
SNES64x32map두세트총8KiB VRAM,wordbases0000/0800;CHRword2000..3fff16KiB.
main VMAIN80,edgeVMAIN81/32wordincrement DMA로다음page첫column만전송.
packetfine-X→HOFS, BG1SC=slot*8+1 commit.
정상PPU DMA1988B/frame,max19618clocks/minmargin10282.
fine-X1top/bottom+fine-X0baseline각4frames연속일치,edge/scroll/length3fault도예상대로검출.
software16negative통과.239줄두독립관측의union240줄245760sourcepixels;동시240아님.
실제fine-X0/1만확인.큰CHR·sprite·세로/coarse/중간scroll·in-cellbank미지원.
원본4색은RGB555변환/기호보존이며최종색정책아님.

**다음구현:021 실제sprite표본을BG와함께보존하는packet/표현과SNES재생**.
이후cell내bank patch·큰CHRresidency비용을정하고live producer/queue/CDC/pacing 및018에대입.
whole16KiB startup과완성packetROM공급조건유지;release tick은metadata,실시간연결없음.

tools/build_nes_fine_scroll.py,run_nes_fine_scroll.py,verify_nes_fine_scroll.py.
관측snes/video_probe/capture_fine_scroll.lua.
결과analysis/FINE-SCROLL-RESULT.ko.md,계약docs/nes-fine-scroll-contract.md.
증거analysis/local-fine-scroll-022/{top,bottom,baseline,edge,scroll,length}/{build,capture}.
이번실행6건은새SNES Mesen이며NES RTL/Questa/Quartus재실행없음.
021의110hash/status6files보존;020/021소스·NES코어·GBC·upstream·원본미변경.
DMC/SMB3/전체fit·STA/실기/HDLhold및동시240미완료.

아래는 과거 기록이다. 당시 최신/다음 지시는 위 현재 계획보다 우선하지 않는다.

---

# 현재 이어받기 지시 — VIDEO-WORKLOADS-021

[README](../README.md) → [계획](../PROPOSAL.ko.md) → [관문 JSON](../../../docs/nes-development-plan.json).
후보021/구현014. 최근NES CPU기능기준017,자원018,실제SNES소비자020유지.
자체Mapper4 baseline/fine_x/sprite/split/banks32 각4frames를NES Mesen에서새로관측했다.
20frames/1,228,800source pixels 캡처. 이숫자는전체renderer일치화소수가아니다.
기준4frames승인/나머지16frames미지원거부. 상태+cadence+byte+reference 승인검사12negative통과.
가로1pixel:raw packet43,993~45,250불일치/frame;8x8sprite:32~33불일치/frame.
IRQ split은line63 R0dot30..35/R1dot87..92 변경,한8x8cell내tile변경으로거부.
32KiB전체atlas는020한계밖. 네묶음union16KiB지만각묶음한번관측해warm이후hit주장금지.
BG캐시만분석;sprite/dummy traffic비용은포함하지않음.

**다음구현: fine-X 가로scroll packet/map표현과021참조대비실제SNES재생**.
단순히지원한계검사만반복하지않는다. 이후sprite/분할bank patch·큰CHR residency비용,
producer완료/packet/queue/CDC/pacing기한및018자원으로진행.
새승인검사는오프라인full-reference도구다. runtimeRTL/SNES에넣었다고말하지않는다.
기존020상위build는고정ROM/golden검증을했다;이번raw primitive한계를020오류통과로해석하지않는다.

tools/build_nes_video_workloads.py,run_nes_video_workloads.py,
nes_video_packet_admission.py,verify_nes_video_workloads.py.
관측tests/nes-functional/capture_video_workloads.lua.
결과analysis/VIDEO-WORKLOADS-RESULT.ko.md,계약docs/nes-video-workloads-contract.md.
증거analysis/local-video-workloads-021/verification-final.json가최종;
unused-fetch를primitive가무시하던초기gate/reviewer/results도보존했고최종cadenceguard로거부.
이전020의183hash/status6보존. 이번새NES Mesen5실행만,RTL/Questa/Quartus/SNES실행없음.
core014/GBC/upstream/기존ROM보존. 표시240·최종색·DMC·SMB3·board/실기·HDLhold미완료.

아래는 과거 기록이다. 당시 최신/다음 지시는 위 현재 계획보다 우선하지 않는다.

---

# 현재 이어받기 지시 — TRACE-REPLAY-020

[README](../README.md) → [계획](../PROPOSAL.ko.md) → [관문 JSON](../../../docs/nes-development-plan.json).
후보020/구현014. NES CPU기능기준017,자원018,fetch분석019 유지.
실제009/014 BG fetch에서960cell타일맵을추출,packet1,944B·PPU DMA1,928B.
불변CHR ROM전체16KiB를NES→SNES planar변환후시작때사전적재.
실제SNES 두viewport4프레임씩연속재생화소일치;consumer최대18,046clocks/minmargin11,852.
두독립관측union은240줄245,760화소. 동시출력은239줄이며표시정책미승인.
RGB555변환을명시,4기호보존. packetrelease tick은metadata일뿐live producer위상연결없음.
CHR byte변조와packet2 길이변조의의도된실패를관측.소프트웨어음성검사9종통과.

**다음: 더넓은자체Mapper4 bank/scroll/sprite/중간변경부하와packet표현거부조건 검증**.
이어producer완료시각/packet전달/queue/CDC/pacing기한을연결하고018자원에대입한다.
whole16KiB startup과완성packetROM공급을큰게임일반해법또는실시간통합으로부르지않는다.
240동시출력·DMC refill timing·실제메모리·SMB3·fullboard/실기·HDL반입hold는열린과제.

도구tools/build_nes_trace_replay.py,run_nes_trace_replay.py,verify_nes_trace_replay.py.
관측snes/video_probe/capture_trace_replay.lua. 결과analysis/TRACE-REPLAY-RESULT.ko.md.
원시증거analysis/local-trace-replay-020;top/build-02가최종top생성물.
실패top01은header22B→21B영역삽입으로ROM1B증가,최종은65536B/packet주소검사추가.
startup overscan안정화대기추가;초기width음성검사no-op수정기록보존.
019의61hash확인/status6files보존.이번SNES Mesen4실행;Questa/Quartus/NES RTL재실행없음.
core/원본/GBC/upstream미변경.

아래는 과거 기록이다. 당시 최신/다음 지시는 위 현재 계획보다 우선하지 않는다.

---

# 현재 이어받기 지시 — FETCH-WORKLOAD-019

[README](../README.md) → [계획](../PROPOSAL.ko.md) → [관문 JSON](../../../docs/nes-development-plan.json).
기술후보019/구현014, 최신기능검증017, 자원실측018 유지.
보존된014 Mapper4 BG4프레임의causal LRU:4KiB캐시매프레임4096B,8KiB캐시4096/4096/0/0B.
순간512B/1364NESmasterticks. 새4KiB일괄DMA는기존239줄rawblank도초과한다.
BG만 있는 두bank표본이며 CHR 전체ROM16KiB 중관측union8KiB를미래preload선택에쓰면안된다.
전체240줄245,760화소의즉시공급소프트웨어복원일치. 실제SNES기한/FIFO크기검증은아니다.

**다음: 실제trace→compact packet→SNES replay의deadline/240줄accounting 연결**.
더많은bank/scroll/sprite/중간bank변경 자체표본으로같은분석확대, 실제서비스예산으로FIFO/cache를정해018자원에대입.
source16B NES tile을SNES형식/역할/VRAM배치 검증 없이그대로전송가능하다고간주하지않는다.
DMC refill timing은R3열린이슈. R1의새resourcewrapper기능도통합전에검증한다.

tools/analyze_nes_fetch_workload.py, tools/test_nes_fetch_workload.py.
analysis/FETCH-WORKLOAD-RESULT.ko.md, docs/nes-fetch-workload-contract.md.
증거analysis/local-fetch-workload-019/run-02;run-01은pixel-only를lower_bound라부른표기를수정하기전기록.
018의95hash를확인하고status6files보존.019에는Python분석만실행;Questa/Quartus/SNES새실행없음.
원래ROM·core·GBC·upstream미변경. R2부분진척이며제품완료아님.

아래는 과거 기록이다. 당시 최신/다음 지시는 위 현재 계획보다 우선하지 않는다.

---

# 현재 이어받기 지시 — RESOURCE-018

[README](../README.md) → [계획](../PROPOSAL.ko.md) → [관문 JSON](../../../docs/nes-development-plan.json)을 읽는다.
기술 후보018/구현014, 기능 기준017 유지. R1 기본 구성 두 종류의 Quartus map/fit/STA 완료.
RAM 포함12,281LE/881LAB/12M9K; 내부 setup+10.943ns/hold+0.152ns. 외부IO 미제약.
전체 board/메모리 controller/영상 encoder/FIFO/CDC는 미포함. LAB91%와 OAMEval7,916cells이 주요 자원 위험이다.

**다음은 R2 실제 fetch 부하 분석**: 기존009 기록으로 causal tile working set/miss burst/packet 요구량 도구를 검증하고
더 넓은 자체 Mapper4/지정 SMB3 표본으로 확대한다. 요구량으로 R1 unknown 비용을 채운다.
DMC refill +123/+275cycle 차이는 R3 열린 이슈다. 새로운 자원 wrapper의 기능도 통합 전에 검증해야 한다.

검증 경로는 tools/nes_resource_probe.py와 verify_nes_resources.py, 원시 증거는 ignored analysis/local-resource-018.
기존014 검증 RTL의 코어 바이트는 보존하고 자원 사본에서만 진단 ROM 크기 제한을 풀었다.
이번 작업은 Quartus만 실행; GBC152hash 검증 PASS/upstream clean/잔류compiler·simulator·FLOAT process0.
프로젝트 전체 자원 또는 기능 완료로 확대 해석하지 않는다.

아래는 과거 기록이다. 당시 “최신/다음 작업”은 위 현재 계획보다 우선하지 않는다.
라이선스 중지 이력도 역사 기록이며 기존 사용자 승인된 FLOAT 작업 재개 상태는 유지한다.

---

2026-10-05 최신: **NES-P2-DMC-OAM-017 중재/데이터/CPU 복귀8조건 통과, DMC refill timing 불일치 미해결**. [결과](../../../analysis/DMC-OAM-RESULT.ko.md), [계약](../../../docs/nes-dmc-oam-contract.md).
CPU가 실제 APU를 설정, DMC/OAM 어느 입력도 force하지 않음. OAM2,048bytes/read-write4,096/OAM snapshot2,048bytes가 actual Mesen/ROM과 일치. overlap RTL9/Mesen10건, 각 timeline의 DMC 우선 read+idle 후 OAM 재개와 CPU INC1회 확인; 변조10종 거부.
**다음 우선 작업: DMC enable 후 첫 refill 위상 차이의 reset/timer/bit-counter/buffer 상태 원인 분리.** 첫 sample fetch는양쪽+5cycles, 다음은RTL+123/Mesen+275. runtime_timing_match=false이며 전체DMC 통과로 취급하지 않는다.
코어 변경 없음(구현014, compiled17sources 동일). run_nes_rdy.ps1 + dmc_oam_tb.sv. 두 RTL실행bus/OAM동일; buffer관측추가와 verifier off-by-one 수정 전 기록도 보존. evidence ignored analysis/local-dmc-oam-017/. 직전117hashes/GBC152hashes/upstream 보존, FLOAT process/listener0.
렌더링off/ideal memory. DMC IRQ·loop·wrap·boundary, audio, NES→SNES·SMB3·fit/STA·실기·license hold 미완료. 이전 IRQ/Mapper4 회귀는 과거 보존 결과.

2026-10-05 최신: **NES-P2-OAM-INTERRUPT-016 실제 DMA 중 IRQ/NMI24조건 통과**. [결과](../../../analysis/OAM-INTERRUPT-RESULT.ko.md), [계약](../../../docs/nes-oam-interrupt-contract.md).
실제 $4014 DMA의 cycle1/256/512에 없음/held IRQ/1-cycle NMI/동시 입력. 각 조합의513/514pause, DMA6,144bytes·12,288bus accesses·OAM6,144bytes, IRQ12/NMI12 및 동시6조건 NMI→IRQ, stack/RTI/INC1회 복귀 확인. 변조12종 거부.
코어 변경 없음: compiled17sources는015와 동일(구현014). runner는 run_nes_rdy.ps1 + oam_interrupt_tb.sv. 첫 ROM의 위상 coverage 실패와 초기 verifier의 다음 case 초기화 포함 오류를 보존 후 수정했다.
**다음 우선 작업: 실제 DMC/OAM DMA 경쟁과 bus arbitration/CPU 복귀.** 이번 입력은 synthetic IRQ/NMI이며 Mesen runtime 주입 또는 exact interrupt latency 검증은 아니다. rendering/DMC off, ideal memory. 이전 Mesen/Mapper4 회귀는 보존된 과거 결과.
증거 ignored analysis/local-oam-interrupt-016/. 직전132hashes/GBC152hashes/upstream 보존, FLOAT process/listener0. NES→SNES·SMB3·fit/STA·실기·license hold 미완료.

2026-10-05 최신: **NES-P2-OAM-DMA-015 실제 DMA16개 통과**. [결과](../../../analysis/OAM-DMA-RESULT.ko.md), [계약](../../../docs/nes-oam-dma-contract.md).
CPU $4014 write로 실제 DmaController 실행. RAM pages2/3×OAM start00/01/FC/FF×두 위상. 전송4,096bytes, read/write8,192건과 OAM snapshots4,096bytes가 actual Mesen runtime/ROM oracle에 일치한다. pause513/514cycles가 모든 page/start 조합에서 확인되고 CPU INC가1회씩 복귀한다.
코어 수정 없음: compiled inventory는014와 동일. 기존 run_nes_rdy.ps1 + tests/nes-functional/oam_dma_tb.sv를 사용한다. 초기 ROM은 첫 pair가514만 있어 coverage 실패; 최종ROM에 초기3-cycle padding을 넣어 모두 통과했다. verifier 변수 shadow 오류와 초기 기록도 보존.
**다음 우선 작업: 실제 OAM DMA 중 IRQ/NMI 도착과 CPU 복귀. DMC/OAM 경쟁·rendering 쓰기·RMW trigger·memory stalls는 별도 관문.**
증거 ignored analysis/local-oam-dma-015/. 직전245 hashes/GBC152 hashes/upstream 보존, FLOAT process/listener0. 과거014의 IRQ/영상 회귀는 보존 결과이며 이번 재실행이 아니다. SMB3·NES→SNES·fit/STA·실기·license hold 미완료.

2026-10-05 최신: **NES-P2-RDY-014 read-stall NMI 보존 수정 및 회귀 통과**. [결과](../../../analysis/RDY-RESULT.ko.md), [계약](../../../docs/nes-rdy-contract.md).
14위치×4 interrupt modes=56조건, baseline/no-stall와3-cycle RDY-low 총112completion. read152회 정지/write16회 진행 및 RAM 결과/IRQ28/NMI28 보존 확인. 수정 전 case35/36/47/48 branch operand 정지에서 짧은 NMI 누락을 재현했다. mode00 really_rdy=0일 때 기존 NMI sample/edge gating을 허용하는 두 조건만 수정했다.
최신 실행은 tools/run_nes_rdy.ps1(-Mapper4 가능). 011 branch bus와012 IRQ latch 수정을 포함하며 이전 driver는 역사적 재현용. syntax 오류 이력 보존 및 wrapper FLOAT 시작 전 syntax preflight 추가.
NMI/IRQ42개·branch IRQ52개·Mapper4 140.02ms/245,760pixels 회귀 PASS, unpaused interrupt trace2개 및 frame/fetch/control/edges8개 동일. GBC152 hashes/upstream/원래draft 보존, FLOAT process/listener0.
**다음 우선 작업: 실제 $4014 OAM DMA 256-byte 전송과 CPU 복귀. 이번 synthetic RDY는 actual DMA나 외부 memory arbitration의 검증이 아니다. 정지 밖1-cycle NMI·반복 edge·MMIO·임의 RDY·상태복원도 남아 있다.**
증거 ignored analysis/local-rdy-014/. launcher02의 Python quoting 오류는 컴파일 전 실패이며 최종 성공에 포함하지 않는다. NES→SNES·SMB3·fit/STA·실기·license hold 미완료.

2026-10-05 최신: **NES-P2-INTERRUPT-PRIORITY-013 진단42개 통과**. [결과](../../../analysis/INTERRUPT-PRIORITY-RESULT.ko.md), [계약](../../../docs/nes-interrupt-priority-contract.md).
BEQ not-taken/same-page/cross-page에서 2-cycle NMI+held IRQ의 도착 순서와 mask 검사. NMI→IRQ21, IRQ→NMI12, IRQ-only3, NMI-only6. vector/return PC/first-entry cycle/handler counts 및 변조6종 PASS. 기준은 Mesen 소스 기반 oracle이며 Mesen runtime IRQ주입/실기 검증이 아니다.
코어 수정 없음, compiled T65는012와 동일. 기존012 runner+새 tests/nes-functional/interrupt_priority_tb.sv를 사용한다. 012의 branch56/MMC3 회귀는 보존 결과이고 이번 새 실행이 아니다.
**다음 우선 작업: RDY 정지·재개 시 bus/interrupt 보존. 1-cycle NMI/반복 edge/BRK hijack/다른 opcode/상태복원도 추가 검증 필요. 이번 결과를 전체 interrupt 정확성으로 일반화하지 않는다.**
증거 ignored analysis/local-interrupt-priority-013/. 직전199 hashes/GBC152 hashes/upstream 보존 확인. FLOAT process/listener0. SMB3·NES→SNES·fit/STA·실기 및 license hold 미완료.

2026-10-05 최신: **NES-P2-BRANCH-IRQ-012 이른 IRQ poll 보존 수정 및 회귀 통과**. [결과](../../../analysis/BRANCH-IRQ-RESULT.ko.md), [계약](../../../docs/nes-branch-irq-contract.md).
BEQ 5조건 × cycle별 pulse/held 52개 실제 RTL 시험. 수정 전 page-cross 앞/뒤의 cycle0 1-cycle IRQ를 놓친 2개를 재현했고 기존 IRQ_n_o latch의 유효 샘플을 보존해 모두 통과했다. 기준은 Mesen 소스에서 분리한 모델이며 Mesen 런타임 IRQ 주입이나 실기 측정이 아니다.
최신 수정본은 tools/run_nes_branch_irq.ps1을 사용한다(-Mapper4 가능). 011 branch-bus 수정도 포함한다. 이전 011/010 driver는 역사적 재현용으로 보존했다. 새 saved state나 instruction cycles 추가 없음.
기존 branch56개 및 Mapper4 140.02ms/245,760 pixels/CHR/IRQ 회귀 PASS. 원시 frame/fetch/control/edges8개는 010과 동일, 기존 IRQ4-dot offset 유지. GBC152 hashes PASS, upstream clean, FLOAT process/listener0.
**다음 우선 작업: NMI/IRQ 중첩 우선순위 및 분기 경계의 관측. RDY/DMA/CLI·SEI·PLP 경계도 별도 검증해야 한다. 현재 결과를 전체 CPU interrupt 정확성으로 일반화하지 않는다.**
증거는 ignored analysis/local-branch-irq-012/. 최초 잘못 선택된 변조 대상(PHA) 및 검증기 수정 이력도 보존했다. SMB3·NES→SNES·fit/STA·실기 및 license hold는 미완료.

2026-10-05 최신: **NES-P2-BRANCH-011 로컬 분기 bus 수정 및 회귀 통과**. [결과](../../../analysis/BRANCH-RESULT.ko.md), [계약](../../../docs/nes-branch-contract.md).
8 branch opcodes × 7 cases=56. 수정 전 taken48개에서 discarded-read 주소 오류를 재현했고, 생성된 T65 mode00의 주소 출력만 고쳐 모두 통과했다. cycle 수/PC 갱신/IRQ sampling 로직은 변경하지 않았다. 수정본은 tools/run_nes_branch.ps1, Mapper4 회귀에는 -Mapper4를 사용한다. 과거 006/009/010 driver는 수정 전 재현용으로 보존했다.
Mapper4 140.02ms/245,760 pixels exact, 원시 frame/fetch/control/edges 8개가 010과 동일. IRQ 상대 cycles 보존, polling dummy read9개가 E186으로 Mesen과 일치. 절대 IRQ timing 및 4-dot offset 기원은 아직 미확정.
**다음 우선 작업: 분기 각 cycle의 IRQ sampling 자체 진단. 현 56개는 interrupts disabled이므로 IRQ 경계 처리를 통과로 간주하지 않는다. RDY/DMA/16-bit wrap/MMIO 등 추가 호환성도 남아 있다.**
증거는 ignored analysis/local-branch-011/. 초기 reset 관측 실패와 CRLF/LF 해시 assertion 실패를 포함해 보존했다. GBC 검증 PASS, upstream/기존 source 보존, FLOAT process/listener0 확인. license hold/SMB3/통합/fit/실기 미완료.

2026-10-05 최신: **NES-P2-IRQ-PHASE-010 상대 사이클 검사 통과**. [결과](../../../analysis/IRQ-PHASE-RESULT.ko.md), [계약](../../../docs/nes-irq-phase-contract.md).
009의 4-dot ack 차이는 IRQ 전 RAM8 read부터 존재하고 이후 10개 bus landmark에도 그대로 유지된다. counter3..6의 첫 stack write→ack는 RTL/Mesen 모두 18 CPU cycles다. IRQ 경로의 추가 cycle 차이는 발견되지 않았다. 절대 CPU/PPU 정렬과 Mesen IRQ 입력 assertion은 미검증이다.
계측 외 core/ROM 변경 없음. 기존 통합 검증 PASS, RTL 8개/Mesen 6개 원시 파일이 009 최종본과 동일. 최초 observer timestamp race 및 수정 후 실행을 모두 ignored analysis/local-mmc3-irq-phase-010/에 보존했다.
**다음 우선 작업: taken/not-taken/page-cross branch의 discarded read 주소와 IRQ sampling 자체 진단. 현 loop에서 RTL E182 / Mesen E186 차이가 보이므로 full CPU bus conformance를 선언하지 않는다.**
GBC 152 source hash 검사 PASS, 원본 upstream 및 license hold 보존. 무료 FLOAT 종료 확인. SMB3·메모리 stall·NES→SNES 통합·fit/STA·실기 미완료.

2026-10-05 최신: **NES-P2-MMC3-INTEGRATED-009 기능 진단 통과**. [결과](../../../analysis/MMC3-INTEGRATED-RESULT.ko.md), [계약](../../../docs/nes-mmc3-integrated-contract.md).
자체 Mapper4 CPU/PPU/MMC3 RTL 140.02ms, Mesen 4프레임 245,760화소와 화소 사용 fetch 61,440건 일치. PRG readback/NMI frame/CPU IRQ handler/ack 확인, A12 상승 7,712건 검사. 최종 RTL/Mesen 반복 기록 동일, 기존 경고 42개 유지.
**다음 우선 작업: 공통 counter3..5의 IRQ ack 관측 차이 4 PPU dot 분석. RTL cart_ce와 Mesen CPU callback 기준점을 맞추고 실제 interrupt latency 차이인지 확인한다. 정확한 IRQ cycle 일치를 완료로 선언하지 않는다.**
초기 polling ROM의 Mesen frame counter 중복을 보존하고 NMI flag 방식으로 교체했다. 원인 확정 없이 초기 기록을 지우거나 최종 통과로 세지 않는다.
원시 기록은 ignored analysis/local-mmc3-integrated-009/{rtl-01..03,mesen-01..03,rom-01..02,baseline,baseline-status}. 원본 ROM SHA는 결과 문서 참조. 기존 NROM runner 불변, 전용 integration driver가 pinned adapter 생성만 확장.
GBC 기준·upstream·license hold 보존. 무료 FLOAT 종료 확인. SMB3·메모리 stall·NES→SNES 통합·fit/STA·실기는 여전히 미완료.

2026-10-05 최신: **NES-P2-MMC3-UNIT-008 완료**. [결과](../../../analysis/MMC3-UNIT-RESULT.ko.md), [계약](../../../docs/nes-mmc3-unit-contract.md).
표준 Mapper4 단독 RTL PRG/RAM 4,112·CHR/미러링 8,200·IRQ 228건 통과. 12개 실제 A12 상승 위상 검사, 최종 두 실행 trace 동일. 오류/경고 0은 매퍼 단독 범위다.
최초 시험의 task-gated clock/고정 상승 phase 문제를 고쳤고 최종 audit는 그 최초 trace를 거부한다. 모든 기록은 ignored analysis/local-mmc3-unit-008/에 보존.
다음: 자체 Mapper4 ROM + 최소 cart adapter + CPU/PPU 통합, 실제 PPU A12/CPU IRQ service와 Mesen 비교. 이번 시험은 Mesen runtime/SMB3/통합 코어 성공이 아니다.
MMC3.sv 개별 파일 license hold 유지. 기존 NROM runner/정규화 규칙/원본 upstream 보존, 임시 FLOAT 서버 종료 확인. GBC 회귀 검증 PASS.

2026-10-05 최신: **NES-P2-RTL-FETCH-007 완료**. [결과](../../../analysis/RTL-FETCH-RESULT.ko.md), [관측·재현](../../../docs/nes-rtl-fetch-contract.md).
실제 Questa RTL 140.02ms, 주소 구분 CHR의 연속 4프레임 245,760화소가 Mesen과 일치. 화소 사용 fetch 61,440건 주소/값 차이 0, 배경 latch 65,552건 검사, 실패 검출 5종 통과.
기존 RTL-006 driver/래퍼 그대로 재사용. 코어 추가 수정 없음, 무료 FLOAT 실행 뒤 서버 정상 종료. 경고 42개 유지.
증거는 ignored `analysis/local-rtl-fetch-007/run-01/`, 과거 상태는 baseline-status/, 검증기 파일명 패딩 수정 이력은 verifier-history/.
다음은 MMC3 자체 진단·bank 물리 mapping·A12/IRQ 비교. NROM PPUCTRL 시험에서 실제 게임 cache miss나 MMC3 성공을 추론하지 않는다. 전체 P1/P2·NES→SNES 통합·fit/STA·SMB3·실기는 미완료.

2026-10-05 최신: 사용자가 **재발 방지 명시 후 NES 개발 재개**를 지시했다. 아래의 이전 중지 기록은 해제됐다.
[RTL-006 결과](../../../analysis/RTL-RESULT.ko.md), [FLOAT 실행 규칙](../../../docs/questa-execution.md)를 먼저 읽는다.
전역/checkout AGENTS.md와 `tools/run_nes_functional.ps1`을 사용한다. 기본 uncounted 경로는 Python driver가 빌드 전에 거부한다. 별도 license smoke를 반복하지 않는다.
실제 NROM RTL 120.02ms PASS: 61,440화소 exact, CPU 12 master clocks, 미정값/오디오 주기 오류 0, 입력 반응 확인.
로컬 수정: T65 폭, timing counter reset, PPU cold_reset/sprite-zero-hit 초기화. de-jitter padding 비활성. upstream 원본 보존.
`analysis/local-rtl-006/run-01..07`에 실패/성공 로그와 변환 사본 보존. 005 driver/testbench 원본은 baseline/ 아래 보존.
Questa 경고 42개는 남아 있고, ideal memory·단일 NROM cold boot 한정이다. 다음은 주소 구분 CHR 진단과 MMC3/A12/IRQ 비교. 전체 P1/P2·fit/STA·SMB3·실기는 미완료.

2026-10-05 사용자 지시: **NES 개발 진행 중지. Questa 라이선스부터 확인.**
라이선스 재확인 완료: 기존 무료 Starter FLOAT(intelqsimstarter, 1 seat, 2027-09-19 만료)로 같은 Standard 설치 경로의 10ns 최소 실행 PASS, 오류/경고 0.
원인은 NES runner가 원래 GBC 프로젝트 `probes/questa-license/probe_float.ps1` 래퍼를 누락하고 기본 uncounted 파일을 직접 사용한 것. 새 유료 라이선스 불필요.
사용자가 NES 작업을 재개하면 기존 래퍼의 `-RunOnly -AfterSmokeScript <절대 작업 스크립트> -QuestaBin <기존 Standard win64>` 경로를 사용한다. 매번 별도 smoke 검사를 반복할 필요는 없다.
임시 서버는 실행 종료 후 내려가는 구조다. 영구 환경변수/서비스/라이선스 원본 변경 없음, 종료 후 서버 프로세스 및 18000–18002 listener 0개 확인.
이번에는 라이선스 최소 실행만 확인했으며 NES RTL 기능 시험을 재개하지 않았다. 아래 FETCH-005 당시 실패 로그는 과거 사실로 보존한다.
진단 원본: 시스템 TEMP의 `questa-session-recheck-20261005-01/result.json` 및 runtime 로그(로컬 전용, Git 제외).

최신 진행: [실제 CHR 관측 — FETCH-005](../../../analysis/FETCH-RESULT.ko.md), [계약·재현](../../../docs/nes-fetch-contract.md).
최소 RTL 컴파일·최적화 통과, Questa runtime은 Windows 세션 라이선스 제한으로 실행 전 실패(exit 12).
Mesen 자체 NROM 8프레임의 실제 CHR fetch와 256×240 RGB exact 검증 및 재실행 동일, 실패 검출 4종 통과.
전체 CHR가 처음부터 있는 PPUCTRL 전환 시험이며 MMC3/게임 cache miss 검증은 아님.
다음은 자체 MMC3 관측·resident/miss 구분과 RTL 실행 환경/경고 검토. P1/P2·239줄 정책·SMB3·실기는 여전히 미완료.
원시 증거는 ignored `analysis/local-fetch-verified/`, 최신 재현 소스는 fetch-artifacts.json 참조. 기존 독립 checkout/브랜치를 계속 사용.

최신 진행: [두 CHR 집합의 상주·사전 적재 — RESIDENT-004](../../../analysis/RESIDENT-RESULT.ko.md), [계약·재현](../../../docs/nes-resident-contract.md). 미래 데이터 가용성은 합성 입력의 조건이며 실제 게임에서 미입증입니다.

최신 진행: [CHR 캐시 전송 결과 — CACHE-003](../../../analysis/CACHE-RESULT.ko.md), [캐시 계약](../../../docs/nes-cache-contract.md).

> 2026-10-05 최신: [NES-P1-STREAM-002 동적 전송](../../../analysis/STREAM-RESULT.ko.md). 진단 ON/OFF 각 128프레임과 reset/오류 주입 검증 추가. 전체 P1·FPGA·SMB3·실기는 미완료.

> 최신 NES-P1-001 결과: [영상 구현 및 검증](../../../analysis/P1-RESULT.ko.md). 아래는 착수 당시 기록입니다. NROM 최소 fit과 고정 장면 SNES 재생이 추가됐으나 전체 P1/실기/SMB3는 미완료입니다.

# NES 코어 작업 착수 인계

2026-10-04 사용자 요청: 공개 완료된 GBC 이식의 경험을 이어 받아 다음 코어로 NES 구현을 시작한다. NES는 아직 구현·합성·실기 성공 전이다. 이 문서는 초기 실행 계획이며 upstream 선정이나 지원 범위의 완료 선언이 아니다.

## 최신 상태를 먼저 복원

1. [현재 상태](../../../docs/PROJECT-STATUS.ko.md), [GBC 이식 회고](../../../docs/development/GBC-PORTING-LESSONS.ko.md), [이식 절차](../../../docs/PORTING-PLAYBOOK.ko.md), [개발 구조](../../../docs/development/ARCHITECTURE.ko.md)를 읽는다.
2. sd2snesHST 0.9.0은 공개됐고 GBC 기준은 C44다. 예전 C10 인계의 “점멸·빠른 로딩·자동 저장·메뉴 미완료”를 현재 상태로 취급하지 않는다. [제품 매핑](../../../release/product-version-map.json)과 [GBC 지원 범위](../../gbc/README.md)를 기준으로 삼는다.
3. 실행 코어의 출처는 Gameboy_MiSTer, CGB 부트 코드는 SameBoy 유래다. 새 NES의 출처는 별도로 조사한다.
4. 공개된 바이너리·태그·저장 형식을 보존한다. GBC 검증 경로를 이동하거나 NES 때문에 선제적으로 공통화하지 않는다. 개발 저장소의 최신 master와 이 인계 변경을 포함한 별도 `codex/` 작업 브랜치에서 진행한다.

## 1단계: 후보 선정과 예산

현재 유지되는 NES FPGA upstream 후보를 공식 저장소·고정 커밋에서 조사한다. 출처·라이선스, CPU/PPU/APU·매퍼 의존성, 외부 SDRAM/DDR·플랫폼 전용 코드, state 접근 가능성, Cyclone IV 합성 가능성을 비교한다. 유명한 코어라고 바로 선정하지 않는다.

[제안서](../../CORE-PROPOSAL.ko.md)를 NES용으로 채우고 각 값은 측정/자료 근거/가정을 구분한다. 첫 실행 범위는 기본 카트리지 경로와 최소 매퍼를 제안하고, 실제 선택 이유를 기록한다. iNES/NES 2.0·trainer·mirroring·PRG/CHR RAM·배터리 등의 입력 판별은 선택한 지원 범위에 맞춰 명시하고 미지원 파일은 명확히 거절한다. FDS·추가 음원·특수 주변기기·전 매퍼·강제 저장을 처음부터 약속하지 않는다.

하드웨어는 기존 FXPAK Pro / Mk.III STM32 + EP4CE15F17C8, 무개조가 출발점이다. NES는 GBC와 별도 FPGA 이미지로 동작한다. 코어/변환기/중재기/FIFO/음향/저장 예상치를 분리하고 LE·LAB·M9K 블록·PLL·외부 메모리·버스 점유를 합산한다. NES 화면을 SNES PPU로 보내는 해상도·팔레트·업데이트 비용과 오디오·frame pacing을 새로 계산한다. crop·색 축소·정상 모드 프레임 폐기를 조용히 도입하지 않는다.

## 2단계: 가능한 후보를 실제로 합성

코어별 독립 소스/빌드 경로를 만들고 출처·고지를 등록한다. 상용 ROM 없이 합성 가능한 최소 wrapper와 자체 진단 입력을 사용한다. 원래 제약을 보존하고 클록·리셋·CDC·메모리 계약과 미제약 경로를 기록한다. 같은 후보의 전체 출력 경로를 포함할 자원 여유가 있는지 판단한다.

GBC 빌드 스크립트는 C44 해시 일치를 요구하는 재현 도구다. NES 출력에 맞추려고 기존 golden hash 검사를 끄지 말고 NES 전용 빌드 항목을 추가한다. Quartus/시뮬레이터는 기존 설치를 확인하고 새 설치나 라이선스 변경을 가정하지 않는다.

## 3단계: 최소 수직 통합

자체 진단 프로그램으로 ROM 로드 → 코어 RUN → 화면 → 입력 → 음향 → 메뉴 복귀·리셋의 한 경로를 완성한다. 새 파일 확장자/코어 ID/FPGA 이미지/renderer/명령 공간은 충돌 여부를 확인한 뒤 정한다. 기존 `.egbc`, `.gb`, `.gbc` 분기와 저장 파일을 보존한다.

처음부터 다음 실패를 자극한다: 로딩 후 기존 cleanup 명령, 늦은 메모리 응답, 연속 주소 DMA, 메뉴 중 output backpressure, 마지막 바이트 SPI read-ahead, 타임아웃/부분 SD 쓰기, cold/warm reset. 모델 통과와 실제 보드 결과를 분리한다.

## 4단계: 실기 후보와 확장

모델·동일 후보 fit/STA·인터페이스 검사 통과 후 설치 세트와 해시 검사, 백업·복귀 방법, 짧은 관측 항목을 갖춘 NES 시험판을 만든다. 공통 MCU/출력 경로를 바꾸면 GBC 시작·메뉴 복귀·SRAM·state·리셋 회귀와 GBC → NES → GBC 전환을 함께 검사한다.

최소 실행 뒤 매퍼·배터리 저장·호환성 표본을 늘린다. 메뉴·상태 저장·배속의 GBC 구현은 설계 참고이며 NES에 자동 호환되지 않는다. 초기 조사를 넘어 의미 있는 구현을 지속하되 자원/출력 대역폭 한계가 입증되면 수치·실패 결과와 대안을 제시한다. 기존 0.9.0 공개 자산은 수정하지 않는다.

## 다음 보고에 필요한 산출물

- 고정 upstream과 라이선스 비교, 선택·탈락 이유.
- NES 제안서, 실제 또는 미측정으로 표시한 자원·영상/음향 예산.
- 첫 합성/시험 결과와 재현 명령, 소스·제약 해시, 미제약/미검증 범위.
- 진행할 통합 경로와 첫 실기 관문. 사용자가 정해야 하는 품질·지원 범위 선택만 질문한다.

GBC 회고의 로컬 증거 색인은 [여기](../../../release/gbc-porting-evidence.json)에 있다. 과거 개인 테스트 입력은 로컬에서만 확인하며 공개 문서에 복사하지 않는다.
