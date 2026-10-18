# NES242: 공유 데이터 경로를 위한 실제 피연산자 측정

## 작업 의미

241의 제어 ROM 후보를 기각한 뒤, **240 데이터 저장·연산을 공유할 때 필요한 공간과 RAM 접근량을 측정**했다. 실제 첫 레벨 스크롤 자료에 계측기를 붙였으며 새 encoder나 실기판을 만든 단계는 아니다. 채택 기준240의490LE·40LAB 부족과 생산227은 그대로다. 이 측정은 그 부족분을 줄일 다음 구현의 범위를 정하기 위한 것이다.

## 측정과 보장 범위

실행하는240 RTL의 선택 필드 nonblocking assignment에 simulation-only write marker를 넣었다. 같은 값을 다시 쓰는 경우도 세며, 실제로 실행하지 않은 branch의 write는 세지 않는다. read는 상태별 양쪽 branch를 합친 보수적 집합이다. ROWVALUE 최초 두 byte의 history warmup, 사용하지 않는 송신 주소와 cold/warm RAM 주소만 명시적으로 제외한다. 따라서 read 횟수를 실제 최소 instruction 수라고 해석하면 안 된다.

reset 값만으로 초기화됐다고 간주하지 않고, 각 필드의 실제 정상 경로 write 이후에 의미 있는 read가 일어나는지 검사한다. 이는 관측 경로의 초기화 규약 검사이며 전체 경로의 formal liveness나 RAM 기반 구현의 검증은 아니다. operand 주소도 실제 회로에 연결한 것이 아니라 충돌 없는 배치안이다.

collector201→query235→계측240→SPI235 실제 핀→actual C234/231의 같은905..975를 사용한다. PPU stimulus와 host PREPARED는 fixture이며 실제 게임 CPU/ARM/SNES 표시/실기 FPS는 아니다. 기록 파일에 게임 byte와 원시 trace가 포함되므로 private archive에만 보존한다.

## 확인된 결과와 쓰기 생략 규칙

기존240 계측과 쓰기 생략 variant 모두 같은71프레임에서2229records/350blocks/62967payload B 및355개 C 복원 파일이 일치했다. 각 실행의4,066,624 reference checks와1459 C fault/restart도 통과했다. 두 실행의 cycles.csv는 기존240과 byte-exact다. 각 variant에24정상+17경계41검사와7view 긴 stall을 적용했고 초기화 검사도 통과했다. 초기화 marker를 의도적으로 누락한 negative는 각각 FSTORE에서 검출됐다.

FSTORE는 모든 incoming byte에서 old_byte/byte_at를 쓰지만, cold 경로에서는 이 값을 읽지 않는다. buffered map/raster 경로도 MAPLVALUE/RASTERVALUE 또는 다음 direct FSTORE가 소비 전에 다시 설정한다. 그래서 실험 variant에서는 **!cold && cursor>=2112 && (cursor<3872 || cursor>=5664)**인 직접 literal 영역에서만 두 필드를 쓴다. cold/base RAM 갱신·scratch payload·query offset·wire 규약은 그대로다. 이 규칙의 bounded replay/경계 검증이며 전체 formal proof는 아니다. production RTL 파일은 바꾸지 않았고, private simulation 변환과 재현 도구를 남겼다.

warm69의 byte 환산 필드 쓰기는 **2,743,381→1,935,253B**, **808,128B(29.46%)** 감소했다. 이는 실제 SPI bytes나 실행 시간의 감소가 아니다. 기존240은 원래 여러 FF를 같은 cycle에 쓰므로 두 variant의 실행 시간은 같았다. 다음 RAM 기반 구현에서 없앨 수 있는 저장 동작의 근거다.

| warm69 접근 비용 모델 | 전체29B RAM 정책 | hot5 유지/24B RAM 정책 |
|---|---:|---:|
| 원본: 추가 issue cycle 최대 |41,957|23,944|
| 쓰기 생략 후: 추가 issue cycle 최대 |38,053|20,040|
| 쓰기 생략 후: 추가 issue 시간 최대 |1.729661ms|0.910898ms|

모두frame954의 최대값이며 **추가 issue 시간은 측정된 실행 시간/FPS가 아니다.** 초기 상태에서도 hot5가 보수적 read+실행 write 접근량의50.20%를 차지했다. 따라서 자주 쓰는5B까지 RAM으로 보내는 후보보다 hot5 유지와 dead write 생략을 결합한 후보를 먼저 구현한다.

중간 실패도 보존했다. test01은 observer의 end/다음 token 사이 공백 누락으로 compile 실패했다. guards01은 정상41검사와 의도적 negative 검출은 됐으나 Questa가 fatal 후 exit0을 반환해 harness가 결과를 거부했다. guards02에서는 expected fatal와 정상 완료 부재를 판정한다. analysis01은 Python tuple/JSON list 비교에서 중단됐고 analysis02부터 직렬화 형식을 맞췄다. 회로 실패나 자원 결과로 해석하지 않는다.

## 메모리와 수명 경계

기존512×8 scratch의 payload 영역은 O0..65,N128..193,L256..495,C80..91,M96..103,P208..227이다. 합계412B로 **100B가 payload 밖**이다. 검토한22필드는204bit/29B다.104..127과228..232에 서로 겹치지 않게 배치할 수 있어, operand 저장 때문에 새 M9K가 필요하다는 전제는 제거한다. 이것이 새 설계의 합성·RAM port·timing 통과를 의미하지는 않는다.

| 필드 | 수명/초기화 | 공유 시 조건 |
|---|---|---|
| row_start,row_i,row_size | START에서 초기화, DISPATCH에서 다음 행 설정 | FSTORE와 map/raster 처리 동안 유지 |
| lit_at,lit_len,lit_used,gap | START·flush·raw 전환에서 설정 | 미발행 literal과 발행 중 L view를 분리 |
| byte_at,old_byte | FSTORE 또는 map/raster read에서 설정 | LITERAL이 쓰기 전 값을 소비해야 함 |
| old1,old2,new1,new2 | ROWVALUE가 2byte history를 채움 | row_i<2의 history 값은 비교에 사용하지 않음 |
| group_start,rows,cheap_cost,cheap_i,xor_byte | START/GROUPDONE/mask read/cheap publish로 설정 | 그룹 전환 전에 이전 그룹 record 완료 |
| spans,expanded | START에서0, geometry record별 증가 | GEOTRAILER 전까지16bit 값 유지 |
| raw_limit,build_i | START와 각 header/raw 진입에서 설정 | patch0..7 및240B literal 한도 유지 |

epoch32/base_serial32/generation16,독립 cursor13,input new_byte8,checksum16,송신 rec_i8/record_length8 및 제어 flags는 이번 offload 집합에서 제외한다. 이들을 유지하므로 START 직후 caller serial/epoch가 바뀌는 규약과 연속 lease 검사,독립 offset 비교,CRC 갱신을 몰래 느슨하게 만들 필요가 없다. 이후 옮기려면 별도 검증이 필요하다.

**공유 RAM의 가장 중요한 추가 조건은 출력 byte latch다.** 현재240은 a_q를 byte_data에 직접 연결한다. operand 접근으로 a_q를 바꾸면 ready 지연 중 공개 byte가 변하므로, 새 회로는 공개 직전에8bit를 고정하고 ACK까지 유지해야 한다. 동일 주소 read/write는 old-data 설정에 기대지 않고 순서로 회피한다. speculative base invalidation/common reset,abort/lease/ACK 우선순위도 유지한다. 현재 host/NES 최초 오류 보존 문제를 해결했다고 주장하지 않는다.

## 접근 예산의 해석

측정은 두 정책을 비교한다. 첫째는22필드 모두를 매 실행 단계마다 RAM에서 읽고 쓰는 방식, 둘째는 row_i와4개의 행 history 값을 레지스터에 남기는 방식이다. 후자는40bit/5B를 유지하고164bit/24B가 offload 대상이 된다.

hot5를 남기면 나머지24B는 **104..127 한 구간에 연속 배치**할 수 있다.5bit byte index8..31에 `{4'b0011,index}`를 사용하면 RAM 주소96+index가 되므로 분할 주소 lookup이 필요 없다.0..7은 M96..103이므로 operand index로 금지한다. 이 배치는 아직 회로에 연결하지 않았다.

`max(ceil((operand read+write+payload port 사용)/2), 산술 대입 byte폭, 1)`을 기존 실행 단계와 비교했다. 산술 대입 byte폭은 `+`/XOR 등이 포함된 대입의 좌변 폭을 byte로 환산한 값이다. 한 RHS의 여러 연산을 전부 세는 instruction 수가 아니다. 이는 **정의한 uncached 정책의 이상적인 issue 비용**이다. branch 비교, instruction fetch, 읽기 의존성,주소 decode,PC 제어는 제외했고 read 집합도 보수적이다. 실제 microprogram의 실행 시간 상한이나 모든 설계의 이론 하한으로 사용하지 않는다.

REQUEST/WAITACK/FETCH 대기는 operand를 다시 읽지 않으며,송신 주소는 SREAD에서 한 번 결정한 뒤 새 output latch로 유지한다는 조건이다. RAW response 대기는 실제 응답으로 write가 실행될 때만 센다. 기존 시간에 issue 비용을 더한 값은 민감도 계산일 뿐,지연을 적용해 SPI/ARM/SNES를 함께 재실행한 결과가 아니다. 전송 대기 시간만큼 추가 연산이 모두 가려진다고 가정하지 않는다.

## 다음 구현 범위

1. 240을 기준으로 START snapshot/lease/독립 offset/CRC/출력 byte 유지와 hot row history 경로는 보존한다. 차가운29B 전체를 무조건 RAM으로 옮기는 방식 대신 측정된 hot5 유지 정책을 우선 후보로 둔다.
2. 나머지24B를 기존 scratch의 비사용 영역에 배치하고,8bit 공용 ALU·carry/compare flag·주소 latch로 넓은 offset/count 갱신을 순차 처리한다. 기존 넓은 필드와 update case를 그대로 두고 decoder를 추가하는241 방식은 반복하지 않는다.
3. 제어 저장소는 최대512×18bit/1M9K를 **설계 한도**로 둔다. 예시 accumulator ISA는 opcode5+payload13 안에서9bit branch target+condition4 또는8bit immediate/5bit register index를 인코딩할 수 있다. 아직 전체 codec microprogram이512word에 들어간다는 증명도 합성 결과도 없다. 모든 필수 branch/RAM latency를 포함한 assembly와 실행 cycle부터 검증한다. 넘치면 묵인해 두 번째 ROM block을 쓰지 않는다.
4. 공용 scratch의 read/write 충돌,old/new operand 순서와output latch를 포함한 실제 kernel을24정상/17경계/7view stall에 맞춘다. 자원 gate를 통과할 가능성이 있는 경우만 whole-board MAP/FIT 한 번으로 확인하고,통과 후보에서 같은71프레임을 재실행한다. 이번 issue 비용 모델을 후보의 시간 측정 대신 쓰지 않는다.
5. 전체16.67ms는 여전히 미승인이다.236의 공유 SPI16.277ms 사례와240 isolated source6.236ms는 범위가 달라 단순 합산/상쇄할 수 없다. 새 입력 full ARM RUN/IRQ,host/NES first fault,최종 source lease/displayACK/retire,CDC/IO/STA,232의5개 VBlank 초과 burst도 남아 있다.

생산227/GBC164/save SRAM,240/241와 이전 봉인 archive는 보존한다. 이번에는 새로운 FIT·firmware·ZIP·실기 재시험 요청이 없다. 다음 구현에서 면적과 속도 양쪽을 확인하기 전에는60fps나 mapper 여유 확보로 판정하지 않는다.
