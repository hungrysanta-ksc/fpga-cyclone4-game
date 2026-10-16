# NES209 큐 연결과 직접 전송 실기판

## 작업 의미

188~208에서 준비한 직접 타일 전송 경로를 실기 시험판으로 묶는다.208의 실제 C·RTL·65816 결합에서 모델로 남았던 큐는 새 명령의 실제 packet/ACK를 사용해 선택된207 RTL에서 재생한다. 제품의 데이터 경로를 다시 설계하지 않고, 검증된 배치와 런타임을 유지해 첫 레벨 스크롤에서 측정할 단계로 이동한다. 성능 향상이나60fps 달성은 아직 실측하지 않았다.

## 제한된 결합 검증

SELECT **test02**.208 normal86/partial31 packet과 actual65816 ACK117개를 사용한다. SPI status 타이밍은208에서 기록하지 않았으므로 이를 재현했다고 주장하지 않는다. BEGIN/SEAL barrier를 유지하며 최대4credit로 다시 묶어 정상19회/부분7회 full queue를 만들고 실제207 `nes_sink_spi165/bridge/bus`를 통과시킨다. 정상345event/20250check, 부분125event/12979check가 통과한다. 부분 모드의 새 E9 중단 자체는208 증거이며209는 그때 완료된 큐 packet을 재생한다.

선택된 큐/reset/bus4개 RTL은184 route02와 동일하다. 실제 sink가6040~6050 descriptor,400800~400fff aperture,700000 세이브 주소를 점유하지 않는지 검사한다. 최상위 SNES/MISO mux의 assign7개를 원문 그대로 추출하여 버스64조합+SPI256조합을 확인한다. 동시 선택 때 MISO를 해제하고 SNES 읽기·쓰기 소유권을 유지한다. peer 신호는 fixture이며 full-board/공통 clock/경쟁·metastability/게임FPS 검증이 아니다. 기존207 전체FIT가 최상위 연결의 합성을 검증했고,208은 직접 경로의 실제 consume/ACK/retire를 검증했다.

test01은 새 시험용 mux의 timescale 선언 누락으로 시뮬레이터 load가 실패했다. 생산 RTL은 바꾸지 않았고 test02에서 해결했다.

## ARM·ROM 짝

SELECT **arm01/check02/report02/asm01/romcheck02**.203 전체 소스1424개를 복사하고 메뉴·로그·VERSION3개만 바꿨다. 실행명은 NES GAME 209.nh1, ROM game209.nes, FPGA fpga_n209.bi3, 로그 progress209/game-last209다. 종료 formatter에 plan_error/plan_sent/plan_end만 추가한다. RUN/SD/USB/사운드/입력/복원 코드는 그대로다.

전체 ARM203744B, static26872B, RUN 상한28784B, IRQ508B, 잔여9260B로 기존203과 메모리 상한이 같다.1024B 최소 여유 조건을 유지한다. 최대 폭16입력·16history 로그4047/4096B 통과. report01은 sandbox GCC DLL 실행 제약으로 실행 전 실패했고 승인된 실행 환경의 report02를 선택했다. check01은 의도한209 메뉴 식별자 변경을 기존 hash 비교가 거부했다. check02는 이 변경과 새 로그 블록만 역변환하여203 원본 일치를 확인하고 나머지 플랫폼/링크 검사를 유지한다.

선택된207 mapfit02를 새 ASCII 폴더로 복제해 ASM/CPF만 수행한다. 새 MAP/FIT/STA/MIF 변경은 없다. assembly 시 원본 source·routing/report 일치를 확인하고 encoder/decode roundtrip도 검사한다. EDA는 뒤이어 ROM 확인용으로만 수행한다. 해당 FIT DB에서 생성되는 출력은 default/slow85/fast0의3개다. 오래된170 checker는4개를 기대하여 romcheck01이 거부됐으므로, 실제 생성되는 세 이름을 명시한209 checker로3×4096B atom 상수를 확인한다. 이는 새로운3corner 타이밍 분석이 아니다.207의 별도3corner 관련 setup+0.173/strict+0.041/hold+0.156ns와 조건부IO 증거를 재사용한다.

ROM195의 compact4096B와 실제32768B client projection,208의 actual65816 ROM,209 FPGA의 post-fit atom이 모두 일치해야 패키징한다. 생산 RTL은207그대로이며15260LE/962LAB/47M9K,148LE/1LAB 여유를 유지한다. 전체CDC/MTBF/전기 signoff를 주장하지 않는다.

첫 패키징 검사는 EDA 이후 QSF를 raw prefix로 비교하여 거부됐다. 실제 diff는 줄바꿈 정규화, LAST_QUARTUS_VERSION의 Lite→Standard 표기 및 EDA 출력 설정3개뿐이었다. ASM 시점의 원본 일치 검사는 이미 통과했으며, 후속 패키징 검사는 이 정확한 변환만 허용하고 나머지 모든 설정을 비교한다. 패키지 생성 전 거부이므로 잘못된 ZIP은 생성하지 않았다.

## 배포·다음 작업

패키지는 firmware와fpga_n209를 짝지으며186의 제공 ROM·메뉴·기본 코어·GBC164 복원 파일을 그대로 보존한다. 새 시험판 준비 완료는 실기 통과를 뜻하지 않는다. 기존186과 원본 archive24개를 유지하며 세이브 SRAM은 사용하지 않는다.

다음은 [NES209 실기 안내](nes-game209-ready.ko.md)에 따라 숫자1+A→RIGHT+B 유지/A press-release의 실제 스크롤을 관찰하고 두 로그를 수집하는 것이다. 현재 collected_runs는 비어 있다. 기존 전체60초 ACK 평균이나 합성 repeated-tile 결과로60fps를 선언하지 않는다. 로그는 aggregate/마지막 전송 상태이며 scene별 p95/physical cache hit를 모두 측정하는 계측은 아니다. 우선 이 실기 결과로 다음 병목을 좁히고 필요한 측정만 추가한다. AV약60fps→장기play/error-reset로그→입력 유지, MMC4/5·CHR-RAM·state/mute/frameskip 예산을 유지한다.
