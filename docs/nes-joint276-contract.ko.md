# NES276 — 원본 descriptor와 source·receipt 통합 core

별도 참조 프로그램과 inline prefix를 제거했다. ARM은274와 동일한 원본 packet을
보내고, SNES가 소비한 descriptor가 FPGA receipt·CRC·manifest 처리의 입력이 된다.
host의 일반 명령 해석기를 제거하고 기존 source/query/receipt core의 상태 기계에
합쳤다. queue·typed map staging·source transport·CDC·최종 표시 소유권은 별도의
필수 경계로 남고 전체 비용에 포함한다. 보드 전체가 한 FSM이라는 의미는 아니다.

## 실제 교체와 공유 수명

일반 명령은 원본 packet의 정확한 SNES read coverage와 ordered ACK 이후,
tile은 staging read와 token consume 이후 core에 전달한다. 내부 manifest는 이전과
같이 SNES 재읽기·ACK 없이 처리한다. queue head와 credit은 core의 완료 응답까지
유지한다. typed map은 기존 범위별 DMA·receipt·token 경로를 사용한다.

기존24bit forward/8bit return CDC를 유지한다. 원본 descriptor·소비 token 문맥
8워드를 전송한 뒤 core가 원본 held payload에서 필요한 바이트를 요청한다.
ARM wire에 새 프로그램이나 새 descriptor를 추가하지 않았다. payload read 왕복은
실제 일정에 포함한다. packet RAM·phase RAM·mailbox를 추가하지 않았다.
비교 입력은274의 bounded packet split을 유지한다. 참조 프로그램 공간을 위해 더
잘게 나눴던 일부 packet까지 다시 합친 최적 전송 형식이라는 주장은 하지 않는다.
현재 whole 회로 게이트가 실패했으므로 입력 분할만 바꾸는 추가 실험을 이어가지 않는다.

source/query의 선행 읽기는 유지한다. 입력 commit 후 query 요청이 남아 있지 않을 때
기존 레지스터를 출력 단계에 재사용한다. 상태·바이트·진행 위치·CRC·receipt 처리의
소유자는 기존 core의 같은 always/state 블록이다.272의 별도 parser FSM은 만들지 않는다.

|입력 단계 레지스터|출력 단계 역할|
|---|---|
|q_held, old1/old2/new1/new2, edge0/edge1, q_maps/q_raw_seen|원본 descriptor·token·길이·H2 문맥120bit|
|raw_at/raw_limit|descriptor 소비 위치·끝|
|new_byte/mask_acc|원본 payload 바이트·요청 주소|
|raw_count/shift_left|RLE 남은 길이·zero 여부|
|spans/q_mode|manifest 위치·단계|
|row_i/diff_count|metadata·token 읽기 위치|
|block_id, q_objects/q_exceptions/q_palettes|같은 core의 실행 종류·인수|
|record_length, left_row/q_normal/right_row|복귀 위치·소유권·hash 진행 방식|

receipt의 cursor/expanded와 display의 build_i는 출력 실행 중에도 살아 있으므로
descriptor 위치와 겹치지 않는다. 새 프레임의 source admission에서 source 필드를
다시 초기화한다. source 상태와 descriptor 상태 사이에 RAM write·query 소유권을
검사했다. STOP 이후에는 기존 first-fault/lease/RAM freeze 규칙을 유지한다.

원본 descriptor의 주소·길이에서 연속 receipt granule을 직접 계산하며 한 번에
최대16개를 처리한다. section 경계·길이·중복 bit·누락 manifest·hash/certificate
검사는 기존 core에서 수행한다. source/receipt CRC16 조합 경로도 공유한다.
SNES가 소비한 descriptor와 따로 전송된 참조 프로그램을 대조하는275 제어는 없다.
queue의 실제 transaction 길이/CRC zero residue 검사는275의 제거 결과를 유지한다.

## 기능과 전체 일정

71프레임/1231패킷의 actual SPI E1 payload가274 ARM 출력과 byte-identical하다.
모든 packet은256B 이하이고 source83240B/map124묶음2069범위13406B/map·tile DMA26350B를 유지한다.
프레임마다 metadata8570B/receipt754B/CRC64B를 대조했다. 기존 실제65816 일반 명령
544개의 read byte·ACK와 논리 출력128041B(재사용 포함),PPU DMA39648B/223회,
bank zero DMA2200B/2회도 유지한다.
71프레임 모두 source query 횟수·prepare/transfer/overlap cycle이274와 같고,
source 전체 cycle 차이는 클록 위상에 따른-1~+1cycle이다. 입력 처리 시간 절감은 없다.

|조건|274|275|276|274 대비|
|---|---:|---:|---:|---:|
|frame905|63.615873ms|64.804541ms|63.657918ms|+0.042045ms|
|frame906|51.692289ms|53.107999ms|51.899559ms|+0.207270ms|
|frame954|18.222145ms|19.187997ms|18.222145ms|+0.000000ms|
|제한 ROM905|90.351416ms|91.540038ms|90.393415ms|+0.041999ms|
|제한 ROM906|114.269811ms|114.161994ms|114.311219ms|+0.041409ms|
|제한 ROM907|18.246508ms|17.522699ms|18.204691ms|-0.041818ms|

정상warm 초과는6/69개, 최대 진단 부족은1.555478ms다.
전체 출력 SPI는274의165401B,275의176770B에서276의166159B다.
별도 참조 wire13385B를 없앴으나 polling·IRQ 일정이 달라지므로 그 바이트만큼을
시간에서 단순 차감하지 않았다. E0 249회/E2 7101회를 실제 실행했다.
274 대비E2가82회, E8이1회 늘었다.
추가82×9B+1×20B가 전체SPI 증가758B와 정확히 일치한다.
954는E1 1239B, E2 110회,전체SPI 2748B,
ARM·IRQ event명령200940개다.
274 대비 wire·명령·transaction 비용 차이+0.000036ms와
남은 schedule 차이-0.000036ms를 별도로 기록했다.

제한 ROM3프레임의 절대 종료는274 264.959866ms,
275 265.316862ms,276 265.001456ms다.
전체 종료 차이는274 대비+0.041590ms,275 대비-0.315406ms다.
907만의 증감을 독립적인 처리량 변화로 계산하지 않는다.

full 실험 ARM의 실행 section·주소·symbol table은274와 byte-identical하다(text4206/BSS612B).
ELF 전체 hash는 비실행.strtab의 GCC 임시 object 파일명만 달라서 다르다.
관측 stack은248B,IRQ 본문은203회 실행했다.
275의text6498/BSS684/stack336B에서 돌아왔지만 full RUN stack 상한은 아니다.

시간은 실제 ARM serializer/refill·IRQ 본문을 CPI1/84MHz로 진행한 동일 조건의
직렬 진단이다. 입력은 기록된 plan이며 ARM planner/full RUN/NVIC 전체를 실행하지 않는다.
실제 tile ROM arbiter에 모의 core 경쟁 요청을 넣는다. ARM E0/E2 polling은 실제 실행
횟수다. 일반65816은274의 forced-blank bus trace를 새 경로에서 바이트·ACK까지 대조했다.
새 CPU 캡처는 없고, map/tile/final display 및 SNES ready 대기는 기존 버스 모델이다.
전체65816 polling/active VBlank/whole pixel/실기 deadline 상한은 아니다.
full_path_ms는 null이며 실기60fps로 해석하지 않는다.

## 동일 whole-board Quartus Lite 비용

|항목|274|275|276|274 대비|
|---|---:|---:|---:|---:|
|LE|22487|22898|22986|+499|
|조합 논리|17680|18130|18245|+565|
|FF|8892|8877|8832|-60|
|RAM bits|303712|303712|303712|+0|

15408comb 한도 대비 부족은2837개다. core own2448→3818(+1370),
host output own2206→1536(-670),queue282→173(-109)로 직접 교체 계층 합계는+591comb다.
나머지 계층 합성 차이-26을 포함해 whole+565comb다. FF는60개 감소했고 RAM은같다.
core/host FSM이 정상 추출됐으며 통합 core의 상태는42→56개다.
board wrapper는270부터 외부 native capture lease를 연결하며 simulation wrapper의
내부 lease 인스턴스와 다르다. module 이름·tile_closed 출력·lease 연결 차이가
이전·현재 버전에서 정확히 같음을 diff로 확인했다. core·joint core·queue는
byte-identical하다. 이 비교는 동일 whole 합성 경계이고 새 보드 전체 실행 증거는 아니다.
FIT/STA는 실행하지 않았다.
기존490LE/40LAB 배치 실패를 해결했다고 주장하지 않는다.

원본 descriptor를 사용하는 기능 통합은 완료했지만, 레지스터 공유와 FSM 통합만으로
조합 논리가 줄어들지는 않았다. core의 문맥 선택·검사·복귀 경로까지 포함하면
host에서 제거한 제어보다 비용이 커졌다. FSM 추출 실패나 추가 RAM 때문은 아니다.
inclusive parent와 child를 합하지 않았으며, 변경하지 않은 계층의 합성 차이를
구조적 절감으로 계산하지 않는다.

## STOP·최종 ACK 및 증거 범위

새 통합 RTL에서 기존38개, 분할 descriptor6개, 통합 core STOP5개로 총49개 guard를 실행했다.
전송 CRC를 재계산한 주소·길이·section·manifest/token/identity 변형도 검사했다.
검사된49개 번호는 공개 JSON에 기록한다.

ARM serializer와 실행 section은274와 같아 기존 ARM41개 오류 및credit wrap65530→54
증거를 해당 source·ELF hash에 연결해 재사용했다. SPI endpoint의6개 RTL 파일도275와
byte-identical하므로 기존171개 길이·CRC·credit 검사를 파일 hash로 연결해 재사용했다.
이 둘을276에서 새로 실행한 검사 수로 계산하지 않는다.

기존 source/core와 host의 원본 semantic guard를 새 경로에 다시 실행한다.
새 STOP은 descriptor metadata load, payload read 대기, receipt RAM update,
CRC byte update, 완료 응답 경계에서 발생시킨다. 중간 취소 뒤 lease·최종 ACK·stale
ordered ACK를 차단하고 공유RAM1024B가256cycle 동안 변하지 않는지 확인한다.
이 guard의 SNES consumer는 모델이며 새 CPU/RTL STOP 동시실행 증거는 아니다.

초기 test01의 forward declaration compile 오류와 수정 후 test02의3프레임 PASS를
보존한다. 성공 자료만 남기거나 이전 실패를 덮어쓰지 않는다.

## 판단과 다음 경계

NES276: 별도 참조 전송을 제거하고 원본 descriptor 해석을 source/query/receipt core의 한 FSM에 통합했다. 71프레임/1231패킷/2069map 범위/544일반65816 trace와49 STOP·semantic guard PASS. warm 최대18.222145ms(274 대비+0.000000,275 대비-0.965852), 목표 부족1.555478ms. whole Lite18245comb(274 대비+565,275 대비+115), 부족2837개. 기능 통합은 검증했지만 시간·회로 공동 최적화 후보로 채택하지 않는다.

추가 opcode·FSM 인코딩·개별 FF·FIT seed 반복으로 이 후보를 다듬지 않는다.
다음에는 역할/전송 경계를 재검토한다. 유지하는 독립 검사와 삭제할 실제 제어를
먼저 분리하고, 원본 데이터의 한 번 소비로 DMA·receipt·CRC를 완료할 수 있는
소유권 및 RAM 포트 구조를 전체 비용으로 비교한다. host/SNES 읽기와 NES 검증의
클록·RAM 포트를 무료로 가정하거나 기존 CDC를 숫자에서 빼지 않는다.
현재 후보를 기준으로 새 구조가 시간·회로 게이트를 함께 만족할 근거가 있어야
추가 구현·FIT/STA로 진행한다. production227/GBC164/saveSRAM은 유지한다.
P2 미선택이며 자동 merge하지 않는다.
