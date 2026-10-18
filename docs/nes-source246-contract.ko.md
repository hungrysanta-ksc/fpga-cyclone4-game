> 2026-10-18 계획 갱신: 이 문서의 기능·자원 결과는 보존한다. 아래 “수정된 다음 순서”는 [PR127 회고·인계](nes-pr127-retrospective.ko.md)와 [P0–P3 계획](nes-pr127-next-plan.json)으로 대체됐다. 단일 sequencer는 미선정이며 구현은 PR127 머지 후 새 PR에서 진행한다.

# NES246: 공유 연산기 전체 연결과 자원 gate 기각

## 작업 의미와 판정

245의 행·literal 연산기를 실제 frame 입력/base write/header/CRC/RAW/ACK 흐름에 연결했다. 기존240의 넓은 codec operand를 병렬로 남기지 않고 scratch RF로 대체한 **전체 인코더 후보**다. 25정상 frame과17경계 검사에서 출력·CRC·base가 기준과 일치한다. 그러나 전체 보드 FIT가 **16027LE/1011LAB/55M9K**를 요구한다. 칩 한도15408LE/963LAB/56M9K에619LE·48LAB가 부족하고,240보다129LE·8LAB·1M9K 늘었다. **246은 채택하지 않는다. 기능 기준240, 생산227을 유지한다.**

공유하면 작아질 것이라는 가정은 전체 연결 결과에서 성립하지 않았다. 이번 결과를 화면 속도 개선이나60fps 달성으로 보고하지 않는다. 배치되지 않았으므로71프레임 스크롤 통합·STA·ARM·설치물 생성으로 넘어가지 않았다.

## 실제 연결

- scratch512×8 하나에 payload와24B RF를 함께 둔다. base4096×8+2048×8은240과 같다. row_start/lit_at/byte_at/group_start,길이·rows·spans·expanded 등은 engine RF만 보유한다.
- 외부 frame 제어기는 admission epoch32/baseSerial32/generation16,독립 cursor13,입력 byte,CRC16,record/prefix 제어를 유지한다. 입력 수집용 row_i7와 engine 내부 scan row_i7는 별개이며 이 중복 비용을 숨기지 않는다.
- 245의 불필요해진81word를 제거하고 모든 JMP/JZ/JC 주소를 재배치했다. fused direct/row literal과 raw_begin36word를 더해408/512word다. direct는 old/new와 위치를 한 번에 고정하며,row literal은 O/N을 engine이 직접 읽는다. 이전 context→literal 두 호출을 한 호출로 합쳤다.
- SETARG는 engine이 이미 잡은 인자의 low byte만 갱신한다. frame admission 값은 변경하지 않는다. raw_append는 새 길이를 반환해 매 byte 외부 RF read를 없앤다.
- header20B/geometry trailer10B/raw end6B는 외부 latch에서 송신한다. trailer의 spans/expanded만 idle/read-only RF 접근을 사용한다. CRC는 실제 승인된 byte에서 한 번 갱신하며 trailer CRC 자체는 제외한다.
- literal 결과2는 동일 입력을 유지한 flush 후 재시도,결과3은 flush 후 진행이다. raster group은 이전 group flush/output/reset 후 새 mask를 설정한다. RAW는 geometry count에 포함하지 않는다.
- base는 speculative하게 쓰지만 성공 ACK 전에는 committed base가 아니다. 실패 시 base_valid를 지우고 common reset이 필요하다. done/PREPARED가 SNES 최종 displayACK라는 뜻은 아니다.
- prefix 레코드 길이는 요청부터 마지막 byte까지 유지한다. engine RECORD는 직전 byte latch가 비었거나 같은 edge에 승인될 때만 다음 header를 공개한다. 이전245 독립 cheap 시험에서는 드러나지 않았던 마지막 byte 장기 stall의 레코드 겹침 가능성을 전체 연결에서 차단했다.

## 검증과 보존 자료

선택 guards04는 변경하지 않은240의24개 완전한 geometry/raw/serial/expected fixture와,두 cheap record가 연속되는 추가1frame을 사용한다. 출력 record 경계/길이/모든 byte/CRC와 완료 후5741B base를 대조한다. 추가 frame은 기존234 독립 encoder로 기대값을 만들며 게임 ROM 입력이 아니다.

총25정상+17경계=42검사,7종류 출력 view stall을 통과했다. cold/warm,serial carry 및 최대 경계,epoch/serial 불일치,offset 오류,lease/generation 상실,abort,early/wrong/rejected ACK,RAW invalid/missing-response 대기,긴 record 중 취소와 cold 재실행을 포함한다. 별도 record_ready와 byte_ready 조건에서 cheap 첫 record의 마지막 byte를256cycle 막았고 다음 header가 먼저 공개되지 않았다.

- guards01: payload_ready 선언 순서 compile 실패. 원본 보존.
- guards02:24+17=41 기능 통과. prefix 외부 length 수명 보강 이전.
- guards03:41검사에 record 길이·발행 순서 invariant 추가. guards02와 frame cycle 동일.
- guards04: engine의 다음 RECORD 공개 조건과25번째 frame/256cycle stall 보강. 최종 선택.
- board01: guards04와 같은 RTL/ROM hash로 MAP1회·FIT1회. 합성 성공,용량 부족으로 FIT 실패.

actual collector/SPI 핀/C/SNES가 연결된71프레임 시험은246에서 실행하지 않았다. 이 단계의 결과를 기존240의71프레임 결과와 섞지 않는다. synthetic42검사가 모든 게임/mapper 의미를 증명하지도 않는다.

## 전체 비용과 실패 원인

|같은 전체 보드 범위|240|246|변화|
|---|---:|---:|---:|
|MAP LE|19809|19884|+75|
|조합 함수|14966|15027|+61|
|FF|8577|8535|-42|
|FIT 요구 LE|15898|16027|+129|
|FIT 요구 LAB|1003|1011|+8|
|M9K|54|55|+1|
|encoder 조합/FF|1399/409|1424/367|+25/-42|
|source 전체 조합/FF|2092/974|2125/932|+33/-42|

246 encoder의1424조합 함수는 외부 제어827+engine597이다. 전체 codec operand를 공유 RAM으로 옮겼지만 frame FSM/continuation/kentry/인자 선택과 engine의 opcode/phase/RAM 중재가 공존한다. **제어·선택 회로의 비용이 operand 갱신 절감을 상쇄했다는 해석**이다. 특정 mux 하나가 몇 LE를 소비하는지는 이 hierarchy 보고서만으로 분리할 수 없다.827 전체를 순수 FSM 비용으로 부르거나597 전체를 새로 더해진 비용으로 단정하지 않는다.

FF42개 감소도 배치 이득이 되지 않았다. LUT-only는240의7321에서7492로171개 증가했고,register-only는932에서1000으로68개 증가했다. paired는7645에서7535로110개 줄었다. 더 적은 FF가 더 적은 LE/LAB를 보장하지 않는 실제 결과다. FIT의1011LAB는 요구량이며 배치 완료치가 아니다.

scratch4096bit와program9216bit는 M9K로 정상 추론됐다. FF 배열로 풀린 RAM이 이번 실패 원인은 아니다. 총 유효 memory321120bit(62%)라도 물리 M9K는55/56(98%)다. 남은1M9K를 여유 메모리38%로 해석하면 안 된다. 직접 전송206도 보드에2504조합/1670FF로 남지만 실제 타일 생성·전송 경로에 사용되므로 검증 없이 제거 가능한 중복이라고 간주하지 않는다.

216개의 이미 제거된 source instance SDC만 정리한 내용은240과 byte-exact다. 새 false path/clock 완화/seed 탐색은 없다. 기존 loader state unmatched와 IO 경고가 남으며 새 STA/CDC/IO 승인은 없다.

## 시간 비용

기능 시험은 ready stall을 포함한 full encoder cycle을 기록한다. 최소 정상130097cycle,변화량이 많은 합성 case15는1043674cycle이다.22MHz 환산으로약5.91ms와47.44ms다. 이것은 새 실제 스크롤 FPS도,240과 동일한71프레임 시간 비교도 아니다. 그러나 큰 변화 frame의 추가 cycle을 무시하고 자원만 맞추면60fps라는 결론은 낼 수 없다.

408word/512word에 들어간 것과 주어진16.67ms 안에 실행되는 것은 별도 조건이다. 통신/SNES 시간을 이 값에서 임의 차감하지 않는다. 기존232의5개 VBlank 초과 burst와 SPI236의여유 문제도 계속 남아 있다.

## 수정된 다음 순서

1. **246의 미세 튜닝/독립 opcode 확장/seed 반복은 중단한다.** 더 작은 FF 수를 성공 지표로 삼지 않는다.240의490LE·40LAB 부족도 여전히 해결되지 않았다.
2. 다음 후보는 먼저 제어를 포함한 전체 면적·시간 구조를 비교한다. 한 가지 검토 대상은 frame FSM+continuation과 engine PC를 하나의 sequencer로 합쳐 경계·입력·출력 대기를 같은 제어 흐름에서 처리하는 것이다.241은 wide datapath를 남긴 control-only ROM,246은 shared datapath에 외부 제어가 남은 구조이므로 단순히 어느 한쪽 ROM을 다시 붙이는 반복은 하지 않는다. 기존240에서 경로 간 중복을 제거하는 대안도 함께 비교하고,더 싸고 빠른 쪽만 구현한다. 아직 어느 쪽도 절감 보장은 없다.
3. frame query/admission/CRC/output latch/ACK 수명을 포함한 비용을 사전에 적는다.246 기준 최소619LE·48LAB 이상과 mapper 여유를 마련해야 하므로 작은 카운터 몇 개로 닫힌다고 가정하지 않는다. 프로그램512word,단1M9K 잔여,반복 literal/RAW 최악 cycle과22MHz/16.67ms를 함께 제한한다. 근거 있는 절감 경계가 없으면 큰 재작성/FIT에 들어가지 않는다.
4. 선택 후보만 최소 전체 byte/reference/취소 검사→단일 whole-board gate→통과 후 동일905..975 스크롤71프레임 통합으로 진행한다. 이어서 full ARM RUN/IRQ,host/NES 최초 오류,최종 displayACK/source lease/retire,CDC/IO/STA와실기 first-level scroll을 확인한다.

생산227,GBC164,save SRAM,이전 봉인 자료는 유지한다. 새 설치물이나 같은227/044 실기 재시험은 없다. MMC4/5와state-save/frame-skip/mute의향후 여유도 미승인이다.
