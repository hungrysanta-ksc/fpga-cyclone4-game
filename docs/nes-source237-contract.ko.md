# NES237: 실제 조회→증분 생성→SPI→C 연결

## 작업 의미

60fps를 위한 입력 전송 절감 모델을 FPGA 회로로 옮겼다.235에서는 조회 RTL과 SPI RTL 사이를 미리 만든 record 파일이 연결했지만,237은 실제 collector가 반환한 현재 화면과 FPGA RAM의 이전 화면을 비교해 전송 record를 직접 만든다. 기존 게임 실행부를 바꾸는 실기 배포판은 아직 아니다.

## 구현 범위

- `nes_source_encoder237`은 N4 BEGIN, geometry literal/행 이동/raster XOR, END-count/CRC, raw patch, 최종 END를 생성한다. 필드 길이·CRC·serial·epoch를 줄이지 않았다.
- 이전 화면은5741B이며 RAM 깊이는6144×8이다. 첫 serial1에서 전부 쓴 뒤에만 재사용한다. 이후 비교 중 바뀐 byte만 쓴다. 중간 실패는 base 전체를 무효화하며 sender/receiver의 common reset이 필요하다.
- 작업 RAM 주소는 old row0..65, new row66..131, literal132..371, cheap raster372..383, mask384..391, pending record392..634다. 보수적635B를1024×8 RAM 한 개에 배치했다. 두 포트 동시 동일 주소 쓰기와635B/5741B 범위 초과는 시험에서 검사한다. payload RAM은 reset하지 않는다.
- 두 은행 SPI235에 완전한 record를 넘기며, D2 POP 전에는 해당 은행을 재사용하지 않는다. D3 PREPARED의 accept/generation을 검사한 뒤 source base를 승인한다. **이것은 최종 SNES 표시 ACK나 resident commit이 아니다.** 기존 capture lease/final retire와 common STOP이 여전히 필요하다.
- 실제 collector query는235 reader를 재사용한다. raw query kind7도 같은 collector에 연결했다. 현재는 query와 encoder를 하나의 경로에 연결한 기능 후보이며, cursor/holding/복사 상태를 완전히 공유한 최종 자원 최적화 구현은 아니다.

## 검증 경계

동일한 관측 SMB3 첫 레벨 스크롤905..975의71프레임을 actual frame201→query235→encoder237/base/scratch RAM→SPI235 실제 핀 전송→actual C234/231에 넣는다. 사전에 만든234 stream은 비교 기준으로만 읽으며 FPGA 입력으로 공급하지 않는다. 기록된 PPU stimulus와 host PREPARED ACK, C의 ROM/표시 callback은 fixture다. 게임 CPU 전체 실행·실제 SNES 표시 ACK·실기 시험으로 해석하지 않는다.

71프레임의2229record/350block/62967payload byte와 record 경계가234 기준에 일치한다. SPI로 받은 바이트를 실제 C에 넣은 geometry/raw/metadata/packet/plan355파일이 같고4,066,624 reference checks 및 기존 C fault/restart1459검사가 통과한다. 출력 파일 일치로232 소비기 증거를 재사용하며 이번에65816을 다시 실행한 것은 아니다.

별도20합성 프레임은 양방향 행 이동, 전체 잡음, 반복·0·희소 raster mask, literal gap/240B 경계, patch0..7, generation65535→0을 검사한다. 추가16검사는 잘못된 epoch/serial/offset, lease/generation 상실, 부분 전송 중 abort, 이른 ACK/잘못된 ACK/reject, raw hit/폭 오류, 응답 누락 후 abort, common-reset cold replay다. 총36검사가 통과하며 모든 정상 완료에서 base5741B를 현재 입력과 비교한다.

## 준비 시간과 전송 대기

기존 비교와 같은907..975의69프레임에서 source clock45.454ns, host11.904ns, SPI2.625MHz 핀 자극을 사용했다. source cold는905 한 프레임이며906은 source warm이지만 출력 쪽 두 번째 은행의 cold 비용을 분리하기 위해 기존69프레임 창을 유지한다.

| 입력 경로 구간 | 최대 cycle | 최대 시간 |
|---|---:|---:|
| 전체 시작→PREPARED 승인 |137913|6.268698ms|
| 조회·RAM·차분 생성 준비 |39779|1.808115ms|
| record 버퍼 공간 대기 |71543|3.251916ms|
| 최종 block 전송 및 ACK 대기 |23271|1.057760ms|
| record/byte 전송 제어 |3321|0.150953ms|

각 프레임에서 네 하위 counter의 합이 전체 counter와 같다. 표의 각 최대는 독립 최대이므로 합산한 값을 한 프레임이라고 주장하지 않는다. 전체 최악은954다. `ackwait`는 마지막 block을 비우는 시간까지 포함하며 ACK 자체 왕복 지연이 아니다. 다른 은행이 봉인된 동안에도 새 payload byte를 썼다.

**6.27ms는 전체 화면 출력 시간이 아니다.** 실제 ARM 파싱·planner 계산·다른 SPI 명령·SNES DMA/표시 ACK가 제외돼 있다.236의 ready4 공유 SPI16.277ms 모델과 단순 가산하거나 대체할 수 없다. 이 측정은 실제 encoder를 넣어도 overlap이 동작하며 준비 시간이 어느 정도인지 확인한 것이다.60fps 및232의5개 VBlank 초과는 아직 미완료다.

## 자원 gate와 실패 보존

최초 board01에서 scratch의 두 쓰기 포트를 하나의 sequential process로 기술해 Quartus가 M9K로 추론하지 못했다. 전체 MAP 추정41542LE/16823FF, source encoder만23014 combinational/8659FF가 발생했다. 이 결과를 논리 자원 요구량의 최종값으로 사용하지 않는다.

두 RAM 포트를 별도 process로 분리했다. 동일 주소 동시 쓰기가 없는 controller 규약을 추가 assertion으로 검사하고,20합성/16경계와 실제71프레임을 최종 소스로 다시 실행한다. 변경 전후 전체 `cycles.csv`가 동일해야 봉인한다. 이 수정은 controller/codec의 기능 변경이나 seed 탐색이 아니다.

전체 보드 resource 후보는 기존 exporter203,96bit records mailbox,17bit PREPARED mailbox,SPI165와 그 host release를 교체한다. capture/lease,loader/arbiter,plan/tile/sink 경로는 회수하지 않는다. 새 source serial과 start admission을 연결한 보드 glue는 자원 측정용이며 생산 runtime 또는 CDC 검증을 대체하지 않는다. ROM/SNES 소비기 내용과 clock/SDC 예외는 바꾸지 않는다. 새 source CDC 이름을 검증하지 않은 기존 SDC로 STA 합격을 주장하지 않는다.

board02는 RAM 추론에 성공했지만, 이미 제거한 mailbox를 가리키는 기존 CDC 제약 때문에 FIT 준비 중 실패했다. `nes_dac162:audio|nes_release[1]` 오류도 제거된 native_records/native_prepared의 up 경로에 붙어 있던 제약에서 발생했다. 이 결과를 물리적 자원 부족의 확정 증거로 쓰지 않는다.

board03은 **제거한 exporter/records/prepared/SPI 인스턴스가 포함된 기존 제약216행만 삭제**했다. 남은 제약은 그대로이며 새로운 false path/clock group 예외나 큰 지연 허용값을 추가하지 않았다. 이 정리는 새 source CDC 검증 완료를 뜻하지 않는다. 기존 정상224도 MAP 추정18850LE→실제 FIT15249LE였으므로 MAP 추정치만15408과 비교해 불가능이라고 단정하지 않는다.

최종 전체 보드 MAP은20539LE 추정/조합15664/8619FF/316000memory bits다. base6144×8 single-port와 scratch1024×8 true dual-port M9K 추론이 확인됐다. 기존47개+base6+scratch1=54/56 M9K는 용량 산술이며, 실패한 FIT로 실제 배치 완료를 주장하지 않는다.

이번 FIT는 SDC missing/ambiguous 오류 없이 자원 검사에 도달한 후 **Error170011: 조합 node15664개가 기기15408개를 초과**해 종료됐다.256은 최소 초과량일 뿐이다. FF와 LAB packing,타이밍 및 mapper 확장 여유까지 고려하면256만 줄여 충분하다고 말할 수 없다. 새 source 계층은 조합2782/1016FF이고,그중 encoder2069/451FF,reader225/139FF,transport454/426FF다. 이 hierarchy 조합 수를 최종 FIT LE로 바꾸어 표기하지 않는다.

다음은 기능 검증된 codec를 보존하면서 query/cursor,여러 return-state,주소 선택·복사 제어를 통합하는 구조 변경이다. 기본 목표는 기존1392LE 교체 범위와159LE 여유 보존이다. 기존 endpoint MAP에서 산출한 추가271LE 목표를 현재2069조합 node와 같은 단위의 확정 차감식으로 섞지 않는다. 행이동/raster를 제거하는 방법은236의 같은 스크롤 전송 예산에서 이미 탈락했으므로 다시 시도하지 않는다. 단순 seed/클록 완화 반복도 하지 않는다.

선택은 test04/guards02/board03/source01이다. test01의 벤치 시간 리터럴·줄바꿈 compile 실패,test02의 두 프레임 확인,test03/guards01의 RAM 포트 수정 전 성공,board01의 RAM 추론 실패,board02의 제거된 제약 참조 실패도 보존한다. 라이선스 서버 자료와 ROM·게임 trace·binary는 Git에 넣지 않는다.

## 미완료와 보존

실제 전체 ARM 입력 parser RUN/IRQ 여유,최종 source lease→displayACK→retire 연결,보드 자원/CDC/IO/STA와232의5개 map/OBJ VBlank burst가 남아 있다. 기능이 같다는 이유로233의1616B 여유를 새 입력 경로 승인값으로 쓰지 않는다. 자원과 전체 경로가 통과한 뒤 새 paired firmware/FPGA로 실제 첫 레벨 스크롤을 확인한다.

생산227,GBC164,save SRAM,기존 봉인 자료는 변경하지 않는다. 새 실기 ZIP은 없으며 동일227/044 재시험을 요구하지 않는다.
