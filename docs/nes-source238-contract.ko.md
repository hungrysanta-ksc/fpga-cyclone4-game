# NES238: 전송 규약과 처리 시간을 유지한 인코더 회로 축소

## 작업 의미

60fps를 위한 입력 증분 생성기를 기존 FPGA에 넣기 위한 구조 변경이다.237에서 실제 스크롤 자료의 생성·전송·수신 정확성은 확인했으나 전체 보드가 조합 자원 한도를 초과했다.238은 literal/양방향 행 이동/raster XOR/raw와 모든 CRC·serial·epoch 필드를 유지하면서 회로 제어와 RAM 주소 계산을 줄인다. 기능을 빼거나 전송량을 늘려 자원 문제를 옮기는 방법은 사용하지 않는다.

## 구조 변경

237의 네 복귀 변수는 각각 전체 상태 번호7bit를 저장하고 그 값을 다음 상태에 직접 넣었다.238에서는 송신3bit,복사2bit,flush3bit,literal2bit의 독립 continuation tag를 저장한다. 각 분기는 상수 상태로만 이동한다. main FSM을 합성기가 분석할 수 있게 만드는 변경이며 실제 추출 여부는 전체 보드 MAP 보고서로 확인한다. enum bit 수 감소를 실제 FF 절감량이라고 단정하지 않는다.

작업 RAM은 같은1024×8 true dual-port 한 개를 사용한다. 다음 배치로 주소 상수 덧셈을 bit 결합으로 바꾼다.

| 영역 | 주소 | payload 크기 |
|---|---|---:|
| 이전 행 |0..65|66B|
| 현재 행 |128..193|66B|
| literal |256..495|240B|
| 송신 대기 record |512..754|243B|
| 저비용 raster |768..779|12B|
| raster mask |784..791|8B|

총 payload635B는 동일하며 주소 범위만792B로 정렬한다. 두 포트 process와 RAM reset 금지 규약은 유지한다. 이전 화면 base6144×8도 그대로다. SRAM save 영역은 사용하지 않는다. 시험은 동일 주소 동시 쓰기와792B/5741B 쓰기 경계를 검사하고 모든 정상 완료에서 base5741B 전체를 입력과 비교한다.

복사 작업은 두 시작 주소에 매번 index를 더하는 대신 read/write 주소를 순차 증가시키고 남은 길이를 감소시킨다. read→write 두 cycle과 복사 순서는 유지한다. header의 가변 shift는 명시적 byte 선택으로 바꾼다. 기존20합성 프레임의 난수 seed237을 그대로 사용해 후보 이름 변경으로 비교 자료가 바뀌지 않게 했다.

## 검증 범위

actual frame201→query235→encoder238/base·scratch RAM→SPI235 실제 핀→actual C234/231을 동일한905..975 스크롤71프레임으로 비교한다.234 record는 oracle이며 입력으로 공급하지 않는다. 기록된 PPU stimulus,host PREPARED ACK,C ROM/표시 callback은 fixture다. 전체 게임 CPU,실제 ARM 실행 또는 SNES 최종 표시 ACK를 함께 실행한 시험은 아니다.

20합성 화면과16오류·중단 조건은237과 동일하며 generation wrap,양방향 행 이동,반복·희소·0 raster,240B literal,patch0..7,serial/epoch/offset 오류,lease 상실,부분 abort,이른/잘못된/reject ACK,raw 오류,응답 누락 후 abort,cold replay를 검사한다. 기존235 SPI 경계 시험과232 소비기 결과는 보존·재사용한다.

전체 보드 resource 후보는237과 같은 교체 경계와 glue를 쓴다. 제거된 기존 source 인스턴스 관련216개 SDC 행만 삭제한 파일은237 board03과 byte-exact다. 새 false path,clock 완화,timeout 확대,seed 탐색은 없다. 새 source의 CDC/IO/STA를 이 기존 SDC만으로 승인하지 않는다.

71프레임의2229record/350block/62967payload byte,record 경계,C 출력355파일이 전부 일치했다.4,066,624 reference checks와1459 C fault/restart 검사,별도36 encoder 검사가 통과했다. 전체 `cycles.csv`도237 test04와 byte-exact다.

동일 비교 창907..975에서 입력 시작→PREPARED 최대137913cycles(6.268698ms),조회·준비 최대39779cycles(1.808115ms),다른 은행이 봉인된 동안50208B 쓰기가 유지됐다. source45.454ns,host11.904ns,SPI2.625MHz 모델 수치다. `ackwait`는 마지막 block 전송을 포함하며 이 시간에는 실제 ARM 계산·다른 SPI·SNES 표시가 없다. 이 구조 변경으로 실기 FPS가 올랐다고 주장하지 않는다.

## 전체 보드 측정 결과와 메모리 산술 정정

선택은 test01/guards01/board01/source01이다. 변경 구조에 대해 전체 보드 MAP/FIT를 각각 한 번 실행했다. MAP 보고서에서 encoder의 main state와 일부 continuation이 상태 머신으로 추출됐음을 확인했다. 아래 값은 동일 전체 보드 경계의 보고값이며 개별 변경 하나의 기여도로 분해하지 않는다.

| 항목 |237|238|
|---|---:|---:|
| encoder 조합 논리 |2069|1519|
| encoder FF |451|487|
| source 계층 조합 논리 |2782|2211|
| source 계층 FF |1016|1052|
| 전체 조합 논리 |15664|15115|
| 전체 FF |8619|8655|
| MAP 추정 LE |20539|19990|

encoder 조합550개(26.58%) 감소,전체 조합549개 감소다. FSM 추출로 FF는36개 늘었다. 전체 조합은15408 이하가 됐으나 **FIT Error170012:1014LAB 필요/963LAB 한도**로 배치에는 실패했다. 실패한 FIT 자원 요구량은15945LE/15408이다.537LE와51LAB 부족은 현재 최소 부족량이며 향후 mapper·배선·타이밍 여유를 포함하지 않는다. 전체 배치 성공이나 최종 timing 결과가 아니다.

이번 FIT 메모리 표에서 **56/56 M9K 사용 요구**가 확인됐다.6144×8 base는 용량 산술6개와 달리 실제 mapping에서8개를 요구한다. scratch와SPI는 각각1개다. 따라서237의54/56 산술을 여유2개라는 설계 근거로 사용할 수 없다. 기존 봉인 자료는 수정하지 않고 여기서 정정한다. 각 RAM의 location은 Unassigned이며 배치 완료값이 아니다.

다음 구조 변경은 query/cursor/holding 중복과 연산·복사 제어의 공유를 함께 줄이고,base를 명시적인4096+2048 또는1024 단위 bank로 나누는 방식을 검토한다.6개 M9K로 추론되는지,bank 선택이 같은1cycle read와 원자적 base 무효화를 지키는지 실제 측정해야 한다. 새로운 control ROM을 추가할 여유가 있다고 가정하지 않는다. 단순537LE 감소가 아니라 기존 source footprint와 mapper 여유를 보존하는 목표를 유지한다. query reader 하나를 합치는 것만으로 충분하다고 보지 않는다.

## 남아 있는 조건

실제 입력 parser를 포함한 전체 ARM RUN/IRQ 여유,query와 encoder cursor/holding의 추가 공유,host/NES fault 영역과 최초 오류 보존,source lease→최종 displayACK→retire,새 source CDC/IO/STA,232의5개 VBlank 초과 burst가 남아 있다.233의1616B ARM 여유는 새 입력 경로 승인값이 아니다. D2 POP,D3 PREPARED와 최종 화면 표시 commit도 서로 다르다.

전체 자원·타이밍과 runtime 연결을 통과한 뒤 paired 실기판을 만든다. 생산227,GBC164,save SRAM과 기존 봉인 자료는 변경하지 않으며 이번 결과를 물리60fps 또는 mapper 확장 여유 확보로 해석하지 않는다.
