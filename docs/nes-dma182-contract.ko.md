# NES182 — 화면 전송의 바이트별 CPU 대기를 DMA로 교체

## 작업 의미

181에서 SMB3 첫 레벨의 화면 정지는 해결됐지만, 60.06초 동안 표시 완료136회로 심하게 끊겼다. 이번 변경은 **60fps를 위한 실제 전송 경로 개선**이다. 디버그 관측기를 늘리거나 게임 실행 속도를 낮추는 작업이 아니다. 아직 실기 성능 개선이나60fps를 달성했다고 주장하지 않는다.

181은 같은2.625MHz SPI를 쓰면서 매 바이트마다 TXE 대기→쓰기→RXNE 대기→읽기를 CPU가 실행하고, 각 대기에서 전체 세션 소유권을 검사했다.182는 같은 패킷을 SPI1의 DMA2 stream0/RX와 stream3/TX, channel3으로 전송한다. CPU는 전송 중에도 전체 세션 검사·SPI/DMA 오류 검사를 계속 수행한다. 실제 소프트웨어 비용은 기존 로그로 분리 측정되지 않았으므로 절감률을 미리 수치화하지 않는다.

기존 GBC 부팅용 DMA 함수는 수정하거나 호출하지 않는다. NES RUN의 `nes_native165_bulk`만 바뀌며, ROM 로딩·observer·STOP의 기존8바이트 전송은 그대로다. 로딩 시간이 줄어드는 변경은 아니다. FPGA·SNES 클라이언트·수신/변환/압축1813·1815·ACK/CRC·SPI클록·SS간격은181과 같다. 새 FIT가 필요하지 않다.

## 수명과 중단 계약

- 길이1~259바이트,8비트·단일 전송·주소증가·비순환 DMA. 별도 프레임/송수신 버퍼, heap, cartridge save SRAM을 추가하지 않는다.
- 기존 GPIO/SPI/세션 소유권 검사 뒤 두 stream이 비활성인지, DMA클록이 켜져 있는지, 해당 NVIC IRQ가 활성/대기 중이지 않은지 확인한다. 다른 소유자의 stream을 강제로 빼앗지 않는다.
- 두 stream의 CR/NDTR/PAR/M0AR/M1AR/FCR을 저장한다. 수신 stream과 수신 DMA 요청을 먼저 켜고 송신 요청을 마지막에 켠다. FIFO·burst·DMA IRQ는 사용하지 않는다.
- RX/TX 완료 플래그 모두와 두 NDTR=0이 필요하다. 이후 TXE=1, BSY=0을 순서대로 확인한다. TX DMA 완료만으로 SPI가 끝났다고 판단하지 않는다.
- 전체 polling131072회 및 무진행1024회로 제한한다. 매 polling에서 기존 `nes_cf86_check094`와 DMA/SPI 오류를 확인한다. 이 숫자는 시간 측정값이 아니다.
- 오류 시 CS를 해제하고 SPI를 끈 다음 DMA요청/stream을 중단한다. EN=0을 확인한 뒤에만 저장한 레지스터와 GPIO를 복원하고 호출자에게 반환한다. 자동 재시도는 없다.
- EN이1024회 확인에도 해제되지 않는 비정상 상황에서는 CS/SPI를 해제하고 리셋·공유 오류를 설정한 채 반환하지 않는다. 아직 DMA가 접근할 수 있는 stack buffer를 해제하지 않기 위한 마지막 방어다. 이 경우 SD 로그/메뉴 복귀를 보장하지 않는다.
- 기존 CSS NMI는 SPI요청과 SPI를 끄고 영구 정지한다. exception-return이 없으므로 해당 buffer 수명이 유지된다. CSS 코드·벡터·IRQ 경로는 원본 그대로 검증했다.

**이전과 다른 점:** DMA가 전송하는 동안 CPU는 IRQ/guard를 실행할 수 있다. 바이트마다 CPU가 다음 쓰기를 허가하는 이전 스케줄과 같지는 않다. CPU가 실행되지 않아도 최대259바이트의 현재 패킷은 진행할 수 있고, 새 패킷은 시작되지 않는다. 물리 오류 검출 지연/WCET와 AHB경합은 레지스터 모델로 입증되지 않는다. 이 범위를 감춘 채 안전성·처리시간의 완전 등가를 주장하지 않는다.

## 검증 결과

- 실제 생성된 C 드라이버의 비동기 레지스터 모델: 정상/경계794경우, 실행된 guard 위치907곳의 오류,259개 바이트 위치별 DMA6종/SPI4종 오류2590경우 통과. TX완료가 RX보다 먼저 오는 경우, 진행 지연, RX/BSY정지, 다른 stream의 flags 보존, 기존 소유자/IRQ 거부, 실패 뒤 재진입 금지를 포함한다. CS 안정화 대기의 오류도 첫 DMA 요청 전에 차단한다.
- EN 해제가 지연되는 동안 주소/버퍼를 복원하지 않으며, 해제 불능이면 함수가 반환하지 않는 것을 검사했다. 모델이며 STM32 자체 시뮬레이션·실기 성능 검사는 아니다.
- 전체 ARM 링크200844B, static26564B, RUN보수상한36968B, IRQ508B, 잔여1384B. 새 정적RAM은 없다. DMA 함수의 로컬 저장은 전체 call graph에 포함했다. 실제 high-water 측정이나4KiB목표 충족은 아니다.
- 기존13개 library/platform 함수의 정규화된 명령 일치, NMI벡터/STOP·메뉴호출·noinline RUN workspace 수명 검증. 최고 필드값 로그3921/4096B.
- FPGA는181 배포 바이너리와 byte-exact. 기존 SPI RTL 시험은 이미 바이트 간 추가 대기 없는2.625MHz 파형을 사용했다. 이것을 새 RTL 실행으로 세지 않는다. 연속 DMA의 실제 보드 타이밍은 다음 실기 대상이다.
- test01/check01은 기존 sandbox DLL623 문제로 도구 실행 실패. 초기 test02/arm01/check02/release01 뒤 시작 직전 guard를 보완했고 **test03/arm02/check03/report01/release02**가 최종 선택이다. report01은 formatter 소스가 동일하여 해시 확인으로 재사용했다. 이전 디렉터리/패키지를 덮어쓰지 않는다.

## 다음 판단

182에서 같은 SMB3 첫 레벨을 플레이하고 완료ACK 수·receive/build/seal 시간·화면·음성·메뉴 복귀를181과 비교한다. 실제60fps가 아니면 그 사실을 그대로 기록한다. 새 FPS cap·의도적인 frameskip은 없다.

DMA는 CPU가 바이트를 공급하는 틈을 줄일 뿐, 필수 데이터량이나capture lease를 없애지 않는다. 기존 raw7 합성 egress 하한22.154ms만으로도16.7ms를 넘으며 실제181은약442ms/완료였다. 다음 순서는 실제 결과에 따라 (1) 유효 payload와 ACK/poll 비용, (2) 기준세대가 확인된 section/CHR 차등전송, (3) capture→전송→표시의 버퍼 수명 중첩이다. 이미 완성된1813/1815압축·rawsteady를 다시 만들지 않는다. fetch01/04 재동기화와 장면별 거부도 계속 남은 항목이다.

AV60fps→장기플레이와 오류/리셋로그→입력유지 순서를 유지한다. MMC4/5·save/load·mute/frameskip 확장 계획,181기준판·GBC164·기존세이브·완료archive를 보존한다.

근거: [ST RM0368](https://www.st.com/resource/en/reference_manual/rm0368-stm32f401xbc-and-stm32f401xde-advanced-armbased-32bit-mcusstmicroelectronics.pdf)의9.3.17(stream정지/재설정),20.3.8/20.3.9(SPI종료/DMA), [181실기 결과](nes-game181-hardware01.ko.md), [검증 색인](../analysis/dma182-verification.json).
