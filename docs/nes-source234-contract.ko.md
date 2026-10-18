# NES234: 한 번 순회하는 입력과 END-count 검증

PR127의 같은 브랜치에 이어 기록한다. 기존231/232/233 및 생산227은 변경하지 않는다. **입력 C 프로토콜과 순차 접근 알고리즘은 통과했지만 FPGA 송신기·생산 SPI·전체 RUN은 아직 연결하지 않았다.** 새 실기 설치물은 없다.

## 작업 의미

60fps 화면 경로에서 입력 개수를 미리 세기 위한 전체 재순회를 없애는 작업이다. 전송 감소가 실제 준비 시간 감소로 이어지는지 확인하며, FPGA 송신기와 SPI 버퍼를 함께 교체할 조건을 구체화했다. 디버그 로그 확장이나 새 압축 종류 추가가 아니다. 출력231과 실제65816 소비기232의 결과를 그대로 보존한다.

## 구현과 wire 계약

`nes_stream234.py`는 이전 geometry5741B와 현재 immutable query 포트에 대해 앞으로만 읽는다. 모든 fetch가 이전 cursor와 같아야 하고, 프레임당 이전 자료와 현재 자료를 각각 정확히5741B 읽는다. 읽은 부분의 기준 메모리는 잠정 갱신하므로 중단 시 전체 기준을 무효화해야 한다. Python의 입력/출력 파일·packet list는 시험 fixture이며 FPGA frame 저장소가 아니다.

행 비교는 old/new66B씩, literal은240B, 저비용 raster 후보는12B 이하만 보관한다. raster XOR가13B 이상 유리해지는 순간 mask/count만 유지한다. 기존231 oracle과 같은 literal·행 이동·raster 연산을 생성한다. 전체 변경 위치 목록이나 두 번째 geometry 이미지를 만들지 않는다. 생성 알고리즘의 payload scratch를 보수적으로 row132+literal240+cheap12+mask8+pending243=635B로 잡았다. 주소·카운터·CRC·제어 레지스터 및 실제 RAM 포트는 별도 구현 대상이다.

새 C 수신기는 `nes_source234_packet`으로 **완전한 한 record**를 받는다. 헤더·marker를 구별하며 기존231의 logical_record/범위/요구 태그 검증은 재사용한다. 생략한 기록을 개수와 CRC로 검사한다. 여기의 CRC는 전송 무결성 검사이며 인증 수단이 아니다. 기존 SPI block token/CRC, immutable epoch admission, common STOP을 대체하지 않는다.

| 구간 | 바이트와 의미 |
|---|---|
| BEGIN20 | `N4`, version1, full flag0/1, epoch32, base serial32, serial32, generation16, reserved16=0. 숫자는 little endian |
| literal3+n | offset16, length8(1..240), bytes. 이전 끝보다 앞서거나 겹치면 거부 |
| raster13 | offset16,0,kind1,rows8,mask64.3872..5664의8B 행 경계만 허용 |
| shift7 | offset16,0,kind2,direction1/255,edge16. map의66B 행 단위만 허용 |
| GEOMETRY_END10 | FFFF16,0,kind3,span count16,expanded bytes16,CRC16 |
| RAW3+n | offset16,length8,bytes. geometry 확정 후0부터 patch_count×256까지 연속 수신 |
| END6 | FFFF16,0,kind4,CRC16. raw 길이까지 맞아야 COMPLETE |

CRC는 CCITT polynomial1021/초기FFFF이다. BEGIN20와 geometry 기록, GEOMETRY_END의 첫8B를 누적해 첫 CRC와 비교한다. 저장된 CRC2B 자체는 누적하지 않고 raw 기록과 END의 첫4B를 이어 누적해 마지막 CRC와 비교한다. trailer의 count가 CRC와 함께 재작성되어도 수신한 count와 다르면 거부한다. control 합계36B로231의 비용 모델28B보다8B 증가한다.

serial은0/FFFFFFFF를 거부하며 기준 serial+1을 요구한다. 초기 full은base0/serial1, 이후 delta는 epoch·base가 같아야 한다.16bit generation wrap은 허용한다. GEOMETRY_END 전의 변경은 in-place이며 오류/STOP 후 재사용하지 않는다. END의 COMPLETE는 표시 ACK가 아니다. 기존 PREPARED/COMMIT→consumed 수명을 통과해야 다음 BEGIN이 가능하다.

마지막 marker 자체가 도착하지 않는 경우 parser가 미래 누락을 즉시 알 수는 없다. 진행 기한 또는 common STOP에서 `nes_source234_abort`를 호출해야 한다. 그 후에는 common reset 전까지 BEGIN도 거절한다. FPGA 쪽 대응 base 폐기는 아직 RTL 구현 대상이다.

## 검증

선택 `test03/arm01/analysis02`. test01은 generation wrap 시험이1→0이었던 중간 자료로 보존했다. test02에서 cold65535→delta0를 실제 wire CRC와 함께 검사했고, test03은 cold 기준 RAM의 모든5741B를 반드시 쓰도록 접근 비용 모델까지 수정했다. cold 때 미초기화 RAM과 비교해 쓰기를 생략하면 안 된다. arm01의 candidate C/헤더는 test03과 동일하다.

- 동일230 관측 SMB3 첫 레벨 스크롤71프레임: 실제 C234 수신→기존231 planner/sink→4,066,624 reference checks 통과. geometry/raw/metadata/packets/plans355파일이 봉인된231과 byte-exact이다.186 reference와 비교했고 표시 ACK는 host fixture이다.
- 800개 full/sparse/raster/양방향 행 이동 모델에서 순차 접근 규칙과 기존 oracle의 연산열이 같다. 두 번 순회하거나 전체 changed-index 목록을 만드는 oracle은 비교용으로만 사용한다.
- 실제 C의1,459개 누락·중복·잘린 record·각 바이트1bit 변경·STOP·재시작·CRC를 다시 계산한 잘못된 count·generation wrap 검증 통과. 누락 END는 명시적 abort로 처리한 사실을 구분했다.
- ARM Cortex-M4 오브젝트: source32B, 입력9880B 유지, packet 자체 static stack72B. record 전체를 복사하는 수신 버퍼는 추가하지 않는다. **전체 입력 RUN/IRQ/callback chain은 연결 전이므로233의1616B 여유를 재승인한 결과가 아니다.**
- 출력 패킷 동일성으로232의 실제65816 증거를 재사용한다. 이번에65816을 새로 실행했다고 주장하지 않는다. 남은5개 map/OBJ VBlank 초과도 그대로다.

## 시간과 자원: 단일 순회만으로는 부족

같은 ready4 모델에서 warm69프레임 최대는5333→5341clock bytes,16.27733ms다. frame954의 base 읽기5741+변경 쓰기1683+logical query1977×2cycle을 직렬로 더하는 시나리오는11378cycle,SDC45.454ns 기준0.51718ms다. 합계 **16.79451ms**로16.67ms를 넘는다. query2cycle은 명시적 모델이며 실제 bridge의 지연 상한이 아니다. scratch 접근·제어·CRC·CPU·간격·stall 비용도 빠져 있다. 이 결과로 단일 순회 전체를 포기하지는 않지만, 직렬 준비 후 송신 안을 채택하지 않는다.

기존 `nes_native_spi165`는 `sealed` 동안 record_ready가 내려가고 D2 확인 뒤에야 다음 블록을 채운다. 전송과 다음 블록 준비가 이미 겹친다고 가정하면 안 된다. 읽은 실제224 FIT에서 exporter644LE/225FF, native_spi479LE/304FF/1M9K(buffer256B), 잔여159LE를 확인했다. 두 모듈을 함께 교체할 산술 범위는1282LE이나 회수·배치·타이밍 보장은 아니다.

packed base6M9K+encoder scratch1M9K, 기존 SPI M9K를512B 두 은행으로 재사용할 경우 총54/56으로2개 여유라는 **용량 모델**이다. 재사용 없이 별도 SPI RAM을 추가하면55/56으로1개만 남는다. 아직 multi-clock RAM/port가 맞는다는 증명은 없고, 미래 mapper 기능의 여유 보장도 아니다. save SRAM은 사용하지 않는다.

source 작업을 ingress SPI와 완벽히 겹친 하한은 최악16.27733ms다. 이를 달성 시간이나60fps 승인으로 읽으면 안 된다. 남은 CPU/실제 poll/consumer 비용과232의5개 VBlank 초과를 함께 해결해야 한다. ready1 모델은 최대5941B이며 여전히2프레임에서 SPI 자체가 예산을 초과한다.

## 다음 작업의 구체적인 조건

1. exporter와 single-block SPI를 함께 교체하는 작은 제어기 후보를 만든다. 실제 frame201 query를234 canonical byte로 변환하고 유효 count 밖은0을 만든다. 잘못된 count 밖 RAM을 읽거나 과거 frame 값을 가져오면 안 된다. fetch 시점 CHR/raster/row-mask 의미를 유지한다.
2. 준비 은행/전송 은행의 소유권을 분리해 다음 블록 준비를 겹친다. 기존 D1 CRC/D2 token/부분 SS 중단/STOP·reset을 보존한다. FIFO pop은 수신 block 확인이며 최종 표시 ACK가 아니다. base의 임시 쓰기와 세션 종료 실패를 연결한다.
3. record 최대243B를 block248B에 통째로 배치한다. 기존 ARM 수신 버퍼를 이용할 수 있는지 실제 decoder/callback/full RUN에 연결한 뒤 stack을 다시 판정한다. parser 오브젝트만으로 전체 스택을 통과시켰다고 하지 않는다.
4. controller/RAM 포트·대표 pressure·STOP 경계가 구체화된 뒤 제한된 합성/whole-board gate를 한다. 이후 paired firmware와 동일 첫 레벨 RIGHT+B/A 스크롤 실기로 간다. A가 전체시간/자원 gate를 통과하지 못하면 병렬 metadata B로 전환한다. isolated codec/FIT 반복,228 자동 재개,같은227/044 시험은 하지 않는다.

GBC164·save SRAM·227 배포물·기존 봉인 자료를 보존한다. 새 모듈은 후보 생성기/헤더와 시험 도구이며 실기 펌웨어가 아니다.
