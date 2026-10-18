# 현재 상태 — NES247 P0 완료 / P1 비교 중

NES247 P1 maskboundary-build01:mask8+manifest240/16+SEAL190+은행별초기화/기존coverage+STOP/finalACK 통합진단본문4398B,현재3936B보다462B초과(기존3903보다495B증가). Private상태760B/기존대비+166B. 조립·본문projection·주소비중첩 확인,새기능/오류/시간 재생미실행. 현재4KiB구성 유지후보로기각;SMB3개조나SNES일반ROM한도가아님. FPGA수신프로그램 저장크기는변경가능하며과거194 8KiB진단기록있음. 다음은저장/부팅경계와전체자원비교. 기존mask8 wire4095/4275모델·952/955 DMA초과·sourcearea·ARM미해결,P2미선정/생산227보존.

[전체 비용](../../docs/nes-wholepath247-contract.ko.md) · [P1 결합·소유권](../../docs/nes-schedule247-contract.ko.md) · [의미 투영·병렬 경계](../../docs/nes-relocation247-contract.ko.md) · [unused gap·DMA 계측](../../docs/nes-gap247-contract.ko.md) · [전체순회 기각](../../docs/nes-scan247-contract.ko.md) · [word 순회·직렬 비용](../../docs/nes-wordwalk247-contract.ko.md) · [배치 정렬·수신 비용](../../docs/nes-batchorder247-contract.ko.md) · [범위 크기·묶음 수신](../../docs/nes-coalesce247-contract.ko.md) · [map 공동 비용](../../docs/nes-mapjoint247-contract.ko.md) · [최신 통합 수신 크기](../../docs/nes-maskboundary247-contract.ko.md) · [현재 실행 상태](../../docs/nes-wholepath247-plan.json) · [71프레임 비용표](../../analysis/wholepath247-frames.csv)

P1:SNES수신프로그램의4KiB는현재FPGA저장설계값이며SMB3/SNES일반ROM한도가아님. 현재4KiB유지 vs8KiB확대 vs기존외부저장/WRAM적재 재사용의주소·boot·소유권·전체M9K/LE/LAB/시간을먼저비교;1948KiB기능근거와24054/56M9K미배치조건을구분. 근거없이새decoder/4398B미세축소/3971·3950B재조정금지.952순서·955최소4198/4192 표시비용,source449/rowshift면적,새ARM RUN/IRQ,firstfault/CDCIO/finalACK·lease·retire 공동여유전P2미선정.

PR127 머지 `b6958f24` 확인 후 새 `codex/nes-wholepath-247`에서 진행했다. 아래 PR127 및246 이전 NEXT는 이력이며 현재 지시가 아니다. PR127의 전체 목표와 보호 조건은 유지한다. 새 설치물·FPS·회로 구현 성공을 뜻하지 않는다.

---

# 현재 상태 — PR127 회고 반영 (2026-10-18)

PR127 회고:231/232 증분 출력 개선은 유지,241/246 공유 압축 후보는 기각.240도490LE/40LAB 부족. 면적만 맞춰도60fps가 되지 않으며 SPI/5개SNES burst/전체ARM/확장 여유를 공동 판단한다.

[현재 목표·인계](../../docs/nes-pr127-retrospective.ko.md) · [P0–P3 실행 계획](../../docs/nes-pr127-next-plan.json) · [PR127](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/127)

PR127 머지 확인 후 최신 master에서 새 codex/ 브랜치·새 PR. 기존 스크롤 자료의 전체 예산/변경 원인(P0)과 표현·처리 위치 포함 후보 비교(P1)를 먼저 하고 근거 있는 한 후보만 구현한다. 단일 sequencer는 미선정. 생산227·GBC164·save SRAM 보존.

아래 내용은 이전 개발 이력이다. 과거의 “최신”, 후보 번호와 NEXT를 현재 지침으로 사용하지 않는다.

---

> 최신 실제 묶음 전송: 실제 FPGA exporter/SPI와 C receiver에1813묶음 전송을 구현했다. 같은0/1/7raw행 fixture wire4861/6559/16774→922/1311/3486B, 모델2.994/4.244/11.097ms. 전체receiver byte일치·최대256run/1056map·취소8경우PASS. receiver18064B유지,추가상태소스9bit/ARM국소stack+40B. 새FIT/전체ARM/실기/60fps승인없음. [구현과 다음 단계](../../docs/nes-packed181-contract.ko.md)

> 최신60fps 공동 설계: 배선 개선은 동작 신뢰성 기반이며60fps 전송 개선은 아니다. 기존전송 재검사: SPI2.625MHz/60Hz 총5468.75B, SNES normal 최소21.206ms/raw34.819ms, 동일section도전체전송. raw7행 오프라인packing10752→2160B이나전체record6457B로여전히부족. 생산packing·bank별delta·capture/export겹침을지금계약에포함한다. 새FIT/펌웨어/실기/60fps승인없음. [계약과 다음 순서](../../docs/nes-cadence181-contract.ko.md)

> 최신 ROM 응답 결합: ROM 응답 로컬8비트를 실제 service/arbiter/FIFO/reader에 결합했다. 70ns 모델16위상과9.904ns 데이터 지연에서 기존 응답/샘플과 같았으며, 새8개 경계만 제한했다. FIT15048LE/963LAB/38M9K, 배선 평균68.8→61.4%·수직peak91.2→75.8%로 개선됐다. 실제setup−1.408ns/hold+0.147ns로 전체타이밍은 아직 실패이며 새SD패키지는 없다. [검증·다음 단계](../../docs/nes-replyjoin181-contract.ko.md)

> 최신 배선 연구: 공식 배선 최적화 자료와 현재 보고서를 대조해 ROM 응답을 수신 클록에서 받는 RTL 후보를 추가했다. reader 경계19경우(456읽기/714중단·리셋/19클록정지),9.904ns지연 및 잘못된 캡처 대조군을 확인했다. 응답 추가클록0은 단독 비교 범위이며 보드 결합·새FIT·실기 승인은 아직 없다. [설계 반영](../../docs/nes-routing181-design.ko.md)

NES181은 CDC 제약을 실제 전달 계약에 맞춰 수정해 전체 배치·배선에 성공했다(15,072LE/963LAB/38M9K). 하지만 실제 클록 setup −3.379ns, 같은 PLL memory→host −0.740ns로 타이밍은 실패했다. 새 데이터 경로·조건부 IO/리셋 검사는 통과했으나 설치 후보로 채택하지 않았고 새 ZIP은 없다. [검증·인계](../../docs/nes-cdc181-contract.ko.md). 아래는 과거 기록이다.

NES181 팔레트 선택 회로를 줄여 초기 배치는 통과했지만, 배선/자동 재시도에서965 LAB가 필요해 최종 FIT는 실패했다. 실패 보고는14,961 LE·38 M9K·배선 불가79신호(67 OAM)·공유 충돌75개다. 클록 간 hold 보정 합계605.4ns는 여러 신호의 지연 합이며 slack이 아니다. 타이밍·새 설치 패키지는 승인하지 않았다. [검증·인계](../../docs/nes-rank181-contract.ko.md). 아래는 과거 기록이다.

NES181의 실제 보드 color/emphasis·수집기·전송기와 paired MCU/SNES를 격리 통합했다. 전체 ARM RUN/IRQ 검사 여유1,032바이트와 보드 배선 결합을 통과했다. 공유 읽기로 FPGA 필요 LAB971→965(한도963), LE148개·M9K1개를 줄였지만 FIT는 실패했다. 실기 패키지·타이밍·60fps 승인은 아직 없다. [통합·남은 제약](../../docs/nes-board181-contract.ko.md). 아래는 과거 기록이다.

NES181의 배포용 SNES 수신·부분 행 표시·완료 ACK 후보를 연결했다. 실제 C sink→65816/DMA/HDMA/PPU에서 정상11장면630,784픽셀, 오류8종·STOP2종의 기존 화면 보존을 통과했다. 본문3,768/3,776바이트로4KB ROM에 들어간다. 보드 연결·전체 ARM/FIT·실기와60fps는 미완료다. [SNES 연결·남은 작업](../../docs/nes-client181-contract.ko.md). 아래는 과거 기록이다.

NES181의 COMMITTED 부분 행을 실제 MCU 코드로 SNES 패턴·팔레트·3HDMA와 새 sink payload로 변환했다.5장면47확인과 C출력→실제65816/DMA/PPU 양쪽뱅크114,688픽셀 비교 통과. video15,888/receiver18,064바이트 유지. 배포 SNES decoder·뱅크/ACK/STOP 연결과 보드·전체 ARM/FIT·실기는 미완료다. [표시 변환·남은 연결](../../docs/nes-consume181-contract.ko.md). 아래는 과거 기록이다.

NES181의 부분 행 전송과 MCU 수신 후보를 연결했다. 실제 fill·SPI RTL→C 수신기로0/1/7행,2,048픽셀과95경우를 검증했고 raw 중단7경우도 통과했다. ARM 수신 구조체18,064바이트는 기존과 같다. 배포 SNES 소비·보드 연결·전체 ARM/FIT·실기는 미완료이며180 배포본을 유지한다. [전송 구현·남은 연결](../../docs/nes-wire181-contract.ko.md). 아래는 과거 기록이다.

NES181 수집기 후보의 행별 대체·다음 정상 행 복구를 구현했다. 결합14경우, 정상180 대비9,624단어, 보존3,328픽셀과 정상복구43,923셀 비교가 통과했다. 별도 실제 PPU RTL에서1,792픽셀 정렬도 통과했다. 배포 보드·전송·MCU·SNES 클라이언트와 전체 배치·실기는 미완료이며 새 ZIP 없이180을 유지한다. [수집기 구현·남은 연결](../../docs/nes-collect181-contract.ko.md). 아래는 과거 기록이다.

NES181: 영향을 받은 최대7행만 실제 PPU 픽셀로 보존하는 RTL과 SNES 부분 행 표시 방식을 구현했다. RTL9경우/2,560픽셀, RTL 덤프→SNES 양쪽 버퍼114,688픽셀 전체 비교가 통과했다. 합성 입력 기반 독립 경로이며 실제 수집기·전송·MCU·배포 클라이언트 연결과 전체 배치·실기는 아직 미완료다. 새 ZIP 없이180을 유지한다. [구현·남은 연결](../../docs/nes-render181-contract.ko.md). 아래는 과거 기록이다.

NES180 실기에서 raster08·compact82·185/224행의 거부2회와 오류0·224행 회복2회를 확인했다. 첫 레벨 영상 정지·월드맵 회복 관찰과 부합하며 진단 목적은 달성했다. 영상 정지 해결·약60fps는 미완료다. 최초 오류 위치와 변경된 단일 PPU 필드는 미측정이며, 다음은 공통 렌더링 중단·재개 및 fetch 행 완결성 구현이다. [실기 분석](../../docs/nes-game180-hardware01.ko.md). 아래는 과거 기록이다.

NES180 최소 기록 실기 시험판 준비 완료. 상태3비트로 첫 거부·정상 회복만 남기는 규격3이 실제 SPI·MCU·ARM 링크·단일 FIT·조건부 IO를 통과했다.15,061 LE/962 LAB, 실제 클록 setup +0.096ns, ARM 여유1,040바이트다. 숫자1→A 실기 로그를 기다리며 영상 정지 해결·60fps는 아직 미완료다. [설치·실기 안내](../../docs/nes-game180-ready.ko.md). 아래는 과거 기록이다.

NES180 기록 저장 공간 재사용 두 후보는 기능 검증을 통과했지만 채택되지 않았다. RAM 재사용은15,024 LE/962 LAB에서 실제 클록 setup −0.227ns, 오류 문맥 공유는967/963 LAB으로 실패했다. 새 ZIP 없이 배포178을 유지한다. 다음은 최초 거부·회복으로 관측 범위를 줄이며 실기 영상 정지·60fps는 미완료다. [검증·다음 작업](../../docs/nes-rejectstorage180-contract.ko.md). 아래는 과거 기록이다.

NES180 거부·회복 기록 후보는 실제 SPI·수집기 해제·MCU 판독/로그 검증을 통과했다. 첫 배치는964/963 LAB으로 실패했고, 축소 후보는15,043 LE/963 LAB에 배치됐지만 실제 클록 setup −0.092ns로 미채택이다. 새 ZIP 없이 배포178을 유지하며 실기 화면 정지·60fps는 미해결이다. [검증·남은 작업](../../docs/nes-reject180-contract.ko.md). 아래는 과거 기록이다.

# NES 개발 현황

NES179 조사: 실제 SMB3 기준 실행에서 숫자1→A→첫 레벨에 도달했다. 레벨100프레임의 행중 렌더링 중단·재개를 확인하고 배포178 raster의 거부/회복16경우와 합성 타일 누락/회복5경우를 검증했다. 실기 전체 오류·유일 원인·수정 완료는 미확정이며 배포178 유지, 새 ZIP 없음이다. [조사·다음 작업](../../docs/nes-level179-investigation.ko.md). 아래는 과거 기록이다.

NES178 실기: 월드맵 진입과 게임 오버 뒤 영상 회복을 확인했지만 첫 레벨에서는 영상이 정지했다. 표시 완료69회·마지막59.65초로 영구 정지보다 장면별 수집/표현 제약을 우선 조사한다. 레벨의 최초 거부 이유는 로그에 없어 아직 미확정이며, 지속 영상·60fps는 미완료다. [실기 분석](../../docs/nes-game178-hardware01.ko.md). 아래는 과거 기록이다.

NES178 실기 시험판 준비 완료: START 이후 mask18 거부를 수정한 FPGA·MCU·SNES 조합이 패킷 경계·전체 ARM·단일 FIT·조건부 IO 검사를 통과했다. 실제 게임 전환 후 영상 지속 여부는 사용자 실기로 확인하며 초기 끊김·60fps는 아직 미완료다. [실기 안내](../../docs/nes-game178-ready.ko.md). 아래는 과거 기록이다.

NES178: 목표 SMB3 일본판의 START 전환 후 mask18을 기존 수집기가 계속 거부하는 문제를 재현했다. 왼쪽8픽셀 클리핑을 보존하는 FPGA·MCU·SNES 후보와 경계/픽셀 검증을 완료했다. 전체 ARM 링크·FIT·실기 전이라 배포177 유지·새 ZIP 없음이며, 초기 끊김과60fps는 아직 미완료다. [검증·남은 작업](../../docs/nes-clip178-contract.ko.md). 아래는 과거 기록이다.

NES177 실기: START 화면 전환 때 영상만 정지한다는 사용자 관찰을 확인했다. 로그는27회 표시 완료·마지막12.48초 뒤 추가 BEGIN 없음, ABORT0이다. 종료 직전16클록에서 exporter IDLE/owned0/rawgeometry0/active1/fillbusy0/arbiterfault0이며 전송 적체 증거는 없다. 정상 수집 중간에도 가능한 표본이므로 반복 거부·결합 실패는 아직 구분하지 못했다. 연속 영상·60fps 미달성이며 새 패키지는 없다. [실기 결과·다음 작업](../../docs/nes-game177-hardware01.ko.md). 아래는 과거 기록이다.

NES177 실기 시험판 준비: 기존 history 하위22비트로 마지막 COMMIT 뒤 수집·소유권·전송·중재기 경계를 구분한다. 해제14위치 검증, 실제 클록 setup +0.055ns/hold +0.152ns, 조건부 IO, ARM 여유1040B, 최대TXT3925B 검사를 통과했다. 화면 정지 해결·60fps는 아직 미완료다. 무관한 로더 수정 없이 한 번의 FIT로 패키지를 만들었다. [검증·다음 작업](../../docs/nes-boundary177-contract.ko.md). 아래는 과거 기록이다.

NES176 회고 반영: 실제 SMB3 모델360프레임에서 즉시 해제349개·10프레임 보유35개 정상 후보와 기존 픽셀 일치를 확인했다. 두 장면의 전체5,493바이트 중 차이20바이트를 확인해 앞단 변경 전송의 근거를 마련했다. 공유 메모리 오류 연결6경우도 검증했지만 실기 정지 원인은 확정하지 않았다. 배포174 유지·새 ZIP 없음·60fps 미달성이며, 무관한 로더 미세FIT 반복을 멈춘다. [결과·수정 계획](../../docs/nes-video-review176.ko.md). 아래는 과거 기록이다.

NES175 READY·카운터 후보의 기능/SPI 검증은 통과했다. READY 경로 제거와 쓰기 대기 경로 +1.573ns 개선에도 전체 setup은 각각−0.048/−0.218ns로 실패해 두 후보 모두 미채택이며 새 ZIP은 없다. 배포174를 유지한다. [결과·다음 조건](../../docs/nes-ready175-contract.ko.md).

NES175는 느린 소비 후5회 전달·거부3회 후 회복을 연결 시험으로 확인했다. 실기 정지는 아직 미해결이며, 관측 후보 A4(-0.178ns)·A5(-1.114ns)는 타이밍 실패로 미채택이다. 새 ZIP 없이 검증된174를 보존한다. [검증 결과·다음 조건](../../docs/nes-lifecycle175-contract.ko.md).

NES174 실기:12회 표시 완료·마지막generation23/RUN3.81초 이후 영상만 정지했다. 사운드·조작은 정상으로 보인다는 보고이며 로그상60초 종료·메뉴 준비는 정상이다. 변환·전송/표시 확인 평균167.5ms, 연속 화면·60fps 미달성. 다음은 새 후보의 허용·해제·전달 경계다. [실기 분석](../../docs/nes-game174-hardware01.ko.md). 아래 시험판 준비 기록은 당시 상태로 보존한다.

NES174 실기 시험판 준비 완료: 실제 클록 setup +0.246ns / hold +0.156ns와 기존 외부 인터페이스 조건을 통과했다. 타일 간 비트평면 수정·묶음 전송을 새 FPGA/MCU에 함께 적용한다. 화면 정지 해결·60fps는 실기에서 확인할 차례다. [현재174 설치·시험 안내](../../docs/nes-game174-ready.ko.md).

NES174 로더의 명령 허용 상태를 분리해 전체 실제 클록 setup을 -0.807ns에서 -0.098ns로 개선했다. 기능·실제 SPI 연결은 통과했으나 타이밍은 여전히 실패다. 후속 속성 변경(-1.344ns)은 미채택이며 새 실기 ZIP은 없다. [타이밍 변경과 검증](../../docs/nes-legality174-contract.ko.md).

NES174에 타일 묶음 전송을 추가했다. SMB3 모델 장면의 패턴 요청18회→3회, 전체 요청45회→30회이며 실제 SNES 수신·229,376픽셀과 ARM 여유1040바이트를 확인했다. 실기 속도·60fps는 미확인이다. FPGA 타이밍-0.807ns와 전체 테이블 전송 비용이 남아 새 ZIP은 없다. [묶음 전송 검증과 다음 작업](../../docs/nes-batch174-contract.ko.md).

NES174 후보는 SMB3의 서로 다른 타일 비트평면을 보존하도록 수정했다. 모델frame24 수집과 frame24·25의114,688픽셀 비교, SPI·C 및 ARM 여유1024바이트 검증을 통과했다. FPGA 배치는 성공했지만 memory setup-0.807ns로 미채택이며 새 실기 ZIP은 없다. 실제 정지 해결·60fps는 미확인이고 반복 전송 비용도 남았다. [174 검증과 미완료 작업](../../docs/nes-cross174-contract.ko.md).

NES173 실기: RUN 시작 후5.79초까지 표시 ACK16회 뒤 추가 완료가 멈췄다. 변환/패턴 전송910ms와 테이블·SEAL/ACK2340ms, 합계 회당 약203ms로 초기 처리량도60fps 목표에 크게 못 미친다. 정상60초 종료·STOP/메뉴 준비 확인. 정지 원인 미확정, 같은173 재시험 없이 타일 간 plane 표현과 반복 전송/왕복 개선으로 진행한다. [173 실기 결과](../../docs/nes-game173-hardware01.ko.md).

NES173 실기 시간 측정판을 준비했다. 172 FPGA 전체 바이트·표시 프로그램을 유지하고 MCU에 수신 대기·변환/전송·표시 ACK 누적 시간과 마지막 표시 완료 시각을 추가했다. 화면 정지와 약60fps 연속 표시 목표는 아직 미달성이다. [173 실기 안내](../../docs/nes-game173-ready.ko.md) · [측정 범위](../../docs/nes-profile173-contract.ko.md).

NES172 실기에서 표시 준비와 14회 표시 완료 응답을 통과했지만 이후 화면이 멈췄다. 버튼·스테이지 음악은 계속 반응했고 정상 약60초 한도로 메뉴에 복귀했다. BEGIN/END/COMMIT 각14, ABORT0, 마지막 generation27이다.170의 수집 시간 초과와 달리 다음 BEGIN이 수신되지 않은 경계이며, 초반도 끊겼으며 약60fps 연속 표시 목표는 미달성이다. [172 실기 결과](../../docs/nes-game172-hardware01.ko.md).

현재164 실기: **검정 구간 제거 통과·사운드 정상으로 보임, 심한 갱신 지연으로 정상 플레이 미달성**. 다음은 영상 전송량·갱신 지연 개선이며, DOWN 유지는 이번 미시험입니다. [164 실기 결과](../../analysis/GAME164-HARDWARE-RESULT.ko.md).

이전151 실기: **SMB3 제목·캐릭터 표시와 메뉴 복귀 성공, PPU 읽기 오류로 조기 종료**. 정상 플레이·전체 버튼 입력은 미완료입니다. [151 실기 결과](../../analysis/GAME151-HARDWARE-RESULT.ko.md).

[현재 인계](HANDOFF.ko.md) · [127 결과](../../analysis/LOADER127-RESULT.ko.md)

## 이전 단계별 근거

- [070 결과](../../analysis/CF68-SESSION-RESULT.ko.md) · [전체 CF68 계약·재현](../../docs/nes-cf68-session-contract.md). 검증후보070/MCU069/FPGA068,설치 불가.

- [069 결과](../../analysis/CF68-MCU-RESULT.ko.md) · [CF68 MCU 계약·재현](../../docs/nes-cf68-mcu-contract.md). MCU069/FPGA068, 설치 불가.

- [068 결과](../../analysis/DIAG-SAFETY-RESULT.ko.md) · [초기 대기/외부 예산 계약](../../docs/nes-diag-safety-contract.md). FPGA 후보CF68,설치 불가.

- [067 결과](../../analysis/DIAG-MEMORY-RESULT.ko.md) · [계약/재현](../../docs/nes-diag-memory-contract.md) · [다음 Sol 작업 상세 인계](../../docs/development/NES-067-SOL-HANDOFF.ko.md). 이전067 후보CF67, 설치 불가.

- [066 파일 쌍 결과](../../analysis/PAIR-PREFLIGHT-RESULT.ko.md) · [계약·재현·실기 시험표](../../docs/nes-pair-preflight-contract.md) — 오프라인 준비, 설치 승인 아님.

- [065 메뉴 복귀 결과](../../analysis/MENU-RETURN-RESULT.ko.md) · [계약·재현](../../docs/nes-menu-return-contract.md) — compile-only, 설치 후보 아님.

- [064 하위 종료·오류 결과](../../analysis/DIAG-RECOVERY-RESULT.ko.md) · [계약·재현](../../docs/nes-diag-recovery-contract.md) — compile-only, 설치 후보 아님.

- [063 전체 세션 결과](../../analysis/BOARD-SESSION-RESULT.ko.md) · [계약·재현](../../docs/nes-board-session-contract.md) — 디지털 검증, 설치 후보 아님.

- [062 메뉴 연결 결과](../../analysis/MENU-DIAGNOSTIC-RESULT.ko.md) · [계약·재현](../../docs/nes-menu-diagnostic-contract.md) — 설치 후보 아님.

- [실기 진입 전 공정 점검·진척도·모델 운영 가이드](../../docs/development/NES-HARDWARE-READINESS-REVIEW.ko.md) — 현재096 요약과 과거 항목별 점검표. 최초061 점검과 이후 결과를 구분한다.

- [061 결과](../../analysis/BOARD-DIAGNOSTIC-RESULT.ko.md) · [물리 진단 계약](../../docs/nes-board-diagnostic-contract.md)

- [060 결과](../../analysis/SD-READBACK-RESULT.ko.md) · [SD 읽기 비교 계약](../../docs/nes-sd-readback-contract.md)

- [059 결과](../../analysis/SPI-READBACK-RESULT.ko.md) · [SPI 읽기 확인 계약](../../docs/nes-spi-readback-contract.md)

- [058 결과](../../analysis/ROM-READBACK-PORT-RESULT.ko.md) · [공유 읽기 포트 계약](../../docs/nes-rom-readback-port-contract.md)

- [057 결과](../../analysis/ROM-GEOMETRY-RESULT.ko.md) · [형상 연결 계약](../../docs/nes-rom-geometry-contract.md) · [readback 후속 설계](../../docs/nes-rom-readback-plan.md)

- [056 결과](../../analysis/MCU-LOADER-RESULT.ko.md) · [STM32 적재 계약](../../docs/nes-mcu-loader-contract.md)
- [055 결과](../../analysis/SPI-LIVE-RESULT.ko.md) · [SPI 실제 코어 계약](../../docs/nes-spi-live-contract.md)
- [054 결과](../../analysis/SPI-BOOT-RESULT.ko.md) · [SPI 계약](../../docs/nes-spi-boot-contract.md)
- [현재 인계와 다음 작업](HANDOFF.ko.md)
- [공개 재현 시험과 로컬 의존성](REPRODUCING.ko.md)
- [단계별 진전](MILESTONES.ko.md)
- [실기 044 관측](../../analysis/H1-HARDWARE-044-RESULT.ko.md), [053 결과](../../analysis/ROM-BOOT-RESULT.ko.md), [053 계약](../../docs/nes-rom-boot-contract.md)
- [출처·고정 upstream·보류 파일](../../analysis/source-lock.json), [공개 구현 해시](publication-sources.json)
- [다른 코어에도 적용할 작업 방식](../../docs/development/MILESTONE-WORKFLOW.ko.md)

구현은 `src/nes`, 시험은 `tests/nes-functional`, 자체 SNES 진단 생성기는 `snes/video_probe`, 도구는 `tools/nes_*`·`tools/run_nes_*`에 있다. 기존 GBC 소스를 이동하거나 새 NES 작업에 맞춰 변경하지 않았다.

기존 문서에 반복 누적된 과거 상태는 [이전 README 이력](history/README-053.md)과 [이전 인계 이력](history/HANDOFF-053.ko.md)에 보존한다. 이력 속 ‘현재/다음’ 표현은 당시 기준이며, 현재 판단은 이 문서와 위 인계 문서를 따른다.
