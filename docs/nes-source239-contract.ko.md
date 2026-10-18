# NES239: base RAM 분할과 인코더 상태·연산 공유

## 작업 의미

60fps 입력 증분 생성 경로를 현재 FPGA에 배치하기 위한 자원 개선이다.238은 전체 조합 논리 수를 한도 아래로 줄였지만 실제 FIT가15945LE/1014LAB와56M9K를 요구해 실패했다.239는 base RAM의 깊이 낭비와 동시에 필요하지 않은 저장·연산을 줄인다. codec·전송량·필드 폭·오류 검사는 유지한다.

## 변경과 수명 규약

- base6144×8 하나를4096×8과2048×8로 나눴다. 두 RAM을 같은 edge에 읽고 주소 bit12를 함께 등록한 뒤 결과를 선택한다. 추가 read cycle은 없다. write는 현재 주소의 bank 하나에만 적용하며 RAM payload는 reset하지 않는다. 실제 사용 범위0..5740,부분 실패 시 base 전체 무효화,common reset 후 cold 초기화 규약은 같다.
- 현재 serial32 저장을 제거했다. start에서 요구 serial이 승인된 base serial+1임을 검증하고,base serial은 같은 generation의 최종 source ACK 전에는 바뀌지 않는다. header와 ACK commit은 같은32bit 합을 사용한다. serial0/FFFFFFFF 거부와 epoch 검사는 유지한다. 이는 SNES 최종 displayACK로 승격하는 변경이 아니다.
- geometry cursor와 raw cursor는 사용 시점이 겹치지 않는다. geometry END를 완전히 송신한 뒤 RAWSTART에서 같은13bit cursor를0으로 바꿔 raw에 사용한다. raw 단계에서는 base write가 허용되지 않는다. 다음 frame start도 cursor를0으로 초기화한다. query235의 독립 위치와 encoder 위치 비교는 그대로다.
- geometry span/expanded 누적은 같은16bit counter와 덧셈 경로를 공유하도록 정리했다. literal/행 이동/raster/저비용 record가 만드는 증가량만 선택한다. bit 폭이나 wire 규약은 줄이지 않았다.

query reader의 독립 cursor를 단순히 encoder cursor에 묶어 오류 비교를 항상 참으로 만드는 변경은 하지 않았다. 조회·holding 전체 통합은 추가 설계가 필요하다. 기존SPI235,query235,collector,save SRAM,게임 CPU/APU/mapper는 바꾸지 않는다.

## 검증

동일한 관측 SMB3 첫 레벨 스크롤905..975를 actual frame201→query235→encoder239→SPI235 핀→actual C234/231로 전달한다.234 record는 비교 oracle이며 FPGA 입력이 아니다. 전체71프레임의 wire/record 경계,C 출력355파일과238 test01의 cycleCSV를 비교한다.

독립 합성 시험은 기존20개 자료(seed237)를 그대로 유지하고4개 serial 경계 frame을 추가했다. 각 정상 완료에서 두 RAM bank를 이어 붙인5741B를 입력과 비교한다. 큰 serial 시험은 수십억 frame을 재생한 것이 아니라 검증된 base 내용을 유지한 상태에서 lifetime counter를 직접 seed한 경계 시험이다.

추가 serial은00000100/00010000/80000000/FFFFFFFE다. 첫 추가 frame은 start 후 입력 serial을12345678로 바꿔도 승인된 header/commit이 유지되는지 확인한다. base serialFFFFFFFE 다음의 금지된FFFFFFFF 요청도 별도로 거부한다. 기존16오류·중단 검사를 포함해24정상+17경계 총41검사다. 정상 검사에는 generation wrap,양방향 행 이동,raster 반복/희소/0,literal240B,patch0..7가 포함된다.

PPU stimulus,host PREPARED ACK, C ROM/표시 callback은 fixture다. 실제 전체 게임 CPU/ARM/SNES 최종 표시/실기60fps 검증이 아니다. 기존235 SPI 경계와232 소비기 결과는 변경 없이 재사용한다.

최종71프레임의2229record/350block/62967payload byte와record 경계가 일치했고,C 출력355파일,4,066,624 reference checks,1459 C fault/restart 검사를 통과했다.24정상+17경계 검사도 모두 통과했다. 전체71프레임의 `cycles.csv`는238 test01과 byte-exact다.

동일907..975 비교 창에서 입력 시작→PREPARED 최대137913cycles(6.268698ms),조회·준비 최대39779cycles(1.808115ms),다른 은행 봉인 중50208B 쓰기가 유지됐다. source45.454ns,host11.904ns,SPI2.625MHz 모델이다. 실제 ARM 계산·다른 SPI 명령·SNES DMA/표시는 제외돼 있으며 ACK 대기는 마지막 block 전송도 포함한다. 전체60fps 증명이나 공유 SPI 예산의 대체값이 아니다.

## 전체 보드 경계와 남은 작업

238과 동일한 source 교체 경계에서 MAP/FIT를 실행한다. 제거된 옛 source 관련216개 SDC 행 정리는238 board01과 byte-exact이며 새 예외·clock 완화·seed 탐색은 없다. FIT 자원 표는 실제 보고된 요구량으로 기록하고 실패한 결과를 배치·timing 승인으로 쓰지 않는다.

선택은 test01/guards01/board01/source01이며 전체 보드 MAP/FIT는 각각 한 번 실행했다.

| 항목 |238|239|
|---|---:|---:|
| encoder 조합/FF |1519/487|1395/443|
| source 계층 조합/FF |2211/1052|2091/1008|
| 전체 조합/FF |15115/8655|14977/8611|
| MAP 추정LE |19990|19821|
| 실패한 FIT의 LE 요구량 |15945|15930|
| 실패한 FIT의 LAB 요구량 |1014|1006|
| M9K 요구량 |56|54|

메모리 표에서 base_lo4096×8은4개,base_hi2048×8은2개 M9K를 요구한다.238의 monolithic8개보다2개를 회수했다. 같은 논리 저장 용량316000bit를 유지하며 FPGA 메모리의 낭비를 줄인 결과다. 새 계산상의 여유가 아니라 FIT의 block 요구량에서 확인했다. 전체 배치에는 실패했으므로 RAM 위치는 여전히Unassigned이며 timing 승인은 아니다.

FIT는 **Error170012:1006LAB 필요/963LAB 한도**로 실패했다. LE도15930/15408이므로 아직522LE·43LAB이 부족하며 mapper·타이밍 여유는 별도다.

전체 조합138개/FF44개 감소에 비해 FIT LE 요구량은15개만 줄었다. 보고서의 combinational+register는7825→7658,register-only는830→953,combinational-only는7290→7319다. 따라서 조합 논리 수 감소를 같은 크기의 최종 배치 절감으로 간주하면 안 된다. 이 수치만으로 특정 clock enable나 reset이 원인이라고 단정할 수도 없다.

다음은 작은 덧셈 하나씩의 최적화보다 **제어·데이터 경로와 register 결합을 함께 바꾸는 구조**를 우선한다. 회수한 M9K 내에서 compact control을 저장하는 후보도 검토할 수 있지만,추가 RAM·제어 decode·준비 cycle·향후 mapper 여유를 함께 평가해야 한다. 새2개를 모두 사용해도 된다고 승인한 결과는 아니다. 현재 단계의 목표는 source 교체 범위와 기존 여유를 보존하는 것이며522LE만 줄여 경계에 맞추는 것이 아니다.

추가 회로 축소와 mapper 여유,새 입력 전체 ARM RUN/IRQ,host/NES fault 영역과 최초 오류 보존,최종 source lease/displayACK/retire,새 CDC/IO/STA,232의5개 VBlank 초과 burst가 남아 있다. 새 메모리 여유를 사용할 때도 단순 용량 산술이 아닌 추론·FIT 보고서로 확인해야 한다. 생산227/GBC164/save SRAM과 기존 봉인 자료를 유지한다.
