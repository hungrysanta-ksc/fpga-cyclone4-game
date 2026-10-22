# NES277 — 한 번의 payload 소비와 고정 RAM 포트 소유권

원본 payload의 검증용 재읽기를 없앨 수 있는 데이터 경로는 확인했다.
그러나 **재읽기 제거만으로 60fps 시간·회로 부족을 함께 해소할 근거는 없다.**
276의 실행 결과를 다시 분석하고, 실제 원본 packet·65816 read trace를 입력으로
한 번 읽기 모델을 실행했다. 새 RTL/ARM/65816 실행·Quartus MAP은 하지 않았다.
현재 측정 기준은276의18.222145ms와18245comb이며 부족량1.555478ms/2837comb는 그대로다.

## 역할과 “한 번 소비”의 범위

ARM은 원본 descriptor·payload·H2·manifest와 token/credit 계획을 생산한다.
FPGA는 실제 소비된 원본 descriptor에 대해 범위·길이·중복·누락과 내용 CRC를 검사한다.
SNES는 DMA/WRAM 갱신과 bank 재사용, 표시/VBlank, 완료 ACK를 담당한다.
FPGA의 검증 입력을 SNES가 읽는 queue 출력에 붙이는 것이 이번 검토의 기준이다.

일반 명령의 기존 실제65816 경로는 packet을 queue에서 WRAM으로 DMA한 다음,
WRAM 자료로 명령 실행·PPU DMA 또는 HDMA bank 갱신을 한다.
따라서 queue의 마지막 바이트를 읽었다는 사실은 PPU DMA 완료가 아니다.
읽기 중 계산한 CRC는 잠정 결과이고, 같은 descriptor의 ordered ACK까지 있어야
receipt/재사용 유효성을 확정할 수 있다. FPGA가 실제 PPU 쓰기를 직접 관측한다는
주장을 추가하지 않는다. 기존 CPU 실행/ACK 계약을 그대로 유지한다.

- literal은 SNES queue 읽기에서 나온 각 바이트를 CRC 입력과 결합한다.
- repeat2/4는 원본2/4B를 한 번 읽고 최대4B 패턴으로 논리 출력 순서를 생성한다.
  확장한 출력마다 같은 queue 주소를 재요청하지 않는다.
- 내부 H2/requirements/manifest는 SNES가 읽지 않는다. 같은 host 실행기가 queue를
  한 번 읽고 의미검사를 진행하며, 필요하면 내부적으로 backpressure할 수 있다.
- typed map은 원본 queue payload를 한 번 읽어 shared staging에 쓴다. 이후 SNES의
  staging DMA 읽기는 여전히 필요하다. staging 쓰기를 receipt로 간주하지 않는다.
- tile ROM 생산·plan queue·tile/map aperture는 남는다. 입력 source codec의 읽기까지
  없애거나 모든 메모리 접근을 딱 한 번으로 줄였다는 의미가 아니다.

현재 host admission의 header 읽기와 SNES packet header 읽기도 남는다.
“한 번”은 enqueue 후 **원본 body를 검증 때문에 다시 읽지 않는 것**을 뜻한다.
SPI 수신 시 queue 기록과 전송 CRC, SNES WRAM/PPU 접근은 별개의 필수 작업이다.

read tap은 매 clock 변하는 RAM 출력 자체가 아니라, 주소 tag와bus_valid가 맞는
실제 SNES read의 바이트를 잡아야 한다. read 종료 observer가 늦게 도착해 다음 주소의
RAM 값을 CRC에 넣거나, 한 read를 여러 번 계산하지 않도록 data/tag/valid 보관 비용을
포함한다. 이것도 아직 설계 조건이며 현재 trace 대조가 새 tap 회로를 증명하지는 않는다.

## 비교한 세 가지 구조

|안|원본 body 처리|포트·제어 비용|판단|
|---|---|---|---|
|A: 기존 NES 검증 core에 read tap 전달|일반 명령을 SNES read 때 전달, 내부 manifest는 기존 경로|byte CDC와 NES 검사 FSM, queue head 유지; SNES가 멈출 수 없는 burst의 수신 capacity 증명 필요|가장 작은 변경이지만 내부 후처리와 대부분 제어가 남음|
|B: host 출력 실행기 + 고정 두 클록 phase RAM|일반 read tap·내부 packet·map staging을 한 host 실행기가 소유|NES source 단일 포트화, host receipt 단일 포트화, phase grant/return, host CRC 필요|구조 검증 대상으로 가장 타당하나 시간·면적 채택 게이트 미충족|
|C: SPI ingress에서 검증·완료 처리|수신 때 내용 검사|4개 queued packet의 잠정 상태·rollback/commit 필요; 수신은 DMA 완료가 아님|ingress로 receipt까지 확정하는 안은 거절|

C에서 전송 CRC나 잠정 내용 CRC만 미리 계산하는 것은 가능하지만, 실제 소비·ACK
검사를 없애지 못한다. 최대4credit의 검증 문맥이나 취소 비용을 무료로 두지 않는다.
A에서도 existing mailbox가 모든 SNES burst를 무손실로 받을 수 있다고 가정하지 않는다.
보존한544개 CPU trace의 최소 packet read 간격은8 master clocks,
약31.291 host clocks다. 이것은 관측 간격이며 core stall/paused clock을 포함한 FIFO
용량·하드웨어 응답시간 증명이 아니다. 추가 버퍼를 쓰면 면적·RAM에 포함해야 한다.

## B의 RAM 포트 소유권

클록 mux를 넣어 사용 중인 RAM의 클록을 바꾸는 방식을 선택하지 않는다.
아래는 제안한 고정 포트 계약이다. 아직 이 구성의 RAM inference/배치/CDC 검증은 없다.

|저장소|포트 A|포트 B|소유권 경계|
|---|---|---|---|
|4×256B packet queue|host/SPI 기록|host/SNES 읽기 또는 내부 실행|immutable head와4credit 유지; read tap은 B 출력 사용, 제3포트 없음|
|2×2KiB tile/map staging|기존 producer 기록|기존 SNES DMA 읽기|seal/read coverage/token consume까지 유지|
|1024×8 phase RAM 제안|NES source 전용,512..1023|host 출력 검증 전용|입력 완료·query/transport/pending write drain 후 grant; final ACK·출력 write drain 후 반환|
|source base·source block RAM|기존 NES/host 연결|기존 연결|계속 비용에 포함|
|plan RAM·ROM arbiter|기존 producer/consumer|기존 연결|early-copy credit와tile 경쟁 유지|

276 phase RAM의 양 포트는 현재 **모두 NES clock**이다. source FSTORE는 변경 바이트와
mask를 동시에 쓰고, 출력 receipt는 received와persistent validity를 동시에 갱신한다.
B는 단순 포트 이름 변경으로 구현할 수 없다.

source 쪽 B write는 mask 저장뿐이며 source의 `b_q` 소비는 없다. FSTORE 다음은
scratch에 쓰지 않는 FETCH 또는 BLOCKEND다. mask를 그 한 슬롯 뒤로 미루는 모델에서
68block/4398B, 전체 변경·무변경·교대 변경3vector의 결과가 원래 두 포트와 같았다.
프레임당574 mask write, pending address9+data8+valid1=18bit를 비용 대상으로 잡았다.
모델상 추가 cycle은0이다. 안전한 별도 stall로 구현하면574cycle=0.026091ms가
추가될 수 있다. 둘 다 새 RTL source 시간 측정값은 아니다.
STOP이 그 사이 들어오면 pending write를 취소하고 이후 RAM freeze를 유지해야 한다.

host 단일 포트에서는 received/persistent의 read-modify-write를 직렬화한다.
두 RAM의 동시 RMW를4개 접근으로 바꾸면 갱신당 최소2 host cycle이 추가된다.
954의 일반 receipt 범위 기준 이 추가분만16cycle=0.000190ms다.
manifest 비교·CRC·H2/표시 fetch·초기화와 상태 전환 비용은 이 숫자에 포함되지 않는다.
범위별 token을 내보내기 전에 해당 write를 모두 완료해야 한다.

phase RAM의 validity0..331, CRC332..395는 입력 동안 보존한다.
output received396..561/map562..817/H2 832..863/display offsets864..867의 수명을 유지한다.
출력 단계의 free170B를256B packet buffer로 계산하지 않는다.
수명 공유를 이미 하고 있으므로 이번 안의 RAM 절감량으로 다시 세지 않는다.

기존49bit admission과 final ACK CDC는 남기고 phase grant/return과 묶는 방향이다.
admission의 발생 시점을 source commit·transport empty·query pending=0·mask drain으로
제한할 수 있는지 확인해야 한다. 현재 admission을 수정 없이 재사용할 수 있다는 증거는 아니다.
STOP은 양 clock에서 먼저 쓰기/응답을 금지하고, grant epoch 및 bank 유효성을
무효화해야 한다. 한 clock이 정지해도 늦은 grant/ACK가 새 프레임에 적용되면 안 된다.

## 확정한 교체 대상과 유지할 검사

**B를 구현할 때 삭제 대상**은 아래 제어의 실제 인스턴스/경로다.
이번에는 삭제를 구현하지 않았으며 장부에서 회수했다고 처리하지 않는다.

1. host의 OPUSH/OMETA/OREPLY/OBYTE/OBWAIT,8워드 descriptor 전송과 바이트 주소 왕복.
2. core의 P_LOAD/P_READREQ/P_RECV/P_PCAP 및 source 레지스터를 선택하는120bit
   출력 문맥 alias, local event/continuation mux. host의 원본 header를 직접 사용한다.
3. NES 출력 receipt/H2/manifest/display 상태와 host의 packet 완료 상태를 잇던
   per-byte/per-range 요구·응답 제어. 필요한 의미검사는 host 실행기로 한 번 옮긴다.
4. `consumed`24bit와 `receipt`8bit mailbox. map range·display read도 host에서
   처리할 때만 두 인스턴스를 제거할 수 있다. 일부 경로만 옮겼다면 제거 비용으로 세지 않는다.

**남길 기능**은 다음과 같다.

- SPI 실제 transaction 길이/CRC16/immutable admission, serial·generation·bank·sequence,
 4credit 및 head pinning, wrap/소진 token 정책.
- command 주소/section/길이/정렬, 패턴2/4B, RLE expansion 범위,
  partial granule 거절, 중복·누락 범위와 독립 manifest 대조.
- 정확한 packet/staging read 순서·길이, ordered ordinary ACK,
  tile/map DMA token과 완료 receipt, plan copy credit와tile 완료의 분리.
- fresh scroll CRC, raw-tail granule CRC64B와bank 재사용 validity,
  H2 identity/content/certificate CRC 및 최종422B coverage.
- STOP first-fault, stale ACK 차단, bank 무효화와pending write 취소,
  source/display lease,12B exact display view, drain·VBlank 후 final ACK.

CRC를 read tap에서 먼저 계산해도 receipt를 먼저 발행하지 않는다.
한 literal packet이 여러 raw granule을 바꾸면 CRC RAM에 잠정 기록할 수 있으나,
그 bank의 재사용/표시는 ACK 전 금지해야 한다. 실패하면 bank를 무효화하고 cold 재구축한다.
이때 과거 CRC로 rollback하는 별도 shadow RAM을 가정하지 않는다.
원본 descriptor를 유지한 채 ACK 후 해당 granule의 receipt를 순서대로 commit한다.
STOP 후에는 잠정 기록의 후속 write도 금지한다.

source CRC datapath는 NES에서 유지된다. host CRC는 같은 조합 회로를 클록 간에
공유할 수 없다. 별도 CRC16 또는 기존 SPI CRC와의 중재·accumulator·deadline을
새 비용에 반드시 포함한다. source와output 문맥 register도 서로 다른 clock에서
더 이상276처럼 직접 alias할 수 없다.

## 시간: 재읽기 제거의 한계

276의 실제 parser 이벤트에서 OSETUP→qretire 구간을 합산했다.
이 구간에는 필수 의미검사도 포함되므로 전부0으로 두는 계산은 매우 낙관적이다.
또한 SPI·ARM·ROM·poll 이벤트는 그대로 둔다. **재실행한 일정이나 일반적인 시간
하한/상한이 아니라, 현재 일정에서 직접 비용만 지워 보는 민감도**다.

|954 기준|시간|
|---|---:|
|276 source+output 진단|18.222145ms|
|일반·tile parser 합계|0.041033ms|
|내부 manifest/SEAL까지 포함한 전체 parser|0.275519ms|
|전체 parser를0으로 둔 고정 일정|17.946626ms|
|그때도 남는 부족|1.279959ms|

일반 read tap만으로 없앨 수 있는 구간을 넉넉하게 잡아도0.041033ms이며,
전체 parser를 제거하는 민감도에서도 warm5/69가 초과한다.
내부 manifest/SEAL이 parser 시간의 대부분을 차지한다.
실제 구현에서는 필수 검사와 새 포트 직렬화·CRC·grant 비용이 다시 들어간다.

954의 E2는110회다. 2.625MHz의9B wire+transaction8us만으로 E2당0.035429ms다.
위 낙관적 parser 제거 후1.279959ms를 이 항목만으로 메우려면 **37회**가 사라져야 한다.
poll 직전 ARM 명령을 전부 polling 비용으로 간주하지 않았으며,37회 절감이 가능하다고
예측한 것도 아니다. IRQ/refill/ROM 준비가 poll 수를 결정하므로 실제 일정 재실행이 필요하다.
기존270/271/276에서 확인한 것처럼 polling 변경은 시간이 앞뒤로 이동하거나 악화될 수 있다.

|제한 ROM 조건|276|전체 parser0 고정 일정|
|---|---:|---:|
|905|90.393415ms|89.886921ms|
|906|114.311219ms|113.772706ms|
|907|18.204691ms|17.972791ms|

907도1.306124ms가 남는다. 제한3프레임의 기존 절대 종료265.001456ms를
개별 행의 절감 합만큼 앞당겼다고 주장하지 않는다.
CPU 일반명령은 기존forced-blank trace이고, map/tile/final display는 모델이다.
full ARM planner/RUN/NVIC·전체65816 polling·active VBlank·physical60fps는 여전히 미검증이다.

## 회로: 삭제 목록과 회수량을 구분

276 whole Lite MAP은18245comb,8832FF,303712RAM bits다. device15408comb 대비2837 부족이다.
실제 MAP의 자기 비용을 사용하며 inclusive parent/child를 더하지 않았다.

|항목|기존comb|판단|
|---|---:|---|
|core own + host own + queue|5527|source 연산과필수검사도 들어 있음; 모두 삭제 가능한 제어가 아님|
|위 두 출력 mailbox|34|21+13comb,56+24FF; B 전체 이동 때만 삭제 대상|
|B 교체 영역 합계|5561|새 source·host 실행·CRC·포트 제어·grant 비용 포함 필요|
|영역 외 기존회로|12684|ROM/plan/tile/기타 포함, 그대로 비용 유지|
|영역에 허용되는 산술 예산|2724|5561→2724,약51.02% 축소 필요; 배치/mapper 여유 제외|

mailbox34comb만 없애도 잔여 부족은2803comb다.
source codec/query, 입력 transport·plan early-copy를 그대로 두면서 단순히 출력 검사를
다른 clock으로 옮기는 것만으로51% 감소한다고 추정하지 않는다.
새 comb·FF·RAM 및 순회수량은 측정 전까지 null/미확정이다.
**검증된 회수량은0이며, 새 FIT/STA를 진행할 근거는 아직 없다.**

## 새 검증과 재사용 증거

`tools/analyze_nes_singlepass277.py` analysis03을 선택했다.

기존 private276 자료가 있는 저장소에서 재현한다. 출력 디렉터리는 새 경로여야 한다.

```powershell
python -X utf8 tools/analyze_nes_singlepass277.py --baseline ../probes/nes-joint276 --out ../probes/nes-joint277/reproduce01
```

- 276의1231개 actual E1 packet의 전송 CRC를 확인했다. 총59430 body bytes를
  순차1회 읽고 repeat pattern을 확장했다.
- 71프레임/2069map 범위/13406map B,128041일반 논리출력B가 복원됐다.
  프레임마다 metadata8570B/receipt754B/CRC64B가 기존 독립 기대값과 byte-exact다.
  fresh 내용 CRC 입력은총1989B이며 재사용 raw bank CRC는 보존한다.
- 기존544개 actual65816 trace의 주소순서와 모든 packet byte를 offline 대조했다.
  새 CPU 또는 live RTL replay는 아니다.
- STOP/순서·길이·identity·token/조기 ACK/manifest·certificate/final view/VBlank,
  source pending write와phase grant/return을 포함한71개 **추상 계약 모델** 거절 사례 PASS.
  실제 CDC/RTL STOP 주입을 새로 통과했다는 뜻은 아니다.276의49개 실제 RTL guard는 별도 과거 증거다.
- source 두 포트→한 포트의 지연 mask 저장3vector를 비교했다.
  출력 RMW cycle 값은 포트 접근 산술이며 실제 executor latency가 아니다.

analysis01은 `b_q` 문자열 검사가 `ram_b_q`까지 세는 audit 코드 오류로 실패했다.
정확한 identifier 검사로 고친 analysis02 PASS와, 포트 소유권 거절 사례·MAP mailbox
추출을 추가한 analysis03 PASS를 모두 보존한다. RTL/라이선스 실패가 아니다.

## 결정과 다음 게이트

B를 **다음 구조 검증의 경계**로 정한다. 최적화 채택이나 제품 교체는 아니다.
기존276을 개별 opcode/FF/FSM encoding으로 다듬거나 근거 없이 FIT를 반복하지 않는다.

다음 시제품은 위 삭제 목록을 실제로 대체하고, 고정 포트·source mask 지연·host 단일
포트 검사·STOP grant 취소를 함께 구현해야 한다. 같은 whole Lite MAP에서 새 영역
2724comb 예산과 배치 여유에 접근하는지 먼저 판단한다. 실패하면 이동만으로 절감했다고
주장하지 않고 역할/표현 자체를 다시 검토한다.

시간 게이트에서는 원본 ARM wire와CPU command를 유지한 actual refill/IRQ·E0/E2·ROM
경쟁 일정을 다시 실행한다. 직접 parser 절감 외에도 적어도 약1.280ms와 새 비용을
회수할 근거가 필요하다. source 지연이나 bank 재구축, 추가 FIFO/CRC를 비용에서 빼지 않는다.
두 게이트를 함께 통과한 뒤 whole FIT/STA/full RUN/실기 단계로 간다.
production227/GBC164/saveSRAM 유지, P2 미선택, 자동 merge하지 않는다.
