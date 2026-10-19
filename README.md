NES269: STOP 후 양 bank 표식을 지우고6006으로 응답하는 경계를 실제65816과 RTL에서 검증했다. 짧은 STOP·DMA/MVN·부분ACK·버스 철회7지점, 기존522명령/33범위/38오류를 통과했다. RUN STOP 중 local ROM/6001은 유지하고 pad/packet/ACK는 차단한다. 71프레임의 polling·ROM 재실행 warm 직렬 진단 최대는18.294508→18.391188ms, 부족1.724522ms이며6개 초과다. 안전 경로 비용까지 포함한 Lite MAP은17679→17692comb/2284초과, RAM동일이다. source·receipt 포함6512comb 교체 경계는4228이하가 필요한 장부이며 실제 대체 절감은0이다. 짧은 상태조회는 추가transfer setup을 포함해2.317ms의 고정poll 후보 여지가 있으나 구현된 절감이 아니다. fullRUN/activeVBlank/실기/FIT/STA는 미완료, P2 미선택이다. [검증 계약](docs/nes-joint269-contract.ko.md) · [계획](docs/nes-joint269-plan.json). 아래는 이전 기록이다.

NES268: 실제65816 HDMA zero DMA와 bank-tail 재사용을522일반명령·33경계명령에서 검증했다. 재사용은 cold2회만1100B를 채우고69회 생략한다. 같은ARM/SPI/ROM RTL의71프레임 직렬 진단 최대는20.909704→18.294508ms, warm초과25→6개이며60Hz까지 최소1.627841ms가 더 필요하다. E0 polling5380→3465회. 보드의 중복 legacy E0/E1을 제거한 Lite MAP은23714→22657LE/18399→17679comb/9488→9045FF/RAM8192bits감소이며2271comb가 아직 초과다. queue+plan3블록1427comb를 비용0으로 둬도 밖에서844comb가 더 필요하다. 실제decoder/staging의 head 유지 정책은 교착, RAM 복사 후 해제 정책은 완료했다. fullRUN/activeVBlank/실기/FIT/STA/통합STOP은 미검증이며 P2 미선택이다. [현재 검증](docs/nes-joint268-contract.ko.md) · [계획](docs/nes-joint268-plan.json). 아래는 이전 기록이다.

NES267: 실제 ARM refill/IRQ 본체·E8/E9 tile 계획·ROM reader와 실제65816 일반 명령의 bus trace를 통합71프레임에서 검증했다. whole-board Lite MAP은 23714LE/18399comb/9488FF, 조합 논리만 칩 한도15408을 2991개 초과해 자원 게이트 실패다. H2 공유 전후 같은 보드 delta는 -102LE/-169FF다. CPI1/항상 허용 ROM 슬롯 조건의 source+출력 직렬 진단 최대20.909704ms, warm69 중25개가16.667ms를 넘었다. 실기/전체RUN/active VBlank/FIT/STA/CDC 승인이 아니며 P2 미선택이다. [현재 검증](docs/nes-joint267-contract.ko.md) · [계획](docs/nes-joint267-plan.json). 아래는 이전 기록이다.

NES266: H2와 표시 문맥을 결합하고 기존 phase RAM864..867에 오프셋4B만 저장했다. 71프레임·38오류와 실제65816의905/906/907 표시/HDMA/최종ACK PASS. 통합 Lite MAP8277→8149LE(-128),2924→2755FF(-169),RAM90368bits 유지. warm출력5.847475ms로 기존 재전송 제거 이득을 유지했다. 전체ARM/일반65816/ROM중재/wholeFIT/실기60fps는 미완료다. [현재 검증](docs/nes-joint266-contract.ko.md) · [계획](docs/nes-joint266-plan.json). 아래는 이전 기록이다.

NES265: header identity/ACK 저장·재읽기 제어를 실제로 교체하고 manifest/fence를 FPGA 내부에서 처리했다. RTL71프레임·29오류 PASS,byte echo0 유지. 표시 문맥24B 보관·sealed 후1회 읽기를 포함해 warm출력최대5.846112ms,동일 Lite MAP8277LE(+47)/90368bits. queue는163comb/117FF 줄었으나 전체 면적 절감에는 실패했다. full ARM/일반65816/ROM/VBlank/FIT/실기60fps는 미완료다. [현재 검증](docs/nes-joint265-contract.ko.md) · [계획](docs/nes-joint265-plan.json). 아래는 이전 기록이다.

NES264: ACK 후 queue head를 유지해 수신 payload에서 직접 CRC·receipt를 만들고 manifest를 요구166B→map256B→fence 순서로 바꿨다. ARM/RTL71프레임,RTL19오류/ARM18오류 PASS;byte echo55237→0. warm출력최대5.912ms,동일 Lite MAP8230LE(+943)/90368bits. full ARM/일반65816/ROM/VBlank/FIT/실기60fps는 미완료다. [현재 검증](docs/nes-joint264-contract.ko.md) · [계획](docs/nes-joint264-plan.json). 아래는 이전 기록이다.

NES263: 실제 일반 SPI 패킷→native C 소비기→SNES 버스/공유CDC→core manifest/CRC/receipt를71프레임에서 검증했다. 실제65816 문맥 재사용은cold64DMA에서1148clocks 느리지만 warm7DMA에서566clocks 줄었고,조회 MAP7216LE는 같다. 일반byte-event bridge는7287LE(+71)/RAM동일,출력모델warm최대7.441ms로60fps 구현에 선택하지 않았다. 일반65816/full ARM/ROM경쟁/wholeFIT/실기60fps는 미완료다. [현재 검증](docs/nes-joint263-contract.ko.md) · [계획](docs/nes-joint263-plan.json). 아래는 이전 기록이다.

NES262: H2를 BEGIN 앞에 보내 실제 SPI→core 문맥RAM→일반 BEGIN ACK 경로를 연결했다. ARM71계획·기존12오류/신규6선행검사와 공유RTL71프레임/124묶음/2069범위/12취소를 통과했다. 기존24bit map 완료 mailbox를 공유해 별도 구조7266→7216LE(-50),2830→2806FF(-24),RAM90368bits 유지;261 대비+75LE로 전체 여유는 미입증이다. ARM2320text/312bss/관측stack136B,전체SPI량 동일. setup900 민감도와 실제중첩을 비교했으며 일반stream/digest/manifest 생산기·full ARM/65816·ROM 중재·wholeFIT·실기60fps는 미완료다. [현재 검증](docs/nes-joint262-contract.ko.md) · [계획](docs/nes-joint262-plan.json). 아래는 이전 기록이다.

NES261: 실제 source/core→묶음 map DMA/receipt→표시 lease를 연결해71프레임/124묶음/2069범위와6취소 검사를 통과했다. 실제65816 cold4096B/64DMA·VRAM·표시ACK도 통과했다. 같은4credit cold 출력 경계18.392→15.765ms, warm907은0.858→0.627ms다. 통합Lite MAP7141LE/5665comb/2788FF/90368bits이며 기존 제어 제거 장부를 포함해도 논리 여유는 미입증이다. 실제CPU의 nominalDMA 외900..948master clocks로500setup 배정을 재검토한다. non-map/H2/manifest 생산기·full ARM·전체65816/ROM 중재·wholeFIT·실기60fps는 미완료다. [현재 검증](docs/nes-joint261-contract.ko.md) · [계획](docs/nes-joint261-plan.json). 아래는 이전 기록이다.

NES260: ARM이2,069개 map 범위를124개 패킷으로 묶고 FPGA는 범위별 DMA·receipt 후 마지막에만 head/credit을 반환한다. 954 출력 ARM 완료 모델11.047→7.222ms,같은48DMA/714B다. 입력·출력 공유SPI는14.381ms/CPI2에서는16.550ms로잔여0.117ms다. Lite MAP3282→3509LE(+227),RAM41216bits 유지로 시간·회로 상충을 확인했다. full RUN/실제65816 전체 명령/최종 표시/전체FIT·60fps는 미완료다. [현재 검증](docs/nes-batch260-contract.ko.md) · [계획](docs/nes-batch260-plan.json). 아래는 이전 기록이다.

NES259: Cortex-M4 명령으로 실제 token·4credit·serializer·H2를 실행해71계획/12오류/queue counter순환을 검증했다. 출력 RTL은 전체 metadata/tile과 일반 명령·typed consume·최종 ACK를 비교하고 source/output 공유 SPI를 연결했다. SNES/CPI/ROM 대기는 조건부 모델이며 full RUN·표시는 열려 있다. 공유 MAP3282LE/41216bits로258보다37LE 감소했으나954 조건부 입력+ARM출력17.30ms로 시간 게이트 실패. Quartus Lite를 기본으로 사용한다. [현재 검증](docs/nes-output259-contract.ko.md) · [계획](docs/nes-output259-plan.json). 아래는 이전 기록이다.

NES258: 일반/typed 단일 head·retire와 실제206 tile/map staging 공유를 연결했다. 공유/분리 각각 정상+16검사, 실제65816 일반 ACK→tile16B/map64B DMA→receipt→표시 ACK 통과. 같은 직렬 일정의 MAP은3559→3319LE,73984→41216bits로240LE·4KiB 감소하며 실행 기록은 같다. Standard 평가판 만료 재확인/Lite 합성 성공. 전체 R1/FIT/60fps는 미완료다. [현재 검증](docs/nes-mux258-contract.ko.md) · [계획](docs/nes-mux258-plan.json). 아래는 이전 기록이다.

NES257 R1 첫 범위: 입력 완료 후 표시 lease로 전환하고 실제 packet→staging→65816 DMA(64B VRAM 일치)→receipt→seal→VBlank 표시 ACK 연결과9개 취소 검사를 통과했다. 논리적 RPC 연결이며 전체 R1·실기60fps는 미통과다. Lite 단독 MAP1947LE/40960bits는 일반 ACK가 제거된 제한 경계다. [현재 검증](docs/nes-slice257-contract.ko.md) · [계획](docs/nes-slice257-plan.json). 아래는 이전 기록이다.

NES256 R0: PR129 머지2978f04를 확인한 새 브랜치에서 교체 경계와 전체 비용표를 확정했다. 552개 조건부 일정을 재구성했고 collector/display lease와 실제 DMA receipt 연결 문제를 확인했다. R1·전체FIT·60fps는 미통과다. [현재 경계](docs/nes-boundary256-contract.ko.md) · [실행 계획](docs/nes-boundary256-plan.json). 아래 머지 대기/NEXT는 당시 기록이다.

PR129 회고·다음 계획: 전체 회로와 프레임 예산을 같은 구성으로 판정한다. 머지 전 구현은 중단하며, 머지 확인 후 master 기준 새 브랜치·새 PR에서 시작한다. [회고](docs/nes-pr129-retrospective.ko.md) · [다음 계획](docs/nes-pr129-next-plan.json). 아래 NEXT는 당시 기록이다.

NES255: 선행 읽기와 receipt·바이트 소비 제어를 공유해 동일 경계에서 52LE·61FF 및 처리 시간을 줄였다. 전체FIT·60fps는 미입증이다. [최신 검토](docs/nes-joint255-contract.ko.md) · [현재 계획](docs/nes-joint255-plan.json). 아래는 이전 기록이다.

NES254: FSM 미추출 원인을 분리 검증하고 query/source와 인증서 RAM을 통합했다. MAP3404→3296→3239LE, 조건부500setup최대16.028909ms. 전체FIT·60fps는 미입증이다. [최신 검토](docs/nes-joint254-contract.ko.md) · [현재 계획](docs/nes-joint254-plan.json). 아래는 이전 기록이다.

NES253: 64B CRC를공유RAM에넣은실제query/source/SPI/검증경계의회로와시간을측정했다. MAP 2646→3404LE,조건부500setup최대15.993545ms. 전체FIT·ARM·SNES여유는미입증이다. [최신 검토](docs/nes-joint253-contract.ko.md) · [현재 계획](docs/nes-joint253-plan.json). 아래는 이전 기록이다.

NES252: HDMA의상속내용까지봉인하려면새수신분CRC만으로는부족하다. 양bank의raw-tail CRC64B를보관하는후보는단순재전송보다유리하며조건부잔여0.454ms다. 실제RTL·논리회수·MCU시간은아직미입증이다. [최신 검토](docs/nes-binding252-contract.ko.md) · [현재 계획](docs/nes-binding252-plan.json). 아래는 이전 기록이다.

NES251: 단계별 공유 RAM으로 M9K instance 하나를 줄였지만 논리는33LE 늘었다. ARM HDMA 검사는97779사례를 통과했으며,실행·봉인 비용을 배정한 조건부 잔여는0.485ms다. 전체 논리·시간 여유가 미확보라 P2로 선택하지 않았다. [최신 검토](docs/nes-joint251-contract.ko.md) · [현재 계획](docs/nes-joint251-plan.json).

NES250: source+receipt 공동MAP1506LE,남은 SNES layout/HDMA 검사 약0.654ms. 실측 반영 조건부 최대16.355ms/공동잔여0.312ms이며 회로·시간 여유가 미입증이라 독립 코어 추가 구성은 P2 후보로 채택하지 않았다. [최신 검토](docs/nes-joint250-contract.ko.md) · [현재 계획](docs/nes-joint250-plan.json). 아래는 이전 기록이다.

> 최신 ROM 응답 결합: ROM 응답 로컬8비트를 실제 service/arbiter/FIFO/reader에 결합했다. 70ns 모델16위상과9.904ns 데이터 지연에서 기존 응답/샘플과 같았으며, 새8개 경계만 제한했다. FIT15048LE/963LAB/38M9K, 배선 평균68.8→61.4%·수직peak91.2→75.8%로 개선됐다. 실제setup−1.408ns/hold+0.147ns로 전체타이밍은 아직 실패이며 새SD패키지는 없다. [검증·다음 단계](docs/nes-replyjoin181-contract.ko.md)

> 최신 배선 연구: 공식 배선 최적화 자료와 현재 보고서를 대조해 ROM 응답을 수신 클록에서 받는 RTL 후보를 추가했다. reader 경계19경우(456읽기/714중단·리셋/19클록정지),9.904ns지연 및 잘못된 캡처 대조군을 확인했다. 응답 추가클록0은 단독 비교 범위이며 보드 결합·새FIT·실기 승인은 아직 없다. [설계 반영](docs/nes-routing181-design.ko.md)

NES181은 CDC 제약을 실제 전달 계약에 맞춰 수정해 전체 배치·배선에 성공했다(15,072LE/963LAB/38M9K). 하지만 실제 클록 setup −3.379ns, 같은 PLL memory→host −0.740ns로 타이밍은 실패했다. 새 데이터 경로·조건부 IO/리셋 검사는 통과했으나 설치 후보로 채택하지 않았고 새 ZIP은 없다. [검증·인계](docs/nes-cdc181-contract.ko.md). 아래는 과거 기록이다.

NES181 팔레트 선택 회로를 줄여 초기 배치는 통과했지만, 배선/자동 재시도에서965 LAB가 필요해 최종 FIT는 실패했다. 실패 보고는14,961 LE·38 M9K·배선 불가79신호(67 OAM)·공유 충돌75개다. 클록 간 hold 보정 합계605.4ns는 여러 신호의 지연 합이며 slack이 아니다. 타이밍·새 설치 패키지는 승인하지 않았다. [검증·인계](docs/nes-rank181-contract.ko.md). 아래는 과거 기록이다.

NES181의 실제 보드 color/emphasis·수집기·전송기와 paired MCU/SNES를 격리 통합했다. 전체 ARM RUN/IRQ 검사 여유1,032바이트와 보드 배선 결합을 통과했다. 공유 읽기로 FPGA 필요 LAB971→965(한도963), LE148개·M9K1개를 줄였지만 FIT는 실패했다. 실기 패키지·타이밍·60fps 승인은 아직 없다. [통합·남은 제약](docs/nes-board181-contract.ko.md). 아래는 과거 기록이다.

NES181의 배포용 SNES 수신·부분 행 표시·완료 ACK 후보를 연결했다. 실제 C sink→65816/DMA/HDMA/PPU에서 정상11장면630,784픽셀, 오류8종·STOP2종의 기존 화면 보존을 통과했다. 본문3,768/3,776바이트로4KB ROM에 들어간다. 보드 연결·전체 ARM/FIT·실기와60fps는 미완료다. [SNES 연결·남은 작업](docs/nes-client181-contract.ko.md). 아래는 과거 기록이다.

NES181의 COMMITTED 부분 행을 실제 MCU 코드로 SNES 패턴·팔레트·3HDMA와 새 sink payload로 변환했다.5장면47확인과 C출력→실제65816/DMA/PPU 양쪽뱅크114,688픽셀 비교 통과. video15,888/receiver18,064바이트 유지. 배포 SNES decoder·뱅크/ACK/STOP 연결과 보드·전체 ARM/FIT·실기는 미완료다. [표시 변환·남은 연결](docs/nes-consume181-contract.ko.md). 아래는 과거 기록이다.

NES181의 부분 행 전송과 MCU 수신 후보를 연결했다. 실제 fill·SPI RTL→C 수신기로0/1/7행,2,048픽셀과95경우를 검증했고 raw 중단7경우도 통과했다. ARM 수신 구조체18,064바이트는 기존과 같다. 배포 SNES 소비·보드 연결·전체 ARM/FIT·실기는 미완료이며180 배포본을 유지한다. [전송 구현·남은 연결](docs/nes-wire181-contract.ko.md). 아래는 과거 기록이다.

NES181 수집기 후보의 행별 대체·다음 정상 행 복구를 구현했다. 결합14경우, 정상180 대비9,624단어, 보존3,328픽셀과 정상복구43,923셀 비교가 통과했다. 별도 실제 PPU RTL에서1,792픽셀 정렬도 통과했다. 배포 보드·전송·MCU·SNES 클라이언트와 전체 배치·실기는 미완료이며 새 ZIP 없이180을 유지한다. [수집기 구현·남은 연결](docs/nes-collect181-contract.ko.md). 아래는 과거 기록이다.

NES181: 영향을 받은 최대7행만 실제 PPU 픽셀로 보존하는 RTL과 SNES 부분 행 표시 방식을 구현했다. RTL9경우/2,560픽셀, RTL 덤프→SNES 양쪽 버퍼114,688픽셀 전체 비교가 통과했다. 합성 입력 기반 독립 경로이며 실제 수집기·전송·MCU·배포 클라이언트 연결과 전체 배치·실기는 아직 미완료다. 새 ZIP 없이180을 유지한다. [구현·남은 연결](docs/nes-render181-contract.ko.md). 아래는 과거 기록이다.

NES180 실기에서 raster08·compact82·185/224행의 거부2회와 오류0·224행 회복2회를 확인했다. 첫 레벨 영상 정지·월드맵 회복 관찰과 부합하며 진단 목적은 달성했다. 영상 정지 해결·약60fps는 미완료다. 최초 오류 위치와 변경된 단일 PPU 필드는 미측정이며, 다음은 공통 렌더링 중단·재개 및 fetch 행 완결성 구현이다. [실기 분석](docs/nes-game180-hardware01.ko.md). 아래는 과거 기록이다.

NES180 최소 기록 실기 시험판 준비 완료. 상태3비트로 첫 거부·정상 회복만 남기는 규격3이 실제 SPI·MCU·ARM 링크·단일 FIT·조건부 IO를 통과했다.15,061 LE/962 LAB, 실제 클록 setup +0.096ns, ARM 여유1,040바이트다. 숫자1→A 실기 로그를 기다리며 영상 정지 해결·60fps는 아직 미완료다. [설치·실기 안내](docs/nes-game180-ready.ko.md). 아래는 과거 기록이다.

NES180 기록 저장 공간 재사용 두 후보는 기능 검증을 통과했지만 채택되지 않았다. RAM 재사용은15,024 LE/962 LAB에서 실제 클록 setup −0.227ns, 오류 문맥 공유는967/963 LAB으로 실패했다. 새 ZIP 없이 배포178을 유지한다. 다음은 최초 거부·회복으로 관측 범위를 줄이며 실기 영상 정지·60fps는 미완료다. [검증·다음 작업](docs/nes-rejectstorage180-contract.ko.md). 아래는 과거 기록이다.

NES180 거부·회복 기록 후보는 실제 SPI·수집기 해제·MCU 판독/로그 검증을 통과했다. 첫 배치는964/963 LAB으로 실패했고, 축소 후보는15,043 LE/963 LAB에 배치됐지만 실제 클록 setup −0.092ns로 미채택이다. 새 ZIP 없이 배포178을 유지하며 실기 화면 정지·60fps는 미해결이다. [검증·남은 작업](docs/nes-reject180-contract.ko.md). 아래는 과거 기록이다.

# FPGA Core Development — sd2snesHST

NES179 조사: 실제 SMB3 기준 실행에서 숫자1→A→첫 레벨에 도달했다. 레벨100프레임의 행중 렌더링 중단·재개를 확인하고 배포178 raster의 거부/회복16경우와 합성 타일 누락/회복5경우를 검증했다. 실기 전체 오류·유일 원인·수정 완료는 미확정이며 배포178 유지, 새 ZIP 없음이다. [조사·다음 작업](docs/nes-level179-investigation.ko.md). 아래는 과거 기록이다.

NES178 실기: 월드맵 진입과 게임 오버 뒤 영상 회복을 확인했지만 첫 레벨에서는 영상이 정지했다. 표시 완료69회·마지막59.65초로 영구 정지보다 장면별 수집/표현 제약을 우선 조사한다. 레벨의 최초 거부 이유는 로그에 없어 아직 미확정이며, 지속 영상·60fps는 미완료다. [실기 분석](docs/nes-game178-hardware01.ko.md). 아래는 과거 기록이다.

NES178 실기 시험판 준비 완료: START 이후 mask18 거부를 수정한 FPGA·MCU·SNES 조합이 패킷 경계·전체 ARM·단일 FIT·조건부 IO 검사를 통과했다. 실제 게임 전환 후 영상 지속 여부는 사용자 실기로 확인하며 초기 끊김·60fps는 아직 미완료다. [실기 안내](docs/nes-game178-ready.ko.md). 아래는 과거 기록이다.

NES178: 목표 SMB3 일본판의 START 전환 후 mask18을 기존 수집기가 계속 거부하는 문제를 재현했다. 왼쪽8픽셀 클리핑을 보존하는 FPGA·MCU·SNES 후보와 경계/픽셀 검증을 완료했다. 전체 ARM 링크·FIT·실기 전이라 배포177 유지·새 ZIP 없음이며, 초기 끊김과60fps는 아직 미완료다. [검증·남은 작업](docs/nes-clip178-contract.ko.md). 아래는 과거 기록이다.

NES177 실기: START 화면 전환 때 영상만 정지한다는 사용자 관찰을 확인했다. 로그는27회 표시 완료·마지막12.48초 뒤 추가 BEGIN 없음, ABORT0이다. 종료 직전16클록에서 exporter IDLE/owned0/rawgeometry0/active1/fillbusy0/arbiterfault0이며 전송 적체 증거는 없다. 정상 수집 중간에도 가능한 표본이므로 반복 거부·결합 실패는 아직 구분하지 못했다. 연속 영상·60fps 미달성이며 새 패키지는 없다. [실기 결과·다음 작업](docs/nes-game177-hardware01.ko.md). 아래는 과거 기록이다.

NES177 실기 시험판 준비: 기존 history 하위22비트로 마지막 COMMIT 뒤 수집·소유권·전송·중재기 경계를 구분한다. 해제14위치 검증, 실제 클록 setup +0.055ns/hold +0.152ns, 조건부 IO, ARM 여유1040B, 최대TXT3925B 검사를 통과했다. 화면 정지 해결·60fps는 아직 미완료다. 무관한 로더 수정 없이 한 번의 FIT로 패키지를 만들었다. [검증·다음 작업](docs/nes-boundary177-contract.ko.md). 아래는 과거 기록이다.

NES176 회고 반영: 실제 SMB3 모델360프레임에서 즉시 해제349개·10프레임 보유35개 정상 후보와 기존 픽셀 일치를 확인했다. 두 장면의 전체5,493바이트 중 차이20바이트를 확인해 앞단 변경 전송의 근거를 마련했다. 공유 메모리 오류 연결6경우도 검증했지만 실기 정지 원인은 확정하지 않았다. 배포174 유지·새 ZIP 없음·60fps 미달성이며, 무관한 로더 미세FIT 반복을 멈춘다. [결과·수정 계획](docs/nes-video-review176.ko.md). 아래는 과거 기록이다.

NES175 READY·카운터 후보의 기능/SPI 검증은 통과했다. READY 경로 제거와 쓰기 대기 경로 +1.573ns 개선에도 전체 setup은 각각−0.048/−0.218ns로 실패해 두 후보 모두 미채택이며 새 ZIP은 없다. 배포174를 유지한다. [결과·다음 조건](docs/nes-ready175-contract.ko.md).

NES175는 느린 소비 후5회 전달·거부3회 후 회복을 연결 시험으로 확인했다. 실기 정지는 아직 미해결이며, 관측 후보 A4(-0.178ns)·A5(-1.114ns)는 타이밍 실패로 미채택이다. 새 ZIP 없이 검증된174를 보존한다. [검증 결과·다음 조건](docs/nes-lifecycle175-contract.ko.md).

NES174 실기:12회 표시 완료·마지막generation23/RUN3.81초 이후 영상만 정지했다. 사운드·조작은 정상으로 보인다는 보고이며 로그상60초 종료·메뉴 준비는 정상이다. 변환·전송/표시 확인 평균167.5ms, 연속 화면·60fps 미달성. 다음은 새 후보의 허용·해제·전달 경계다. [실기 분석](docs/nes-game174-hardware01.ko.md). 아래 시험판 준비 기록은 당시 상태로 보존한다.

NES174 실기 시험판 준비 완료: 실제 클록 setup +0.246ns / hold +0.156ns와 기존 외부 인터페이스 조건을 통과했다. 타일 간 비트평면 수정·묶음 전송을 새 FPGA/MCU에 함께 적용한다. 화면 정지 해결·60fps는 실기에서 확인할 차례다. [현재174 설치·시험 안내](docs/nes-game174-ready.ko.md).

NES174 로더의 명령 허용 상태를 분리해 전체 실제 클록 setup을 -0.807ns에서 -0.098ns로 개선했다. 기능·실제 SPI 연결은 통과했으나 타이밍은 여전히 실패다. 후속 속성 변경(-1.344ns)은 미채택이며 새 실기 ZIP은 없다. [타이밍 변경과 검증](docs/nes-legality174-contract.ko.md).

NES174에 타일 묶음 전송을 추가했다. SMB3 모델 장면의 패턴 요청18회→3회, 전체 요청45회→30회이며 실제 SNES 수신·229,376픽셀과 ARM 여유1040바이트를 확인했다. 실기 속도·60fps는 미확인이다. FPGA 타이밍-0.807ns와 전체 테이블 전송 비용이 남아 새 ZIP은 없다. [묶음 전송 검증과 다음 작업](docs/nes-batch174-contract.ko.md).

NES174 후보는 SMB3의 서로 다른 타일 비트평면을 보존하도록 수정했다. 모델frame24 수집과 frame24·25의114,688픽셀 비교, SPI·C 및 ARM 여유1024바이트 검증을 통과했다. FPGA 배치는 성공했지만 memory setup-0.807ns로 미채택이며 새 실기 ZIP은 없다. 실제 정지 해결·60fps는 미확인이고 반복 전송 비용도 남았다. [174 검증과 미완료 작업](docs/nes-cross174-contract.ko.md).

NES173 실기: RUN 시작 후5.79초까지 표시 ACK16회 뒤 추가 완료가 멈췄다. 변환/패턴 전송910ms와 테이블·SEAL/ACK2340ms, 합계 회당 약203ms로 초기 처리량도60fps 목표에 크게 못 미친다. 정상60초 종료·STOP/메뉴 준비 확인. 정지 원인 미확정, 같은173 재시험 없이 타일 간 plane 표현과 반복 전송/왕복 개선으로 진행한다. [173 실기 결과](docs/nes-game173-hardware01.ko.md).

NES173 실기 시간 측정판을 준비했다. 172 FPGA 전체 바이트·표시 프로그램을 유지하고 MCU에 수신 대기·변환/전송·표시 ACK 누적 시간과 마지막 표시 완료 시각을 추가했다. 화면 정지와 약60fps 연속 표시 목표는 아직 미달성이다. [173 실기 안내](docs/nes-game173-ready.ko.md) · [측정 범위](docs/nes-profile173-contract.ko.md).

NES172 실기에서 표시 준비와 14회 표시 완료 응답을 통과했지만 이후 화면이 멈췄다. 버튼·스테이지 음악은 계속 반응했고 정상 약60초 한도로 메뉴에 복귀했다. BEGIN/END/COMMIT 각14, ABORT0, 마지막 generation27이다.170의 수집 시간 초과와 달리 다음 BEGIN이 수신되지 않은 경계이며, 초반도 끊겼으며 약60fps 연속 표시 목표는 미달성이다. [172 실기 결과](docs/nes-game172-hardware01.ko.md).

현재164 실기: **검정 구간 제거 통과·사운드 정상으로 보임, 심한 갱신 지연으로 정상 플레이 미달성**. 다음은 영상 전송량·갱신 지연 개선이며, DOWN 유지는 이번 미시험입니다. [164 실기 결과](analysis/GAME164-HARDWARE-RESULT.ko.md).

이전151 실기: **SMB3 제목·캐릭터 표시와 메뉴 복귀 성공, PPU 읽기 오류로 조기 종료**. 정상 플레이·전체 버튼 입력은 미완료입니다. [151 실기 결과](analysis/GAME151-HARDWARE-RESULT.ko.md).

**sd2snesHST의 개발 저장소**입니다. FXPAK Pro의 코어 구현, 재현 빌드, 검증 근거와 이식 경험을 관리합니다.
제품 이름의 **HST는 HungrySanTa = 제작팀 이름**을 뜻합니다.

일반 사용자 안내는 [sd2snesHST](https://github.com/hungrysanta-ksc/sd2snesHST)에서 제공합니다. **sd2snesHST 0.9.0 = 검증된 GBC C44**를 [공개했습니다](https://github.com/hungrysanta-ksc/sd2snesHST/releases/tag/v0.9.0). 다음 작업은 NES 코어 이식이며, [GBC 회고](docs/development/GBC-PORTING-LESSONS.ko.md)와 [NES 인계 계획](cores/nes/HANDOFF.ko.md)에서 시작합니다.

## 어디서 시작하나요?

| 목적 | 문서 |
| --- | --- |
| 사용자 배포와 개발의 역할·버전 관리 | [두 저장소 운영 계획](docs/distribution/REPOSITORIES.ko.md) |
| 0.9.0 준비·발행 순서 | [0.9.0 공개 계획](docs/distribution/0.9.0-PLAN.ko.md) |
| 배포 저장소 첫 화면 초안 | [sd2snesHST](distribution/sd2snesHST/README.md) |
| 코어 현황·NES/PCE 후속 작업 | [코어 로드맵](cores/README.md) |
| 새 코어 조사 시작 | [코어 제안서](cores/CORE-PROPOSAL.ko.md) · [이식 절차](docs/PORTING-PLAYBOOK.ko.md) |
| 공통 구현과 코어 경계 | [개발 구조](docs/development/ARCHITECTURE.ko.md) |
| 모든 현재 문서와 과거 기록 | [문서 안내](docs/README.md) |

## 개발 기준선

| 구성 | 현재 상태 | 소스·재현 |
| --- | --- | --- |
| GB/GBC | C44 실기 확인, 0.9.0 공개 완료 | [GBC 개발 안내](cores/gbc/README.md) |
| NES | 164 첫 레벨·사운드·메뉴 복귀 확인; 화면 끊김으로 정상 플레이 미달성 | [NES 개발 안내](cores/nes/README.md) |
| PC Engine | 조사 대기; HuCard 범위를 우선 검토 | [PCE 조사 범위](cores/pce/README.md) |

현재 구현 대상은 **FXPAK Pro / Mk.III, STM32 + EP4CE15F17C8**입니다. 제품 이름이 바뀌어도 보드 지원 범위가 넓어지는 것은 아닙니다. NES/PCE의 동작 가능성·일정은 아직 확정하지 않았습니다.

이 보드·MCU·FPGA 대상은 [등록부](cores/registry.json)와 [NES 실기 준비 가이드의 하드웨어 기준](docs/development/NES-HARDWARE-READINESS-REVIEW.ko.md#확정된-개발-대상과-추가-확인-항목)에 고정합니다. 기존에 적힌 제품 정보를 반복해서 질문하지 않습니다. PSRAM IS66WVE4M16EBLL-70BLI 두 개와 MCU STM32F401RCT6도 사진으로 확인했습니다. 추가 확인은 실제 배선 지연·외부 타이밍 등 아직 확인되지 않은 항목으로 한정합니다.

검증된 GBC 입력 경로 `src/fpga`, `src/firmware-overlay`, `src/renderer`는 유지합니다. 코어별 안내·등록부로 구분하고, 실제 공통 코드 추출은 두 번째 코어의 요구가 확인된 뒤 별도 검증으로 진행합니다.

주요 진전마다 [코어별 기록·커밋·PR 절차](docs/development/MILESTONE-WORKFLOW.ko.md)에 따라 정리합니다. NES의 [공개 재현 시험](cores/nes/REPRODUCING.ko.md)과 전체 코어/실기 검증 범위는 구분합니다.

## 기록과 배포 원칙

- 구현 변경·upstream 출처·가설·실패 결과·재현 가능한 검증은 이 저장소에서 관리합니다.
- 사용자용 저장소에는 제품 안내와 릴리스만 정리합니다. 코드를 두 저장소에서 따로 수정하지 않습니다.
- 제품 버전, 코어 후보, 개발 커밋, 바이너리 해시, 세이브/상태 형식을 연결합니다.
- 상용 ROM·BIOS·개인 세이브·덤프·비밀 정보는 공개하지 않습니다.
- [라이선스](LICENSE.md) · [대응 소스 묶음](docs/SOURCE-BUNDLE.ko.md)
- [기여 규칙](CONTRIBUTING.md), [소스 고지](docs/DEPENDENCY-REGISTER.ko.md), [공개 정책](docs/REPOSITORY-POLICY.ko.md)을 따릅니다.
