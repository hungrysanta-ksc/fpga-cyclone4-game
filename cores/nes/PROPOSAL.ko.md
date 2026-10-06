2026-10-06 개발053: **ROM 핀 적재 후 실제 코어 실행 — 실기044 유지.**

360505단위 검사/180226바이트 읽기 확인,8오류 시나리오,2종8프레임491520픽셀 일치. 패킷 내용은 같고 공개 tick 차이는 {'banks32': [-4, -4, -4, -4], 'fine_x': [1, 1, 1, 1]}로 기록했다. 공동13612LE/929LAB/26M9K,34LAB여유. MCU SPI/보드 클록/소비자/실제 타이밍은 미완료, 새 SD 이미지 없음. [결과](../../analysis/ROM-BOOT-RESULT.ko.md), [계약](../../docs/nes-rom-boot-contract.md).

아래는 이전 단계의 결과와 이력이다.

2026-10-06 개발052: **읽기 전용 PSRAM 핀 제어기와 NES/메모리 CDC 연결 — 실기044 유지.**

2종 실제 코어8프레임의491520픽셀·16064바이트·진행 기록이051과 같다. 최종16위상/203392검사,8400완료/208리셋취소, 왕복4NES클록. 공동13547LE/925LAB/26M9K,38LAB여유.25ns핀 모델 가정이며 실제 부품/CDC 배선/PLL/로더/소비자/STA는 다음 관문이다. 전체 코어 실행 소스와 최종 소스의 속성·상수폭 표기 차이는 검증기에 명시했다. 새 SD 이미지 없음. [결과](../../analysis/ROM-PHYSICAL-RESULT.ko.md), [계약](../../docs/nes-rom-physical-contract.md).

아래는 이전 단계 결과와 이력이다.

2026-10-06 개발051: **현재 코어 주소를 이용한 조기 ROM 읽기 —2·3·4클록 응답 통과. 실기044 유지.**

각 지연에서8프레임491520픽셀·16064바이트·진행 기록이050과 같다.624788요청,4168단위 검사.기존050의2클록 실패와051의8클록 실패를 결정 시점 기록으로 보존했다.공동 fit13420LE/935LAB/26M9K,LAB28개 남음.다음은 실제 메모리·빠른 클록/CDC·보드 공동 자원 검증이다.새 SD 이미지 없음. [결과](../../analysis/ROM-EARLY-RESULT.ko.md), [계약](../../docs/nes-rom-early-contract.md).

아래는 이전 단계의 결과와 이력이다.

2026-10-06 개발050: **공유 ROM 중재·읽기 마감 감시 검증 완료. 실기044 유지.**

동기식1클록 응답 모델에서624618요청,8프레임491520픽셀·16064바이트·전체 기록이049와 같다.2클록 응답 모델은 두 ROM에서 PPU 마감 초과를 검출했다.4148단위 검사 통과.공동 fit13538LE/928LAB/26M9K,LAB35개 남음. 실제 PSRAM/클록 경계·로더·SNES 소비자·보드 오류 복구는 다음 단계이며 새 SD 이미지 없음. [결과](../../analysis/ROM-SERVICE-RESULT.ko.md), [계약](../../docs/nes-rom-service-contract.md).

아래는 이전 단계의 결과와 이력이다.

2026-10-06 개발049: **12KiB 내부 RAM·초기화 통합 검증 완료. 실기044 유지.**

실제 코어와 fit에 같은 RAM을 연결했다. 초기화8192클록(약0.381ms),153604단위 검사,8프레임491520픽셀 일치. 이전048 대비 시간 기록만4클록 이동했다. 최종13477LE/920LAB/26M9K이며 외부 ROM은 아직 이상적/가상이다. 매 RESET PRG RAM 초기화는 진단 정책이므로 저장 게임에 그대로 적용하지 않는다. [결과](../../analysis/LOCAL-MEMORY-RESULT.ko.md), [계약](../../docs/nes-local-memory-contract.md). 다음은 외부 ROM 서비스·보드 클록/로더·SNES 소비자와 공동 fit/STA다. 새 SD 이미지 없음.

아래는 이전 단계의 결과와 이력이다.

2026-10-06 개발048: **OAM 쓰기 구조 최적화 —870 LE 절감, LAB 여유10→37. 실기044 유지.**

채택 경로는 `tools/nes_oam_compact.py`다. 원본과216362클록의 상태/메모리 비교를 통과했고, 수정 코어8프레임의16064바이트·491520픽셀 및 진행 기록이047과 같았다. 최종13283LE/926LAB/26M9K. 묶음 분리만 한 첫 시도는 자원이 늘어 미채택했다. [결과](../../analysis/OAM-BANKED-RESULT.ko.md), [계약](../../docs/nes-oam-banked-contract.md). 다음은 실제 메모리/클록/소비자 공동 통합이며, 완성 보드 fit/STA는 미확인이다. 원본 OAM 평가 카운터의 초기화/RESET 범위도 별도 확인한다. 새 SD 이미지 없음.

아래는 이전 단계의 결과와 이력이다.

2026-10-06 개발047: **실제 NES 코어→PPU 감시→NCR1→044 전송 통합 검증. 실기 기준044 유지.**

새 코어 실행8프레임에서131104 BG fetch,16064전송 바이트,491520복원 픽셀이 실제 PPU 출력과 일치했다. PPU 감시20항목 통과. 진단 ROM 범위의 통합 fit는14153LE/953LAB/26M9K이며 LAB 여유10개뿐이다. 다음 우선순위는 보드 자원 예산·동등성 회귀를 동반한 여유 확보, 실제 메모리/로더와 SNES 런타임 연결이다. [결과](../../analysis/NCR1-LIVE-RESULT.ko.md), [계약](../../docs/nes-ncr1-live-contract.md). 전체 STA/게임/실기 통과로 확대하지 않는다. 새 SD 이미지 없음.

아래는 이전 단계의 결과와 이력이다.

2026-10-06 개발046: **순차 BG fetch→NCR1 생성→045→044 전송 경로 검증 완료. 실기 기준044 유지.**

기록된 NES fetch131104개를 원래 간격으로 입력해16항목/18072바이트를 검증했다. 최종 인코더는672LE/2M9K/전체118LAB이며, 배치 후 기능 넷리스트에서도3프레임6024바이트가 일치했다. [결과](../../analysis/NCR1-ENCODER-RESULT.ko.md), [계약](../../docs/nes-ncr1-encoder-contract.md). 실제 PPU/매퍼 tap·모드 감시, 공동 배치, SNES 런타임 소비자는 다음 단계다. 과거 입력 기록의 재생을 새 NES 코어 실행이나 실기 검증으로 부르지 않는다. 새 SD 이미지 없음.

아래는 이전 단계의 결과와 이력이다.

2026-10-06 개발045: **메모리 패킷 생산기 구현·RTL 회귀와 단독 fit 완료. 실기는044 유지.**

완성된 참조 패킷8개를 가변 지연 메모리에서 읽어044 전송부로 전달했다.3클록 조합×17항목, 총57459바이트 일치. 최종416LE/155레지스터/0M9K/전체61LAB이며 epoch 래치 추론을 수정했다. 실제 NES 인코더·물리 메모리 서비스·공동 배치·SNES 런타임 소비자는 다음 연결 대상이다. [결과](../../analysis/PACKET-MEMORY-RESULT.ko.md), [계약](../../docs/nes-packet-memory-contract.md). 새 SD 교체는 없다.

아래044 실기 성공 기록과 이전 이력을 유지한다.

2026-10-06 현재: **044 H1 기본 실기 통과 — 정상 화면 순환과 RESET 복구, GBC 정상 플레이 보고**.

사용자가 자동 종료 없이 LINK SCREEN1→2→3→1 반복 및 GBC 정상 플레이를 확인했다. 첨부 로그는 프로토콜0x44, status03(오류 없음), RESET_ASSERTED, start/stop0, base_restored1이다. 약19.54초는 설정을 포함한 세션 기록이며 정확한 화면 표시 시간은 아니다. 새 영상이나 SD 읽기 해시는 제공되지 않았다.

[실기 결과](../../analysis/H1-HARDWARE-044-RESULT.ko.md)를 최신 근거로 삼는다. 044 이미지와 기존 실패 증거는 그대로 보존한다. H1 재진입·장시간 반복은 미확인으로 남기고 실제 NES 생산자/메모리/소비자 통합 계약을 다음 개발 단계로 진행한다. 진단 통과로 R2/R4 전체나 전기 타이밍을 완료 처리하지 않는다. 현재 증상은 이번044 실행에서 재현되지 않았으며041의 정확한 물리적 원인까지 확정한 것은 아니다.

아래는 이전 단계 당시의 판단을 보존한 이력이다.

2026-10-06 현재: **NES-H1-SAMPLING-044 제한된 실기 진단 시험 준비**.

입력 샘플링·공유 오류 기록을 유지하고 주소 비교의 X 재결합 문제를 이진 동등식으로 수정했다. RTL, MCU 파형, 실제 fit/내부 STA, 설치·복원8조건을 통과했다. 원래 SDF는126바이트에서 실패하며 그대로 보존했다. 별도 첫단 해소 가정의 old/new/mixed 모델은 각각512바이트를 통과했다. 이는 전기적 타이밍 통과나 실기 원인 확정이 아니다.

[검증 결과](../../analysis/H1-SAMPLING-RESULT.ko.md), [시험 안내](../../docs/nes-h1-sampling-test.ko.md), [입력 계약](../../docs/nes-h1-sampling-contract.md).
다음은041 백업 후044 MCU/FPGA 쌍으로1→2→3 순환·RESET·재진입과 로그044를 확인하는 것이다. 실제 최신 관측은 여전히041 자동 복귀 실패다. GBC/H0 기록을 유지한다.

아래는 이전 단계의 당시 판단을 보존한 이력이다. 최신 지시는 위044 안내를 따른다.

2026-10-06 최신: **NES-H1-TIMING-042 조사**, 새실기이미지 없음.

## 최신043 상태 (2026-10-06)

입력 샘플링과 단일 등록 오류 이벤트를 구현했다. 정상936/실제 오류504건, 보드9항목, MCU SPI 및 실제 fit/STA는 통과했다. SDF에서는91바이트 뒤 불확정값이 남아 실기 패키지는 보류한다. 기존041을 반복하지 않는다. [검증 결과](../../analysis/H1-QUALIFIED-RESULT.ko.md)와 [입력 계약](../../docs/nes-h1-qualified-contract.md)을 기준으로 첫 불확정값 전달과0/1 상대 샘플 지연을 먼저 검증한다.
[분석 결과](../../analysis/H1-TIMING-RESULT.ko.md).
실제041 프로토콜확인,동일실패. 집계frontend1과원인0x20(예상frontend2)이상충하므로순서오류로단정하지 않는다.
실제041 배치넷리스트: SDF적용227바이트뒤실패/617타이밍위반,지연없는동일대조512바이트통과.
첫단 비동기샘플/X모델의한계와내부최적화Z별칭을포함하므로실기원인확정으로부르지 않는다.
다음:일관된입력샘플·단일등록오류event와공유기록설계/회귀후새실기후보.현재041반복시험 요청없음.
아래는 과거 단계 기록이다.

2026-10-06 최신: **NES-H1-EDGE-041** frontend 최초 원인 계측 쌍 준비.
[결과](../../analysis/H1-EDGE-RESULT.ko.md), [설치 안내](../../docs/nes-h1-edge-test.ko.md).
040 재시험 실패:화면 미완성 후 자동 복귀,frontend1/stage0/producer0,ROMSEL낮음/40:80E0.
040 RTL 결함 수정만으로 실기는 해결되지 않았다.041은040 동작을 유지하며 정확한 원인·상태·읽기 길이를 계측한다.
실제RTL 정상156/오류84·카운터교정·보드9·MCU파형704/328·ARM/full fit/STA/ASM·MCU decode218719·복원8조건 통과.
**041 MCU+FPGA 둘 다 설치,프로토콜0x41/로그041. 실행표식037/화면034 유지.**
다음:한 번 재현하고 nes-h1-last-041.txt 회수.041은 진단용이며 실기 해결 주장이 아니다.
아래는 과거 단계 기록이다.

2026-10-06 최신: **NES-H1-RELEASE-040** 정상 읽기 종료 오검출 수정 FPGA 준비.
[결과](../../analysis/H1-RELEASE-RESULT.ko.md), [설치 안내](../../docs/nes-h1-release-test.ko.md).
039 실기 frontend1/stage0/producer0. 정상 RD/ROMSEL 종료로 같은 오류 상태를 실제 RTL에서 재현했다.
수정본 정상156·실제오류72·전체보드9·MCU파형448/200·full fit/STA/ASM·MCU decoder223004바이트·설치9조건 통과.
**040 FPGA 하나 교체,039 MCU 유지. 실행표식037/화면034/로그039 유지.**
다음:040 실기1→2→3 순환/RESET/재진입/GBC 확인. 수정040 실기 미실행,전기타이밍 미검증.
아래는 과거 단계 기록이다.

2026-10-06 최신: **NES-H1-FAULT-039** 최초 오류 스냅샷 진단 쌍 준비.
[결과](../../analysis/H1-FAULT-RESULT.ko.md), [설치 안내](../../docs/nes-h1-fault-test.ko.md).
038 실기 로그:F2_STATUS/07,초기진입/STOP 성공,base복구 완료. 실제 하위 오류는 미확정이다.
039는 MCU+FPGA 모두 변경하며 프로토콜39다. 이전036 FPGA와 섞지 않는다. 화면034/실행표식037 유지.
ARM·호스트15·실제RTL파형448/200비트·보드9조건·full fit/STA/ASM·실제MCU decode·설치8조건 통과.
다음:한 번 재현 후 sd2snes/nes-h1-last-039.txt 회수. 진단 보강이며 실제 순환 문제 해결 주장이 아니다.
아래는 과거 단계 기록이다.

2026-10-06 최신: **NES-H1-RUNTIME-038** 자동 복귀 사유 기록용 MCU 준비.
[결과](../../analysis/H1-RUNTIME-RESULT.ko.md), [실기 안내](../../docs/nes-h1-runtime-test.ko.md).
사용자037 실기:LINK SCREEN1 뒤 조작 없이 메뉴로 복귀. 순환 실패/원인 미분류이며 성공 처리하지 않는다.
038은 FPGA036 그대로, MCU 종료 원인만 SD 텍스트로 기록한다. 원인 수정/실기 통과 주장이 아니다.
기존 NES H1 037.nh1로 한 번 재현한 뒤 sd2snes/nes-h1-last-038.txt를 확인한다.
ARM 빌드,호스트15조건,실제RTL파형224샘플/88비트,MCU 교체·복원8시험 통과.
아래는 이전 단계 기록이다.

2026-10-06 최신: **NES-H1-BRINGUP-037** 복구 가능한 실기 묶음 준비 완료.
[결과](../../analysis/H1-BRINGUP-RESULT.ko.md), [실기 안내](../../docs/nes-h1-bringup-test.ko.md).
035 MCU+036 FPGA 바이트 그대로. 화면 제목은 NES H1 034. 이번 실제 Questa24회와 설치/복원12시험 통과.
다음은 동일한 기존 정상 보드에서 짧은 화면→RESET→재진입→GBC 복귀 실험이다.
패키지는 analysis/local-h1-bringup-037/NES-H1-BRINGUP-037.zip. SD 쓰기/실기 실행은 아직 없다.
38입력/11출력 미제약·전기 타이밍 unknown 유지; 묶음 준비를 full electrical signoff로 부르지 않는다.
이하 과거 단계 기록은 해당 시점의 결과다.

# NES 개발 계획 재점검 — 2026-10-05 R1

SPDX-License-Identifier: MIT.

이 문서는 현재 실행 계획이다. 과거 실험의 “다음 작업”보다 우선한다. 기술 후보는
NES-H1-SPI-036(MCU035/인터페이스031/생산기033), 구현은 NES-P2-RDY-014다. 최근 기능 검증 후보는017이다. 계획 갱신 자체를 새 구현 성과로 세지 않는다.
[현재 상태](README.md), [기계 판독 계획](../../docs/nes-development-plan.json).

2026-10-06 우선 갱신036:034 FPGA와035 MCU의 SPI sample 시점 불일치를 재현·수정했다.
C 파형224읽기/응답88비트와 보드6조건 회귀,동일소스fit/STA/ASM 및 RBF/BI3 생성 완료.
1,302LE/104LAB/44M9K. 실제 MCU RLE 해제 코드209,988바이트 exact.
아래035의 FPGA 이미지 생성 대기는 해소됐다. 외부 IO/CDC/turnaround와 복구 설치묶음·실기는 남는다.
[036 결과](../../analysis/H1-SPI-RESULT.ko.md).

2026-10-06 우선 갱신035: H1 실제 STM32 바인딩과 메뉴 수동 진입3개를 추가했다.
전체 ARM 빌드 경고0,호스트 GPIO/SPI·RESET·오류복구11조건 통과.USB IRQ의 고속SPI 재진입도 보호한다.
034 배치의 외부 경로 지연은 추출했으나38입력/11출력은 여전히 미제약이다.
아래034의 STM32 연결/빌드 대기는 해소됐다. 실제 MCU 실행·IO/CDC·GBC 전환 회귀·FPGA ASM과 실기묶음은 남는다.
[035 결과](../../analysis/H1-FIRMWARE-RESULT.ko.md).

2026-10-06 우선 갱신034: H1의 실제135핀/PLL/ROM/SPI 시작·정지를 구현했다.
실제fit1298LE/110LAB/44M9K와 내부STA 양수,RTL/Mesen/host C시험 통과.
외부38입력/11출력 미제약과 STM32/메뉴연결은 남았다. 다음은이두관문 후전체후보검증·실기묶음이다.
[034 결과](../../analysis/H1-BOARD-RESULT.ko.md).아래033의보드PLL/핀/ROM 미구현은 이번에해소했으나전체IO signoff는아니다.

2026-10-06 우선 갱신033: H1 자체 생산기·SNES DMA 프로그램 및 분리된 실제 RTL/Mesen 실행 완료.
H1 전용fit1,144LE/104LAB/20M9K. Lua MMIO모델을 사용한 Mesen 결과는 물리 버스 검증이 아니다.
다음은 실제 보드·ROM공급·MCU로더·RESET 세대·복귀 연결과 같은 후보 fit/STA다.
032의 코어 공동fit/40LAB 여유는 별도 유지하며 H0 기본 육안 통과 상태도 유지한다.
[033 결과](../../analysis/H1-PATTERN-RESULT.ko.md).

2026-10-06 우선 갱신032:동일소스코어+기본RAM+031전송부공동배치13,417LE/923LAB/24M9K 성공.
별도LAB합992가아닌실제공동배치값으로판단한다.남은LAB40은추가구현가능성을보장하지않는다.
아래031의jointfit대기는해결됐으며다음은H1자체producer/실제PPUDMA/보드·loader·복귀연결이다.
이probe는producer가external인공동배치시험이며기능통합/STA/실기성공으로세지않는다.


2026-10-06 우선 갱신031:030의 사용자 정상 보고/영상으로 H0기본육안확인 통과.
pin frontend/동기RAM variant를 통합하여3×13조건/19,218B와027대조14조건을통과했다.
실제전송부fit1,139LE/111LAB/12M9K.018과단순LAB합992>963이므로전체코어+전송부jointfit을우선측정한다.
H1자체생산기→실제PPUDMA·boardPLL/핀/IO/CDC/로더·복귀작업도계속한다.
아래030실기결과대기는과거기록이며현재H0기본육안통과상태가우선한다.


2026-10-06 우선 갱신:029 H0 사용자 실기는 정적인 글리치형 무늬여서 정상 판정 불가.
자동 화소 비교 도안을 수동 실기 확인으로 재사용하지 않는다.030 한ROM의 식별 문자/큰 도형/60프레임 순환을 실제 Mesen으로 검증하여 교체했다.
[030 실기](../../docs/nes-visual-h0-test.ko.md) 결과를 받으면서 H1 실제bus/PPU DMA 통합을 진행한다. 아래029 준비 완료는 과거 패키지 상태다.

**판정: 구성요소 검증은 진전했지만, 제품 성립성을 결정하는 영상·메모리·전체 자원 검증이 뒤처졌다.
이후 우선순위를 세부 CPU/APU 검사의 연속 확장에서 실제 부하와 통합 경계 검증으로 바꾼다.**
확정 완료일/소요시간 기준선은 없으므로 “일정대로 완료 중”이나 일정 지연률을 단정하지 않는다.
실험 번호017이나 테스트 개수는 제품 완성률이 아니다. 근거 없는 완료 백분율과 출시일은 제시하지 않는다.


2026-10-05 R1 실행 갱신: [최신 자원 실측](../../analysis/RESOURCE-RESULT.ko.md).
코어+MMC3+CPU/CIRAM/PRG RAM12KiB는12,281LE/881LAB/12M9K로 fit했다. 내부 setup+10.943ns/hold+0.152ns,
외부IO 미제약·영상/controller/CDC 미포함. R1 전체 종료는 아니며 다음 실행은 R2 실제 fetch 부하 분석이다.
R1의 미측정 비용은 R2에서 packet/FIFO/cache 요구를 정한 뒤 다시 채운다. 아래 실행 단계 정의는 유지한다.

2026-10-05 R2 실행 갱신: [실제 fetch 부하019](../../analysis/FETCH-WORKLOAD-RESULT.ko.md).
자체 Mapper4 BG4프레임을 causal LRU로 측정했다.4KiB캐시는매프레임4096B,8KiB캐시는4096/4096/0/0B.
전체240줄 소프트웨어 복원은 일치하지만 즉시공급 모델이며 실제전송기한 검증은 아니다.
다음은 actual trace→compact packet→SNES replay의deadline/240줄accounting과 더 넓은자체표본이다.
관측union을 미래preload선택에 쓰지 않는다. 필요한FIFO/cache는 실제서비스모델로 정한다.

2026-10-05 R2 실행 갱신020: [실제trace→packet→SNES재생](../../analysis/TRACE-REPLAY-RESULT.ko.md).
자체BG4프레임의오프라인ROM공급패킷을실제SNES에서재생했다. PPU DMA1,928B/frame,
소비자최대18,046clocks/관측최소margin11,852. 두viewport로240줄화소를검증하나동시출력은239줄이다.
CHR전체16KiB초기적재와완성packetROM공급조건이며live producer/CDC/queue기한검증은아니다.
다음은더넓은자체Mapper4부하·표현거부조건,이어서생산완료/전달/속도동기화연결이다.

2026-10-05 R2 실행 갱신021: [자체 Mapper4 표본 확장](../../analysis/VIDEO-WORKLOADS-RESULT.ko.md).
NES Mesen5조건20프레임에서fine-X/sprite/분할bank/큰CHR의현재표현한계를관측했다.
새오프라인승인검사는기준4프레임승인·미지원16프레임거부;상태/전체fetch/참조화면을요구한다.
020정적BG소비자실측은유지하되새장면으로확대하지않는다.
다음구현은fine-X packet/map과SNES재생이다. 이후patch/residency비용을정하고producer기한을연결한다.
표본확장검사만계속늘리지않으며제품표현의확장을실행한다.

2026-10-05 R2 구현 갱신022: [fine-X packet/SNES재생](../../analysis/FINE-SCROLL-RESULT.ko.md).
33번째tile열과HOFS commit을추가해fine-X0/1실제SNES화소비교를통과했다.
packet2,008B/PPU DMA1,988B,소비자최대19,618clocks/minmargin10,282.
정상재생3조건·오류주입3조건을실행했고전체240줄은두독립239줄관측의union으로검증했다.
다음은sprite표본표현/재생,이후bank patch·residency비용과live producer/queue/CDC연결이다.
일반scroll전체·동시240줄·실시간producer기한검증으로확대해석하지않는다.

2026-10-05 R2 구현 갱신023: [단일sprite nativeSNES재생](../../analysis/SPRITE-REPLAY-RESULT.ko.md).
actualOAM/CHR를변환해front8×8sprite1개와BG합성/별도fine-X1회귀를통과했다.
packet2,052B가2KiB를4B넘어ROMstride4KiB,PPU DMA2,032B,최대21,470clocks/minmargin8,444.
일반OAM/priority/overflow/8×16지원이나실시간producer기한으로확대하지않는다.
다음구현은in-cellbank변경patch,이후residency/packet경계와queue/CDC/018통합이다.

2026-10-05 R2 구현 갱신024: [cell 안 CHR bank 보정](../../analysis/BANK-PATCH-RESULT.ko.md).
실제 plane 읽기로20개 타일/320B를 보정해 split 두 viewport와 별도 fine-X1 SNES 재생을 통과했다.
packet2328B/PPU DMA2308B, 최대22788clocks/minmargin7130. 예약 슬롯 충돌/용량 초과를 거부한다.
023sprite와의 결합, live producer와 동시240출력은 미완료다.
현재 다음은021 banks32의 큰CHR residency/packet 저장 경계, 이후 producer/queue/CDC/pacing과018통합이다.
앞선 갱신 단락의 다음 작업은 역사이며 이 최신 순서를 따른다.

2026-10-05 R2 구현 갱신025: [CHR32KiB 상주와 packet 저장 경계](../../analysis/CHR-RESIDENCY-RESULT.ko.md).
전체 불변32KiB startup/프레임별16KiB window 전환으로 banks32 SNES 재생을 통과했다.
packet2008B/DMA1988B, 최대19732clocks/minmargin10166. VRAM40KiB 사용,023OBJ 재배치 필요.
기존 실제packet 최대2328B를 수용하는 데이터2slot은1KiB단위6KiB 또는2의거듭제곱8KiB다.
이는 산술 저장 하한이며 FIFO 깊이/합성 채택은 아니다. joint sprite/patch/큰ROM/실시간 생산은 미검증.
현재 다음은 producer 완료/전달 지연과queue/pacing, 이후memory/CDC와018 자원 통합이다.
위 이전 갱신 단락의 다음 작업은 역사이며 이 최신 순서를 따른다.

2026-10-05 R2 분석 갱신026: [생산·전달·queue/pacing 모델](../../analysis/PACKET-PACING-RESULT.ko.md).
실제022..025 시간에 가정 encode/link/CDC를 연결해 독립tick oracle300+경계13을 통과했다.
split의 aligned 생산·전달 예산7588ticks,2ticks/B 가정 통과. 지연1/2slots는263위상 표본 통과.
±100ppm은frame9350/10053에overflow/deadline: 실제clock/enable 관계 확인과동기화가 필요하다.
새 live pipeline이나에뮬레이터 실행이 아니다. 실제SNES025유지. scratch/metadata/CDC/속도실측 미포함.
현재 다음은 보드clock/enable 확인 및 소유권/ready-gated 인터페이스, joint renderer/018통합이다.
앞선 다음 작업은 역사이며 이 최신 순서를 따른다.

2026-10-05 R2 구현 갱신027: [소유권 RTL/클록 경로](../../analysis/PACKET-QUEUE-RESULT.ko.md).
원본 singleclk3KiB×2slot을Questa실행해14case/10460readbytes/68commit을검증했다.
미완성publish/읽기,조기반환,잘못된epoch/seq/length,reset후stale를차단한다.
보드PLL은CLKIN기반/SNESphi2비동기이며NES시험clock은합성이다. 공통clock/026drift해결근거없음.
아직CDC/SNESbus/PPUDMA미연결;실제SNES025유지. 다음은CDC와ready-gated frontend/지연검증이다.
위 이전 다음 작업은 역사이며 이 최신 순서를 따른다.

2026-10-05 R2 구현 갱신028: [요청·응답 CDC](../../analysis/PACKET-CDC-RESULT.ko.md).
027queue와held request/response bridge를연결해3개독립clock/phase각13case,합19215readB를검증했다.
공통reset/클록정지/응답backpressure/원본packet무결성통과. 독립reset/물리MTBF·STA미검증.
실제SNESbus/MMIO/고정read기한미연결이다. 다음은host명령/상태와read staging/prefetch및실제ready/DMA연결.
기존clock전략·joint renderer·018통합관문은유지한다. 이전다음작업은역사이며이최신순서를따른다.

2026-10-05 R2 구현 갱신029: [호스트 준비 버퍼와 실기 준비](../../analysis/HOST-STAGE-RESULT.ko.md).
3KiB 전체 패킷 prefetch와 명령/상태/순차 읽기를028에 연결해 실제 Questa3조건×10항목,28,431B exact 통과.
실제 SNES bus decoder/IO deadline/fit은 미완료다. H0 자체 SNES ROM3종 실기 묶음은 준비됐고 실기 결과 대기.
사용자 지시에 따라 H0 화면 경로를 먼저 시험하고 H1 자체 producer→실제 bus→PPU DMA를 우선 연결한다.
H1 동일 후보 fit/STA/IO/CDC·로더·복귀가 준비되면 전체SMB3/DMC 완료를 기다리지 않고 실기로 간다.
제품 수준 R1..R5와240줄/clock/메모리/HDL 관문은 유지한다. 위 과거 다음 작업보다 이 순서가 우선한다.

## 목표와 변경하지 않는 조건

- Rev.D / STM32 / EP4CE15F17C8 / NTSC, 지정 일본판 SMB3의 Mapper4/MMC3 정상 플레이.
- 지정 ROM SHA256: DBB1CB5E18B091CA9101B1C2F5A5D6BDBEAA4A30AE1A504251310F6765CABB49.
- GBC C44 / sd2snesHST0.9.0 및 공통 MCU/FPGA를 보존한다. NES는 별도 FPGA 이미지다.
- 정상 속도·색·source frame을 희생해 통과하지 않는다. 240→239/224 crop은 승인되지 않았다.
- 원본 ROM은 변경/배포하지 않는다. 지정 로컬 표본의 읽기·관측과 배포 산출물을 분리한다.
- 전 매퍼/PAL/FDS/확장 음원/저장 UI는 첫 정상 플레이 목표 밖이다. 기본 menu/reset/입력/음향은 포함한다.

## 현재 진척: 무엇이 확보됐는가

| 관문 | 근거 | 현재 판정 |
| --- | --- | --- |
| 재현 환경 | 기존 FLOAT 경로, 실제 RTL 실행, 실패 증거·해시 보존 | 사용 가능. 새 유료 라이선스 문제 없음 |
| 코어 기능 기반 | NROM/Mapper4 자체 진단,009의4프레임245,760화소와 fetch 비교 | 제한된 기능 검증 확보. 게임 호환성 전체 아님 |
| CPU/인터럽트/DMA | 분기 bus·IRQ sampling·RDY NMI 수정,015~017 DMA 검증 | 유효한 기반. DMC refill timing은 미해결 |
| SNES 표시 가능성 |002~004 합성128프레임 전송, CHR cache/소유권/오류 검출 | 부분 증명. 239줄·미래 CHR 사전 지식·ROM 공급원 한정 |
| 자원·실시간 메모리 |018 최신core+MMC3+RAM12KiB,12,281LE/881LAB/12M9K | 기본 구성 실측. 외부IO·controller·영상·CDC 비용 미포함 |
| 실제 NES→SNES 연결 |022 fine-X,023 sprite,024 bank 보정,025 불변32KiB 상주 SNES실측 | 결합/일반sprite·32KiB초과·live producer/queue/CDC·동시240줄 미완료 |
| SMB3/전체 fit·STA/실기 | 지정 게임 종단 실행/보드 검증 근거 없음 | 미완료 |

근거: [P1](../../analysis/P1-RESULT.ko.md), [STREAM](../../analysis/STREAM-RESULT.ko.md),
[RESIDENT](../../analysis/RESIDENT-RESULT.ko.md), [MMC3](../../analysis/MMC3-INTEGRATED-RESULT.ko.md),
[RDY](../../analysis/RDY-RESULT.ko.md), [DMC/OAM](../../analysis/DMC-OAM-RESULT.ko.md).
이번 검토에서는 최신017 manifest124개 해시 및 최소 fit 원시 summary/result를 확인했다.
모든 과거 회귀를 재실행한 것은 아니며, 이전 GBC152hash 검사 등은 마지막 실행 기록이다.

## 계획에서 벗어난 점과 의미

004에서 남긴 질문은 “미리 알 수 없는 CHR 변경을 실제 fetch 정보로 처리할 수 있는가”였다.
005~009의 실행 환경·fetch·Mapper4 통합은 그 질문을 풀기 위한 필요한 준비였다.
010~017에서는 분기·인터럽트·DMA 검사가 연속적으로 확장됐다. 실제 버그를 고쳤으므로 헛수고는 아니다.
그러나 수집한 fetch를 전송 예산에 연결하는 작업, 최신 전체 자원 판정, 최소 수직 통합이 뒤따르지 않았다.
따라서 추가 세부 정확도 검사가 자동으로 다음 최우선 작업이 되는 진행 방식은 수정한다.

README의 본문은015, 상단은017이고 역사 인계마다 “최신/다음”이 반복되어 있었다.
현재 문서는 한 상태만 보여 주고, HANDOFF 아래의 이전 지시는 역사 기록으로 명시한다.

## 먼저 줄여야 할 위험

1. **영상 전송 성립성.** 004는 전환8프레임 전부터 미래 CHR를 적재한다. 일반 게임에서 가능한지 미입증이다.
   합성 working set4,096B가 모두 새 타일이면 해당 표현의 DMA만32,768clocks로239줄의30,008raw blank clocks를 넘었다.
   이 사실은 현재 단순 전송의 실패 근거이지, 모든 캐시/renderer 방식의 불가능 증명은 아니다.
2. **FPGA 자원.**018 최신core+MMC3+RAM12KiB는12,281LE/881LAB/12M9K다. 산술 잔여3,127LE, 목표13,000LE까지719LE다.
   LAB91%와 미포함controller/영상/CDC 비용 때문에 통합 가능성을 보장하지 못한다. R2요구량을 실제 구성에 더해 측정한다.
3. **물리 메모리/시간 경계.** ideal memory와 ROM 공급원은 PSRAM/SRAM 지연·버스 turnaround·MCU 경쟁·CDC를 검증하지 않는다.
4. **표시 높이·프레임 동기.** 239줄 실험은 원본 마지막256화소를 표시하지 않는다. NES/SNES pacing·queue drift도 미검증이다.
5. **정확도와 반입 조건.** DMC byte1 enable+123/+275cycle 차이, 절대 IRQ4-dot 위상 기원, 개별 HDL4개 반입 hold가 남았다.
   Questa 사용 권한 문제와 upstream 소스 반입 검토는 다른 항목이다. 기존 hold를 임의 해제하지 않는다.

## 수정한 실행 순서와 완료 조건

### R1 — 최신 자원과 메모리 예산부터 재측정

초기 핵심 구성 실측은018에서 완료했다. 다음 확대 측정에서도 최신014 수정 포함 CPU/PPU/APU+Mapper4 의존 목록을 고정하고
이전 NROM fit과 조건 차이를 표로 만든다. CPU RAM/CIRAM/PRG RAM/영상 packet/cache/FIFO의 배치·크기·포트를
정하고, 구현된 부분은 실제 합성한다. 아직 없는 부분은 분리된 범위 추정과 unknown으로 남긴다.

완료물: 고정 소스/도구/QSF/SDC, LE/LAB/M9K/PLL, clock/미제약 경로, 메모리별 포트와 worst service 계약,
포함/제외 블록 표, 통합에 남은 여유의 근거. 출력이 관측되지 않아 최적화로 제거된 로직을 자원 절약으로 세지 않는다.
초기 예산 합성은 full board fit/STA 합격이 아니다. 구조적 초과면 mapper 축소·중복 제거·메모리 배치를 먼저 재설계한다.

### R2 — 실제 fetch 부하를 영상 경로에 연결

기존009 기록으로 집계/재생 도구를 먼저 검증하고, 예고 없는 bank 전환·BG/OBJ 변화·split이 있는 자체 Mapper4를 추가한다.
기존에 지정한 SMB3 로컬 ROM은 identity를 확인한 뒤 Mesen 읽기 전용 관측에 사용한다. 타이틀 화면만으로 대표하지 않고
장면 전환·스크롤·sprite 혼잡·bank 전환 구간을 재현 가능한 입력 순서와 함께 표본화한다.
경로/입력 표본이 없으면 그 필요한 정보만 확인하며 합성 진단은 계속한다. 원본 ROM/세이브를 변경·배포하지 않는다.

수집물: 시간별 physical CHR key/generation/role, 실제 필요한 BG/OBJ 타일, palette/OAM/map/patch 변화,
최대 miss burst와 byte 수, 선행 정보가 실제로 알려진 시점, producer→display age·queue peak·누적 backlog.
미래 trace를 들여다보는 최적 캐시는 하한 비교용으로만 쓰고 인과적인 후보와 구분한다.

실제 기록 → compact packet/타일 배치 → 기존 SNES 호스트의 오프라인 재생을 잇는다.
256×240 원본 비교와239줄 실험의 누락을 별도로 보고하며, 실제 DMA·CPU 설정·HDMA 비용을 함께 잰다.
평균이나 cache hit율만으로 통과하지 않는다. 모든 관측 frame의 deadline, burst, 보존 규칙과 표본 한계를 보고한다.
이 재생은 실시간 FPGA 공급 성공이 아니다. 초과하면 causal residency/타일 단위 갱신/포맷·배치 변경을 비교한다.

### R3 — 정확도 차이는 범위를 제한해 닫기

DMC 단독의 동일 cold-reset/register-write fixture로 enable→첫 fetch→다음 refill을 나눈다.
공통 clock 기준과 timer/bit counter/buffer empty를 먼저 비교하고, 확인된 차이만 수정한다.
Mesen과 다르다는 사실만으로 RTL 결함이라고 단정하지 않는다. 절대 IRQ offset도 같은 관측 원칙을 쓴다.

한 번의 완결된 조사 묶음(원시 양쪽 trace+차이 분류+수정 또는 열린 이슈)을 끝낸 후 R1/R2의 진행을 재평가한다.
새 edge case를 끝없이 붙이지 않는다. 원인이 미확정이면 영향과 재현을 기록하고 영상·자원 작업은 진행할 수 있다.
단, 정확도 차이를 숨긴 채 SMB3 정상 플레이나 최종 호환성 gate를 통과시키지는 않는다.
코어 수정 시 해당 검증+관련 DMA/IRQ+Mapper4 영상 회귀를 실행한다. unchanged core의 모든 역사 시험 반복은 하지 않는다.

### R4 — 최소 수직 통합과 표시 정책 확정

R1/R2의 타당성 근거를 얻으면 실제 생산자와 외부 메모리, immutable packet/ownership/epoch/CDC,
SNES consumer를 연결한다. 이때 delayed response, read 유지 중 주소 변화, backpressure, reset/timeout,
장기 drift를 시험한다. 정상 모드 frame 삭제·강제 blank 반복·속도 저하로 queue를 비우지 않는다.

표시 정책은 앞 단계부터 실제 장면 비교를 준비한다. 240줄 보존 대안의 공간/움직임/시간 비용과
239/224줄 선택 시 손실을 수치·영상으로 제시해 사용자가 선택할 수 있는 자료를 만든다.
승인 전 기본은 원본 보존 요구이며 crop을 구현 기본값으로 확정하지 않는다. 다른 독립 작업은 정책 결정과 함께 진행 가능하다.

완료 기준은 자체 진단의 load→RUN→화면→입력→음향→menu/reset 복귀가 실제 경로에서 이어지는 것.
MCU 명령/확장자/core ID와 cleanup 충돌을 확인한다. GBC→NES→GBC 및 GBC 시작/메뉴/저장/reset 회귀가 필요하다.
기존 0.9.0 공개 자산은 변경하지 않는다.

### R5 — 동일 통합 후보의 full fit/STA와 제한된 실기

R1의 조기 예산 판정과 구분한다. 실제 board pins/IO timing/clock/reset/CDC/모든 메모리/영상/음향을 포함하고,
의도하지 않은 미제약 경로·ignored exception을 해결하거나 정확히 분류한다. 근거 없는 false path/clock 완화 금지.
진단 ON/OFF 각각 기능·자원·timing을 확인하고 사용자용 설치 세트/해시/복귀 절차/짧은 시험 항목을 만든다.

자체 진단 실기 후 지정 SMB3의 부팅·메뉴·대표 레벨·전환·입력·음향·연속 플레이를 진행한다.
표본 통과와 전체 게임 보장을 구분한다. 실패하면 해당 경계로 돌아가 수정하며 전 매퍼/상태 저장 확장은 그 뒤다.
개별 소스 반입 hold와 필요한 고지는 vendoring/배포 전에 해소해야 한다.

## 운영 개선과 보고 기준

- 현재 상태의 기준은 README/이 계획/plan JSON 하나로 유지한다. 역사 실험 문서를 지우거나 성공 범위를 소급 확대하지 않는다.
- 현재 다음3개 산출물은 H0 실기 결과와 물리 SNES frontend, H1 자체 패턴/PPU DMA·동일 후보 fit/STA/IO 및 복귀 묶음, 이후 본 NES memory/joint renderer/clock·018 확대 자원표다.
  R3는 한정된 조사로 병행 가능한 작업선이며, 세부 APU 전 범위를 위3개 산출물의 선행 조건으로 만들지 않는다.
- 직렬 실행 가능한 단계부터 진행한다. Questa1seat는 항상 순차 사용하며 자동 subagent/추가 라이선스를 전제하지 않는다.
- 새 검증기는 원시 소규모 fixture의 시작/종료 경계·cycle 개수를 먼저 확인한다. 판정식 오류와 DUT 오류를 별도로 기록한다.
- 반복 parser/manifest/runner 개선은 새 공통 helper로 최소한만 도입한다. 과거 pinned driver를 일괄 변경하지 않는다.
- 비용은 코드 변경과 관련된 회귀에 사용한다. 문서만 바뀌면 링크/상태/해시를 검사하고 Questa를 재실행하지 않는다.
- 진척 보고는 새로 닫힌 관문, 남은 가장 큰 위험, 다음 판정을 바꿀 측정치, 실측/추정/미측정 구분으로 작성한다.
- 날짜 약속은 R1/R2에서 통합 성립성과 필요한 재설계 규모가 보인 뒤 검토한다. 현재는 완료일을 계산할 근거가 없다.

계획 변경 이력과 이전 문서는 ignored analysis/local-plan-review-20261005/baseline/에 보존했다.
[계획 검토 manifest](../../analysis/nes-plan-review-artifacts.json)는017의 증거124개 확인 및 과거 제안서 위치를 기록한다.
