# NES336 실제 read event·private receipt 실행

기준은332 RTL+334 ARM이다.335의 비용 검토를 구현했으며,production227/GBC164/saveSRAM은 바꾸지 않는다. ordinary 소비는 기존325의536B 실제65816 bus trace를 같은 ARM/SPI/IRQ/2슬롯/ROM 일정에 재사용한다. tile/map은 기존 C/버스 서비스 모델이며,DMA 허용 상태에서 호출된다. 전체65816 polling/dispatch 프로그램을 새로 연결했다는 뜻은 아니다. ARM 시간은 실행 명령의CPI1/84MHz 모델이며 물리 MCU WCET가 아니다. IRQ는 기존24-cycle entry/exit 배정과 PB8 foreground checkpoint 모델을 유지한다.

## 실제 교체

host의 `active305.receipt_first/receipt_end`24비트와 descriptor에서 이를 계산하던 first/limit decoder를 삭제했다. validator의 exclusive-end register,끝주소 덧셈,first/last byte mask 및 자동 범위 순회를 삭제했다. descriptor의 domain·정렬·길이·overflow admission과 실제 응답/순차 read/count/token 검사는 유지한다.

유효한 aperture 응답마다 주소·바이트를 한 read job이 소유한다. scroll/raw CRC 처리 후 map2B/BG16B/OBJ32B/CGRAM16B/HDMA16B(마지막 raw9B)의 소비 단위가 완성되면 동일 validator B 포트에서 received/persistent RMW를 수행한다. 원본 payload를 다시 읽거나 ARM에서 receipt 주소를 새로 전송하지 않는다. byte-mask coalescer나 추가 RAM을 도입하지 않았다. 따라서 범위별 byte-mask 갱신보다 RAM 접근 횟수가 많아진다. 실제 read 간격에서 완료되는지 계측하며 이 비용을 무료로 처리하지 않는다.

host의 순차 read 종료 카운터는 남겨 두되,각 종료에 앞선 유효한 응답이 있었는지를 같은 read job의 pending bit로 확인한다. 유효한 응답 없는 bus strobe,누락·중복·주소 불일치,job이 끝나기 전 다음 응답은 fault다. aperture의 주소/token tag와 응답 유효성은 유지한다. raw read 신호만으로 receipt를 만들지 않는다.

## ACK 공개와 취소 경계

DMA 중 received/persistent/hash RAM 기록은 private다. 정확한 모든 응답과 read count,4 token bytes와 consume 값,해당 chunk의 token 및 모든 CRC/RAM job drain이 충족돼야 `good_consume`가 성립한다. 그 ACK 뒤에만 기존 저장 queue의 소비 완료와 map receipt를 공개하고 다음 descriptor로 넘어간다. 저장 credit과 실제 소비 완료는 합치지 않는다.

기존 물리 RAM receipt-before-ACK 금지 assertion은 이 후보의 계약과 다르다. 단순히 삭제하지 않고 다음 검사로 바꿨다.

- private RMW는 DMA 상태의 실제 read job과 유효한 chunk에만 속해야 한다.
- queue 소비/공개는 해당 descriptor의 정확한 token ACK 및 read/CRC/RAM drain 이후여야 한다.
- 최종 expected scan은 미완료 chunk/read/job을 건너뛸 수 없다. 기존 `v_all_consumed=1` 대신 실제 완료 신호를 연결했다.
- STOP/잘못된 ACK/누락 read/CRC 오류 뒤에는 pending write와 completion을 금지하고 phase·queue·staging RAM freeze를 검사한다.
- private persistent bit를 rollback했다고 가정하지 않는다. fault 후 같은 bank를 바로 재사용할 수 없으며 reset의 전체 phase RAM clear와 양쪽 bank cold 초기화가 필요하다.

독립 expected 저장과 최종 coverage/CRC/H2 검사는 유지한다. actual read에서 expected를 만들지 않는다. 최종12개 display read·표시 lease·정확한 최종 token ACK·VBlank 제약은 그대로다. 정상 취소 복구는 따뜻한 bank 복구가 아니라 기존 fault/reset+cold 경로이며,STOP가 보드 reset 없이 새로운 token namespace를 허용하지 않는다.

## 첫 ROM 공급 준비

334 ARM CRC/span 개선을 유지하고,E9 plan 송신 직전의 bitwise CRC16을16항목 nibble 계산으로 바꿨다. 새32B 읽기 전용 table 비용을 ARM text에 포함한다. 초기 plan 생산/정렬·입력 COMMITTED 경계·전송 순서·E9 payload 및 CRC 결과는 바꾸지 않는다. 첫 요청 준비를 단축해도 ROM 허용 구간이 닫혀 있으면 실제 수락은 빨라지지 않는다.

공동 후보의 고정/제한 연속/정상 연속과 RTL-only/ARM-only 고정 일정을 분리한다. 고정 일정은 source 시작 시각과 ROM cycle이 기준과 같아야 한다. 연속 일정은 이전 프레임이 바꾼 시작 시각,요청 시각,실제 수락 시각,수락 이후 처리와 절대 완료를 따로 기록한다. 위상 변화에 따른 대기를 계산 감소로 숨기지 않는다.

## whole 비용과 판정 기준

Quartus Lite whole MAP은 실제 변경 host/validator/소비 완료 연결을 포함한다. old parent/child 면적을 중복 합산하지 않는다. 새 event 상태·pending bit·주소 변환과 유지한 검사까지 전체 수치에 포함한다. 독립 source/plan RTL을 고쳤다고 주장하지 않는다. 주변 mapping 변화도 whole 결과에는 포함하되 해당 블록에서 새 로직을 제거한 것으로 보고하지 않는다.

수치와 최종 검증 목록은 `analysis/read336-verification.json`과 `docs/nes-read336-plan.json`에 결합한다. MAP의 절감은 FIT/LAB/STA 통과를 뜻하지 않는다. fullRUN71·전체 ROM 위상·물리 지속60fps는 별도 미완료 gate다.

## 실측 비교

모든 행은 같은905/906/907 fixture와 동일 SPI payload를 사용한다. 아래 시간은 warm907이며, source 시작부터 최종 표시 완료까지 기존 합산 기준을 유지한다.

| 일정 | 332 RTL+334 ARM | 336 공동 후보 | 차이 |
|---|---:|---:|---:|
| 동일 시작 시각·ROM 위상 |25.059517464ms|25.051199382ms|−8.318082µs|
| 제한 ROM 연속 |20.696615274ms|20.689660812ms|−6.954462µs|
| 정상 ROM 연속 |13.435202412ms|13.410066350ms|−25.136062µs|

RTL-only 고정 일정의 warm 차이는0이고,ARM-only는 공동 후보와 같다. 회로 절감과 warm 시간 개선은 각각 RTL/ARM 변경에서 나왔다. cold 고정 일정에서는 공동 RTL이 ARM-only보다905/906 각각45.454/90.908ns 빠르다. cold 제한 연속 총시간99.244763594/116.712281254ms는 여전히60fps 대상 달성으로 볼 수 없다.

첫 요청은 cold905에서44.545µs,warm 고정에서16.363µs 빨라졌지만 제한 ROM 수락은 동일하다. 제한 연속 warm의 시작은1.363µs,절대 완료는8.318µs 빨라져 프레임 자체 개선은6.954µs다. 정상 연속의 요청/수락이586.175µs 앞선 것은 이전 프레임의 시작 이동을 포함한다. 이를 순수 계산 개선으로 합산하지 않는다.

제한 연속 post-ROM은3.833795ms이며3.180ms 예산보다0.653795ms 크다. 전체20.689660812ms는60Hz 예산보다4.022994145ms 크다. 수락 시각을 고정하면 post-ROM을 전부 없애도 남는 시간이 있으므로,후반 처리만 줄이는 것으로는 목표를 달성할 수 없다.

| Quartus Lite whole MAP | 332 | 336 | 차이 |
|---|---:|---:|---:|
| LE |22539|22256|−283|
| 조합 논리 |17649|17378|−271|
| FF |9097|9066|−31|
| RAM bits |307808|307808|0|
|15408comb 대비 부족|2241|1970|−271|

host own2348→2169(−179),validator1053→957(−96),동일 aperture RTL의 mapping206→203(−3),나머지 net+7로 whole−271이다. 부모/자식 수치는 중복 합산하지 않았다. source/plan을 실제 삭제했다고 계산하지 않는다. 추가 latch/undriven 경고는 없으며 기존 cache_index141 latch 경고는 유지됐다. MAP은 한 번 실행했고 FIT/STA는 실행하지 않았다.

ARM text30054→30110(+56B,32B table 포함),BSS47404/data0/관측 stack1288은 같다. 고정 일정 명령 감소는905/906/907 각각24275/23587/2177개다. 전송량·E1/E9 payload·순서는 전부 동일하다.

## read job 비용과 검증

공동 후보9프레임에서56877 actual read,13983 완성 단위,15618 private RAM write,642 chunk 공개를 대조했다. RTL-only3프레임까지 합치면75836/18644/20824/856이다. ARM-only3프레임은 이전 RTL이므로 이 read-job 개수에 넣지 않는다. 모든 최종 metadata8570B/receipt754B/hash64B와 기존 독립 oracle 비교를 유지한다.

3프레임당 private write는2584/2580/42번이다. 각 write에 RMW read1회를 포함한 고정 FSM 점유는61.519872/61.424640/0.999936µs이며335의8.713728/8.951808/0.357120µs보다 늘었다. 이는 실제 write 수에서 유도한 RAM busy 비용이고 별도 상태 계측값이 아니다. DMA read 간격과 겹치므로 전체 시간에 다시 더하지 않는다. 관측 최대 read→private write108ns,warm60ns,최소 read 간격369ns다. 이 실행 범위 밖의 임의 버스 속도 보장은 아니다.

선택 검증은15 양성 일정(공동3×3,분리2×3),13 fault 주입,실제 M4 E9 CRC964건,raw0/독립 최종 검사7건,private STOP/reset1건과 aperture tile pingpong/wide3418/wrong-token/STOP이다. fault는 SPI 중간 STOP,조기 최종 ACK,expected/actual CRC 훼손,ROM pending STOP/drain,조기 consume,private RMW·raw CRC 중 STOP,잘못된 token,유효 응답 소실,중복 map 단위,domain overflow,공개 전 final scan을 포함한다. 각 fault 뒤 phase1024B/queue1024B/staging4096B freeze와 completion 비공개를 확인한다. 중복/overflow/final scan은 validator 인터페이스에 직접 오류를 주입한 검사다.

STOP/reset 단위 검사는 private received bit가 기록됐으나 persistent bit가 기록되기 전 취소하고256주기 freeze를 확인한다. 이후 reset에서 phase RAM1024B clear와 양쪽 bank 초기화 무효화를 확인한다. 이전 private bit를 따뜻한 bank 복구에 재사용한다는 보장은 없다.

## 다음 교체 예산

336을 다음 실험 기준으로 유지한다. 현재 host+validator+aperture3329,queue/SPI851,source1765,plan460으로 검토 범위6405comb,외부10973comb다. 외부가 같다면 범위 상한4435comb,132comb 여유 목표는4303comb이며 최소2102comb를 더 줄여야 한다. 이전 범위 예산4316을 그대로 쓰면 여유는119comb다. 새 포트 중재·CDC·주소·상태 비용을 모두 이 상한에 넣는다.

남은 host descriptor/queue/SPI 진행과 source/plan의 decode·주소 선택을 함께 실제 삭제할 범위로 다시 잡아야 한다. receipt RAM의 마지막1µs 수준만 반복 최적화해서0.654ms 후반 예산이나4.023ms 전체 부족을 해소할 수는 없다. 입력 완료와 실제 첫 ROM 수락,그 이후 tile/ordinary 공급을 함께 바꾸고 동일 시작 위상과 연속 일정으로 분리 비교한다. 독립 expected/final scan은 유지한다. 개별 FSM·seed·FIT 반복을 다음 작업으로 잡지 않는다.

## 실패 기록

rtl01은 read_count 선언 순서의 compile 실패다. rtl02는 실제 삭제한 descriptor24비트와 기존145비트 고정 monitor의 불일치로 중단했으며121비트로 수정했다. rtl03은 최종 소비 완료 연결 전의 초기3프레임 통과 기록으로 보존한다. 최종 whole MAP 및 선택 실행과 섞지 않는다. 라이선스 문제로 분류하지 않는다.

guards01의case19와 guards02의case21은 fault 발생 뒤 정상 버스 드라이버가 다음 byte를 읽다가 종료해 freeze 검사를 끝내지 못했다. 완료한8건/2건만 partial-result로 보존하고 전체 PASS로 표시하지 않았다. guards03의case21은 순간적인 조합 조건을 주입 시점으로 잡아,후속 버스 중단 뒤 유효한 중복 요청이 들어가지 않아 expected fault timeout이 났다. 이미 처리된 map 단위 확인 후 validator 인터페이스에 중복 요청을 유지하는 방식으로 guards04에서 재검증했다. 이 수정들은 검사 드라이버에만 적용했으며 선택 RTL/whole MAP 입력 hash는 같다. 분석 중 binary ROM UTF-8 decode 실패 로그도 보존했다.

최종 analysis01의 host 파일 전체 hash 동일 조건은 board 전용 기존 `tile_closed267` 출력 두 줄 차이로 실패했다. exact diff로 기존 출력 선언/연결만 확인한 후 이 두 줄만 정규화하고 나머지 byte 전체를 비교했다. validator는 원본 hash 동일,board wrapper는332 입력에 실제 완료 신호 연결 변경만 적용한 것과 정확히 같아야 한다. analysis02는632개 근거 hash를 결합해 통과했다. 이 분석 수정은 RTL이나 합성 결과를 변경하지 않았다.
