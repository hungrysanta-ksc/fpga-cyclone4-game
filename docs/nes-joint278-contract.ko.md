# NES278 — host 출력 실행기와 고정 phase RAM 포트

NES278: host 출력 실행기와 고정 NES A/host B phase RAM을 구현해 descriptor·바이트 RPC와 출력 24/8bit mailbox를 제거했다. 원본 payload의 CRC와 ordered ACK 이후 receipt를 연결하고, 71프레임·52개 STOP/ACK 검사를 통과했다. 일반 조건 warm 최대 18.180055ms(276 대비 -0.042090ms), 목표 부족 1.513388ms. 제한 ROM 907은 +0.167771ms로 회귀했다. 전체 Lite 조합 논리는 17,815개(276 대비 -430, 274 대비 +135)로, 장치 한도를 2,407개 초과한다. 60fps·회로 공동 게이트는 미달이며 P2는 보류한다.
PR130 / `codex/nes-wholepath-boundary-256`; 기준은 NES277 계획과 실제 NES276,
더 작은 이전 보드 NES270/274를 함께 사용한다.

## 구현 경계

- NES source/query는 기존 codec와 64비트 선행 읽기를 유지한다. phase RAM A는
  NES 클록 전용이다. FSTORE의 mask 쓰기를 다음 빈 사이클에 처리하는
  address 9 + value 8 + pending 1비트로 바꾸어 source의 B 포트 사용을 없앴다.
- phase RAM B는 host 클록 전용이다. 초기화, H2, receipt, persistent validity,
  raw CRC, 표시 view를 담당한다. 두 포트를 번갈아 클록 mux로 연결하지 않는다.
  호스트가 receipt와 persistent 비트를 갱신할 때는 네 번의 순차 RAM 접근을 쓴다.
- 출력 검사기는 source의 출력 상태·임시 register alias에서 분리했다.
  source는 input commit 이후 output 대기 상태를 유지하고 마지막 표시 ACK에서
  해제된다. source의 raw 문맥은 collector 해제 후 값이 바뀌지 않도록 기존
  admitted 값을 admission 메시지에 실어 보낸다.
- host는 원래 queue header를 한 번 해석한다. descriptor 8단어·본문 바이트의
  NES 왕복, 반환 주소·완료 응답, 출력 consumed24/receipt8 mailbox를 제거한다.
  admission84와 최종 ACK1 mailbox는 남긴다. source 전송용 mailbox도 남긴다.
- ordinary payload는 tagged·valid SNES queue read를 한 번 tap한다. CRC에 필요한
  fresh scroll/raw tail만 검사기로 보낸다. repeat 패턴은 최대 4바이트를 보존해
  논리 출력 길이만큼 CRC에 반영하며 원본 payload를 다시 읽지 않는다.
  tile token도 같은 실제 SNES 읽기에서 얻는다.
- map staging과 내부 manifest/H2는 기존 queue 읽기 포트를 이용한다. manifest는
  SNES에 재전송하지 않는다. queue의 host/SPI 쓰기 포트와 host/SNES 읽기 포트에
  제3 포트를 추가하지 않는다.

## 반드시 유지하는 의미

내용 CRC와 DMA 완료 receipt는 다른 시점이다. raw CRC는 payload 읽기 중 provisional
상태로 갱신하되 해당 granule의 receipt는 ordered ACK 이후에만 쓴다. 마지막 queue
읽기를 PPU DMA 완료로 간주하지 않는다. SNES의 일반 경로는 queue→WRAM 읽기 후
명령 실행·PPU DMA/HDMA를 수행하고 ACK하는 기존 경로다.

queue 4-credit, 정확한 read coverage, bank/generation/token, 순서 있는 ACK,
독립 metadata·receipt·H2 digest 검사, final view 12바이트 읽기와 최종 ACK,
display lease, STOP 후 bank invalidation은 유지한다. STOP은 pending mask,
host CRC, receipt 쓰기 및 최종 반환 중에도 RAM 쓰기·노출을 차단해야 한다.
한 클록이 멈춘 경우도 검증 범위에 넣는다.

source scratch와 host 출력 데이터의 RAM 주소가 겹치므로 단순한 dual-clock RAM
선언만으로 안전하다고 판단하지 않는다. grant는 source/query/transport/mask drain
후에만 허용하고, output 단계의 source A 쓰기는 금지한다. host B의 출력 쓰기는
유효 grant와 output lease 동안에만 허용한다. 초기 전체 RAM clear는 별도다.

## 측정 범위와 채택 조건

동일한 ARM274 serializer/refill·IRQ 코드, 71개 계획, source 데이터, 일반 65816
실행에서 얻은 544개 명령 trace를 사용한다. 매 실행에서 SPI polling, 4-credit,
실제 tile ROM reader/cache/arbiter와 모델링된 SNES map/tile 서비스를 다시 연결한다.
제한된 ROM window의 905~907도 따로 측정한다.

이는 실제 RTL과 ARM 코드 및 CPU bus trace를 연결한 **진단 일정**이다. full RUN,
N5/planner 전체, 실제 NVIC/MCU cycle, live 전체 65816, active VBlank, 물리 보드,
전체 FIT/STA가 입증된 것은 아니다. 따라서 `full_path_ms`는 null로 유지한다.
71개 실제 입력의 raw count는 모두 2다. 새 RTL의 raw2→0 양 bank 전환은 이번
실행 범위에 없으며, NES250의 이전 전환 검증을 새 RTL의 실행 증거로 계산하지 않는다.

전체 보드 Lite MAP을 동일 경계로 비교한다. 부모 entity와 자식 entity를 중복
합산하지 않고 own count를 사용한다. RAM, 새 host CRC, admission 문맥 증가,
tap 상태·패턴 보존, serial receipt와 기존 source/plan/tile/mapper를 모두 포함한다.
조합 논리 15,408개 이하도 배치·타이밍 여유를 보장하지 않는다.

## 실제 결과

선택: test07, window01, guards03, guards04, board01, analysis01.
동일한 ARM E1 packet 1,231개와 source 83,240B, map 2,069범위/13,406B,
map/tile DMA 26,350B를 확인했다. 각 프레임의 metadata 8,570B, receipt 754B,
CRC 64B를 독립 기대값과 비교했고 일반 65816 trace 544명령을 재실행했다.
ARM 실행 section은 274와 같으며 nonloaded `.strtab`의 임시 object 이름 차이만 허용했다.
ARM/refill/IRQ에서 관측한 stack 248B는 full RUN stack 상한이 아니다.

SNES가 읽은 원본 body 17,277B를 한 번씩 tap했고, source mask 40,754회(574×71)를
다음 빈 사이클에 썼다. provisional raw CRC 32회와 ordered ACK 793회를 따로 계수했다.
CRC 시점에 receipt가 미리 설정되지 않고, nonmap receipt가 ordered ACK 이전에
쓰이지 않는 검사도 통과했다. 신규 테스트에서 source/query/transport/mask drain
이전 grant, output 중 source A write, grant 없는 host B write, ordinary body 재읽기를
금지했다.

|조건|276 진단 일정|278 진단 일정|차이|
|---|---:|---:|---:|
|일반905|63.657918ms|63.489965ms|-0.167953ms|
|일반906|51.899559ms|51.566199ms|-0.333360ms|
|일반907|11.571543ms|11.529453ms|-0.042090ms|
|일반954|18.222145ms|18.180055ms|-0.042090ms|
|제한 ROM905|90.393415ms|90.225463ms|-0.167953ms|
|제한 ROM906|114.311219ms|114.266947ms|-0.044272ms|
|제한 ROM907|18.204691ms|18.372461ms|+0.167771ms|

일반 조건의 warm 69개 중 6개가 16.666667ms를 넘는다. 최대 부족은
1.513388ms이며, full RUN/active VBlank 등 미측정 비용은 별도다.
954는 E2 109회, 전체 SPI 2,739B다.
전체 71프레임은 E2 6,989회, SPI 165,131B다.
954의 ACK 이후 parser는 0.275519→
0.027667ms이며, ordinary/tile 부분은
0.041033→0.002084ms다.
이 부분 감소량을 전체 시간에서 차감하지 않는다. E2는
110→109회로 변했고,
wire·ARM event명령·transaction 비용 차이는
-0.042107143ms,
그 밖의 일정 차이는+0.000016739ms다.
기존 SPI E1 payload는 동일하며 전송량 절감은 polling 등 제어 거래 변화에서 생긴다.

유지한 실제 일반 65816 trace에서 954의 OAM repeat4 명령은
28,952 master clock,
payload 읽기 뒤 DMA 설정 전 구간은
23,224 clock이다.
이번 FPGA 교체가 이 SNES 실행 비용을 제거하지는 않는다.
71개 repeat4 OAM 패턴은 모두 00f00000이며, ROM template DMA 같은 실행 방식의
변경은 별도 후보일 뿐 이번 시간 절감이나 회로 회수량에 반영하지 않았다.

제한 ROM 3프레임의 절대 종료는 276의 265.001456ms에서
278의 264.957002ms로 0.044454ms 빨라졌다. 그러나 warm 프레임 907은
0.167771ms 느려졌다. 따라서 시간 개선은 모든 경쟁 조건에서 유지되지 않는다.

|항목|274|276|278|276 대비|
|---|---:|---:|---:|---:|
|LE|22487|22986|22730|-256|
|조합 논리|17680|18245|17815|-430|
|FF|8892|8832|9077|+245|
|RAM bits|303712|303712|303712|+0|

각 entity의 own count는 source 1,399 + validator 1,063 + host 2,486 + queue 174
= 조합 논리 5,122개다. 276의 같은 영역과 제거된 두 mailbox를 포함한 5,561개보다
439개 작다. 나머지 계층의 증가 9개를 포함해 전체 430개가 줄었다.
FF는 245개 늘고 RAM은 같다. 전체 조합 논리는 274의 17,680개보다는 135개 크다.
나머지 12,693개를 고정하면 이 영역의 예산은 2,715개로, 아직 2,407개를 더 줄여야
하며 배치 여유도 별도로 필요하다.

phase RAM은1024×8 true dual-port M9K로 추론됐다. source/host/validator/tap
FSM도 추출됐다. dual-clock read-during-write 경고는 보존한다. host 출력 중
source A의 읽기 결과는 사용하지 않으며, 실제 사용되는 데이터의 포트 소유권은
grant/phase 검사로 제한한다. 이 검사는 full CDC/STA의 대체가 아니다.
board와 simulation의 기존 wrapper 차이만 유지했으며 양쪽 모두 동일한
output-phase admission 조건을 추가했음을 exact diff로 확인했다.
기존 MAP 실행기의 `input_hashes`는 변경 전 270 보드 입력의 해시다.
최종 감사에서는 이를 원본과 대조하고, QSF의 validator 추가 한 줄과 변경 RTL
5개만 달라졌는지 확인한다. 새 validator를 포함한 실제 합성 RTL은 analysis01의
simulation/board 비교 및 최종 파일 해시로 별도 연결했다.

기존38개 의미·ACK 오류, 분할 패킷6개, 새 host 실행 상태의STOP5개,
NES/host 각각의 정지된 클록 및 source mask pending STOP3개로52개를 검증했다.
각 오류에서 status/invalidation 유지, stale ACK 차단, 최종 완료 금지,
RAM 전체 동결을 확인했다. 기존 ARM41/SPI171 검사는 동일 source/ELF·RTL hash로
연결해 재사용했으며 새로 실행한52개와 구분한다.
guard 생성기의 monitor 교체 범위를 좁힌 뒤 조기·누락·중복 ACK 관련12개를
guards04에서 추가 실행했다. 이 실행은 receipt-before-ACK와 provisional CRC
계수 검사를 보존한다. guards03의52개와 별개의12종 신규 오류로 중복 집계하지 않는다.

실패 보존: test01 RTL 문법, test02/03 collector 해제 후raw 문맥, test04 이전
mailbox 대기 조건으로 인한 진행 정지(수동 종료), test05 진단문법, guards01
이전core hierarchy 참조, guards02 이전NES 클록의context 계수. test06은3프레임
중간PASS이며 최종71프레임에는 추가 read/ACK/grant 계수·검사를 사용했다.
라이선스 오류로 분류하지 않는다.

## 보존 및 다음 판단

실패한 생성·검증 기록과 통과 기록은 서로 다른 경로에 보존한다.
production227/GBC164/saveSRAM을 변경하지 않는다. 새 경계가 실제 시간과 전체
회로 한도를 함께 충족하지 못하면 P2나 FIT seed 탐색으로 넘어가지 않는다.
잔여 비용은 제거된 왕복의 이득, 이동한 제어의 비용, polling·ROM 대기로 나누어
보고하고 그 근거로 다음 교체 범위를 결정한다.

다음 작업은 278의 검증된 read/ACK/포트 소유권을 기준으로, 같은 heavy 프레임의
source 전송·ARM 계획/tile ROM·polling·SNES 실행 비용을 분해하는 것이다.
source+validator+host+queue의 5,122개를 허용 예산 2,715개와 비교하면서,
남은 시간과 회로 부족을 함께 줄일 수 있는 전송·역할 변경을 검토한다.
독립 CRC/coverage, ordered ACK, STOP, 최종 표시 검사는 유지한다.
클록·RAM 포트·CRC 비용을 생략하거나 parser 부분 절감을 전체 시간에서 다시 빼지 않는다.
두 게이트를 통과하기 전에는 FIT seed 탐색이나 물리 60fps 검증으로 넘어가지 않는다.
