# NES236: 누락된 회수 자원 정정과 같은 스크롤의 경로 선택

PR127에 이어 기록한다.235의 두 endpoint 자체는 변경하지 않았다. 실제 교체 범위를 다시 합성하고, 같은71개 스크롤 프레임으로 단순화 후보와 병렬 전송 대안의 비용을 비교했다. **기존 행 이동+raster 증분 A를 유지하되 전체 생성기의 자원·시간 gate를 먼저 통과시키는 방향을 선택한다.** 아직 실기용 생성기 구현 완료나60fps 승인은 아니다.

## 작업 의미

잘못 잡은 자원 범위 때문에 유효한 경로를 포기하거나, 회로를 단순하게 만들려고 필요한 전송 절감을 없애는 일을 피하기 위한 설계 결정이다. 이번 변경은 회로 기능을 추가하는 실기판이 아니라, 다음 생성기 구현의 정확한 교체 범위·예산·대안 탈락 조건을 확정하는 작업이다.

##235 자원 계산 정정

실제224 `nes_live_joint.sv`는 exporter와 SPI 사이에96bit `native_records` mailbox, 역방향17bit `native_prepared` mailbox를 둔다.235의512B dual-clock SPI와 내부 descriptor/ACK mailbox가 이 둘의 역할도 대체한다. 지난235의1282LE 계산은 이 회수 항목을 빠뜨렸다.

| 기존 실제 FIT 항목 | LE | FF |
|---|---:|---:|
| native_export |644|225|
| native_records |219|206|
| native_prepared |50|48|
| native_spi |479|304|
| 교체 대상 합계 |1392|783|

기존 여유159LE를 더하면 **교체 가능한 산술 상한은1551LE**다.235의 개별 MAP 합1122를 빼는 단순 계산은429이며160이 아니다. 기존 native_spi_release의 작은 reset 회로는 추가 회수분으로 세지 않았다. 다른 plan/tile mailbox, capture lease,loader/ROM arbitration은 이 교체 범위에 포함하지 않는다.

같은 top port/장치/Quartus 조건으로 양쪽 경로를 각각 한 번 MAP했다. old는 실제 exporter203+records165+prepared165+SPI165+host reset release이고, new는 query235+SPI235다. **new encoder 입력/출력은 외부 포트로 남겨 최적화 제거를 막았으며 encoder 자체를 포함하지 않는다.**

| 동일 교체 범위 MAP | LE | FF | RAM |
|---|---:|---:|---|
| old |1591|780|256×8 M9K 하나|
| new endpoints |1121|581|512×8 M9K 하나|

차이는470LE다. old MAP1591과 실제 board FIT1392가 다른 것 자체가 문맥별 최적화·배치 차이를 보여준다. **470+기존 여유를 확정 가용 공간으로 사용하지 않는다.** 실제 old FIT1392+여유159−new MAP1121=430도 혼합 산술이며 whole-board 자원 보장이 아니다.

추가 생성기의 초기 설계 목표는 원래 여유159LE를 쓰지 않는 교체 범위1392LE 이내로 잡는다. 현재 endpoint1121 기준 추가 약271LE라는 도전적인 산술 목표다.430을 다 쓰는 안은 여유가0이므로 목표치가 아니다. 실제 FIT의 LE/LAB/RAM/타이밍과 mapper 확장 여유를 따로 확인한다.159LE 보존만으로 MMC4/MMC5 추가가 가능하다고 보장하지 않는다.

## SPI 제어 공유 검토

신호 이름이 같은 SPI endpoint 전체를 하나로 합치는 작업부터 시작하지 않는다. 현재 source/plan/sink는 host clock을 사용하지만 session reset·RUN admission이 같지 않다. 특히 sink는 SS와 SNES write가 idle인 것을 확인한 뒤 session을 허용한다. screen status는 전원/PLL reset 수명이고, observer는 SNES clock에서 STOP 이후 정보도 유지하며, ROM loader는 memory clock이다.

따라서 bit counter/command 레지스터가 비슷하다는 이유로 동기화기와 상태를 공유하면 중간 transaction 재진입과 STOP 경계를 바꿀 수 있다. 글로벌 parser 공유의 순절감은 입증하지 않았고 이번 자원 회수에 넣지 않았다. 이미 검증한235의 source 내부 descriptor/ACK 소유권을 유지하면서, **불필요해진 기존96bit/17bit 전달 회로를 교체 범위에 포함하는 것**이 우선이다.

## 단순화해도 되는가: 같은71프레임 비교

905..975를 세 후보 모두 실제 C234 receiver→231 planner/sink에 넣었다. 각 후보의 geometry/raw/metadata/packet/plan355파일,4,066,624 reference checks가 기존234와 같으며 기존 C fault/restart1459검사도 통과했다.213프레임분의 C 실행이지 새로운 게임 실기 자료가 아니다. 두 cold frame 뒤 warm69개를 동일하게 비교한다.

| 후보 | 공유 SPI ready4 모델 최대 | wire 시간 최대 |5468.75B 초과/warm69|
|---|---:|---:|---:|
| 기존234 행 이동+raster XOR+literal |5341B|16.277ms|0|
| 행 이동+literal, raster XOR 제거 |6922B|21.096ms|8|
| literal만, 짧은 gap 결합 |7616B|23.211ms|22|

full 후보의 기록은 기존234 stream과 byte-exact이다. 다른 두 후보는 정확한 동일 geometry를 복원하는 분석용 대안으로, 생산 C/FPGA를 바꾸지 않았다. raw와 출력 패킷은 동일하므로 source payload와 whole-record248B block 수 차이만 기존 shared SPI 모델에 반영했다.

이 결과는 모든 압축 방법의 이론적 최저값이 아니다. **검토한 단순화 두 안을 그대로 선택하면 전송 예산을 잃는다**는 판단이다. 단순 literal/raster 생략으로 LE를 맞추는 방향은 선택하지 않는다. ready4는 실제 poll/CPU/gap/stall 상한이 아니며 full의 ready1 최대5941B/2프레임 초과는 남아 있다.0개 초과를60fps 증명으로 읽지 않는다.235의 source overlap도 실제 encoder 준비 지연의 검증이 아니다.

## 병렬 전송 B에서 실제로 사라지는 바이트

기존 aperture188은 FPGA→SNES 경로다. 현재 geometry를 읽고 SNES map/OAM/raster로 바꾸는 곳은 ARM이다. ARM이 만든 같은 metadata를 SPI로 FPGA에 다시 넣고 SNES가 병렬로 읽는다면 ARM→FPGA 바이트는 사라지지 않는다.

출력 metadata 생성·전달·상태 확인을 전부 공짜로 가정해도, 기존 입력 geometry payload만 warm 프레임당 **최소19.078ms/평균19.307ms/최대19.785ms**다.69프레임 모두16.67ms를 넘는다. 이 값에는 D0/D1 CRC/D2와 tile plan,ARM 계산,SNES 소비를 더하지 않았다. 따라서 **입력은227 방식 그대로 두고 출력만 병렬화하는 B는 탈락**이다.

입력·변환까지 병렬 경로로 옮기는 B 전체가 불가능하다는 결론은 아니다. 그 경우에는 ARM planner를 FPGA/SNES로 옮기는 실제 구현·자원·CPU 시간,또는 ARM이 자료를 받는 새로운 입증된 연결이 필요하다. 기존 tile DMA의 성공을 geometry 전체 변환의 증거로 재사용할 수 없다. 이번에 새로운 ARM 병렬 하드웨어 연결을 가정하지 않는다.

## 다음 구현 범위

1. A의 fused source 생성기를 하나의 교체 경로로 만든다. query235의 cursor/holding 상태를 무조건 복사하지 않고, base5741B/6M9K와 하나의 scratch M9K 포트에서 순서대로 비교한다. map row pair132B, literal240B, cheap-raster12B,mask8B,pending record243B라는234 보수적635B 범위를 유지한다. session/header 등을 scratch의 남은 공간에 둘 수 있는지는 주소·수명·포트로 입증하며 FF 감소를 미리 합격 처리하지 않는다.
2. 행 이동/raster XOR를 유지하고 두 은행 SPI235에 완전한 record를 공급한다. CRC/token을 제거하거나 epoch/serial/END-count를 축소하지 않는다. partial base 갱신 실패는 common STOP/reset에서 sender·receiver 양쪽 기준을 폐기한다. raw patch는 매 frame 요구 길이만큼 그대로 전달한다.
3. 같은71프레임에서 **실제 query→encoder/base RAM→SPI→C**를 한 경로로 연결해 기준 출력과 source 준비/blocked cycles를 확인한다. 기존 기록을 외부에서 생성하는235 fixture와 구별한다. 작은 standalone FIT·seed 반복은 하지 않고 이 최소 실제 경로가 만들어진 뒤 한 번의 전체 보드 자원 gate로 간다.1392LE 교체 목표/기존 여유 보존,47+base6+scratch1=54/56M9K 용량 가설,CDC/IO/STA를 모두 확인한다.
4. 조건을 넘으면 parser를 무작정 더 압축하지 않는다. 회수 가능한 실제 기존 제어 범위와 B 전체의 계산 위치 재배치를 다시 비교한다. 전체 ARM 입력 RUN/IRQ·최종 displayACK 연결 후 실기 첫 레벨 스크롤로 간다.232의5개 map/OBJ VBlank burst도 별도로 해결해야 한다.

선택 `map01/analysis02`. analysis01은 Quartus 보고서를 UTF-8로 읽다 실패해 실행 전 중단됐고, latin-1을 명시해 수정했다. 실패를 보존한다.235 및 생산227 소스·GBC164·save SRAM·기존 봉인 자료는 바꾸지 않았다. 새 FIT/STA/실기 ZIP은 없다.
