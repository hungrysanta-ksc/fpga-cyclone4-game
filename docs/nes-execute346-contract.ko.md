# NES346 — 단일 record 출력과 host 공통 실행기 실제 교체

338 RTL·336 ARM을 출발점으로 구현했다. 채택 기준은338/336을 유지한다. 새 회로는 whole Lite 조합 논리17511개로 기준17274보다237개 증가하여 보드 한도15408 대비2103개 부족하다. 공통 출력·목적지 진행을 실제로 삭제·공유했지만 시간·회로 동시 개선 후보로 채택할 수 없다.

## 실제 변경

`tools/nes_execute346.py`는338 encoder에340의 MASK·SHIFT·nonmap literal/repeat8/raster repeat16 형식을 유지하면서344의 최종 record 저장을 결합한다. MASK의 mask/value 출력 주소 선택과 SHIFT 출력 byte mux를 삭제했다. nonmap의 rec_i−4 주소 복원과 출력 seed/seed_hi mux도 삭제했다. nonmap data/seed를 local260부터 저장하고256..259의4B header를 backfill한다. 이후 모든 형식이256+rec_i로 읽힌다. 기존512B phase RAM 안에서 최대76B record를 사용한다.

MASK 지연 쓰기, 좌우 SHIFT 판정과 history, nonmap region/seed/count/pending query,64B 경계,CRC trailer2B 선택은 남는다. 현재 query byte가 run 종료를 일으키면 pending으로 보존하여 다음 record에 다시 사용한다. 전체 record 생성·출력 완료 전에 같은 공간을 덮어쓰지 않는다. 형식별 판단까지 제거된 단일 codec은 아니다.

host에서는 PUT/EXPAND325/MISSUE313/MWAIT313 목적지 진행을 ISSUE346/WAIT346/NEXT346로 교체했다. literal·repeat·metadata의 목적지 cursor는 하나의12bit expanded325를 사용하며, metadata의 기존9bit manifest_byte313 저장은 alias로 대체했다. encoded parser cursor는 별도로 유지한다. codec의 run/zero/bounds 검사와 다음 byte 선택은 SUPPLY346에 남으며, 기존 MNEXT313를 이름만 바꾼 부분을 새 절감으로 세지 않는다. header/token 파싱용 at도 남는다.

staging은 put_ready, H2는 mready, expected RAM은 range_ready와 범위 검사를 만족한 ISSUE에서 쓰기/accept한다. expected RAM write enable은 grant가 없으면0이다. metadata는 WAIT 뒤 NEXT에서 한 번만 cursor를 증가한다. 일반 출력도 NEXT를 거치므로 추가 클록이 실제 일정에 포함된다. opcode/version/length/166·256 영역 검사와 독립 validator의 실제 read CRC·coverage·private job·최종 scan은 유지한다. queue 저장 retire, 실제 소비 receipt, 최종 display ACK는 구분한다.

ARM은336 batch 발행·capacity·full COMMIT 장벽을 유지한다. 후보의 ARM 바이너리가336과 동일한 것은 아니다. N5v3의 OBJ-after-GEO 배치에 맞춰340 decoder·checked membership bitmap·늦은 OBJ 수신 처리를 사용하며,340 slot1 prefix와344 BG prefix는 넣지 않았다. 이 변경 비용도 같은 M4 인스턴스에서 SPI bank checkpoint마다 계상한다. 후보 ELF text30270B는33630110 대비160B 증가, BSS47428B는24B 증가, observed stack1288B는 동일하다. 이는 probe ELF이며 전체 firmware RAM/WCET 증명이 아니다.

## 전체 Quartus Lite 비용

|동일 whole 경계|338 기준|346 최종|차이|
|---|---:|---:|---:|
|LE|22144|22394|+250|
|comb|17274|17511|+237|
|FF|9018|9050|+32|
|RAM bits|307808|307808|0|

source encoder own comb는1348→1624(+276), host는2161→2134(−27)다. 이 두 값의 합과 whole 차이는 나머지 hierarchy의 remapping 때문에 같지 않다. 부모·자식을 중복 합산하지 않는다. source/host FSM 모두 추출됐다.340의17602comb보다는91개 적지만 선택 기준338보다 크다. whole15253 목표까지2258개가 남는다. queue/SPI·plan을 제거했다고 세지 않는다.

own FF는 source395→437(+42), host693→683(−10)이다. 공유 cursor 저장은 실제 줄었으나 nonmap region/seed/pending 제어가 추가돼 전체 FF도32개 증가했다. RAM의 FF fallback이나 FSM 추출 실패를 원인으로 설명하지 않는다.

초기 map01은 expected write grant 보강 전17557comb였다. map02는 grant 보강 후17511, map03은 Questa 선언 순서까지 맞춘 최종 소스17511이다. map01/02를 버리지 않으며 최종 기능 검증에는map03 소스를 연결한다. 새 기능 수정·일치 소스 확인에 따른 합성이며 seed/FIT 반복은 하지 않았다. 보드 한도를 초과하므로 FIT/STA를 진행하지 않았다.

## 실제 일정 비교

아래는 CPI1·기존 IRQ/버스 service 모델을 사용한 전체 일정이다. 실제 하드웨어 WCET가 아니다. source02는 압축 source와 호환 ARM만 적용하고338 host를 유지한다. joint03/fixed01/normal01은 동일 최종 결합 RTL·동일 M4 load image를 사용한다. fixed01은 프레임별 시작 시각과 ROM cycle이338 기준과 정확히 같다. 연속 일정은 앞 프레임의 완료 시각 변화가 다음 시작 위상에 반영된다.

|프레임|제한 연속 ms|338 대비 ms|동일 시작·ROM 위상 ms|338 대비 ms|일반 연속 ms|338 대비 ms|
|---|---:|---:|---:|---:|---:|---:|
|905 cold|84.802209634|−14.442553960|84.174717164|−14.442553960|63.762962108|−10.789370526|
|906 cold|114.916120990|−1.796160264|117.973084306|+0.006090836|49.941491604|−0.888307522|
|907 warm|20.690660800|+0.000999988|25.056926586|+0.005727204|11.998037840|−1.412028510|

source02의 제한 연속905/906/907은84.796118798/114.916120990/20.691024432ms였다. 결합 host가 만드는 작은 차이는 ROM 창을 바꾸지 않는다. warm의 source-only와 joint는 동일 절대 ROM 승인 시각258.661601ms이며 post-ROM은3.833794→3.839522ms로5.728µs 증가했다. joint의 시작 시각도6.090µs 늦어져 연속 전체 수치에서 이 증가가 가려진다. 고정 위상은5.727µs 회귀를 드러낸다.

고정 warm 첫 요청은시작 후6.971575ms로 이전 ROM 창 종료6.089722ms보다881.853µs 늦다. warm source 완료는2.692376782ms로 기준2.666649818보다25.727µs 늦지만, 요청은 기준보다 빨라졌다. live decoder/BG 준비의 배치가 달라졌으므로 source 완료와 요청 사이 구간을 별도로 보고, 줄어든 wire를 CPU·대기 시간에서 다시 빼지 않는다. 성공 source wire는564→206B, 출력의 E1·E9 내용과 batch 경계는 기준과 같다. E0/E2 응답·IRQ·polling 차이는 실제 일정에 포함된다.

결합 후보의 제한 연속60Hz 부족분은4.023994133ms, 고정 위상은8.390259919ms다. 기준의4.022994145ms 부족을 줄였다고 볼 수 없다. 일반 ROM에서의 개선을 제한 ROM으로 이식하지 않는다. cold 개선도 모든 프레임의60fps 달성을 뜻하지 않는다.

## 기능 검증 범위

실제 M4 decoder/planner/serializer·IRQ 경로와 RTL source/SPI/2슬롯 queue/host/validator/tile ROM 경합을 사용한다. 일반65816 버스 trace는 기존 기록을 재생하고 map/tile 소비는 C bus model이다. 기존340 decoder의71프레임/압축 oracle 증거와 새 RTL의905–907 실제 wire를 연결하며, 새71프레임 fullpath를 실행했다고 주장하지 않는다. SHIFT는905–907에 없어 별도 synthetic left/right SHIFT·output stall·build STOP 테스트로 검사한다.

초기 source01은 native prepare 중복 적용 오류, joint01은 선언 순서, joint02는 삭제한 EXPAND325를 참조하던 testbench 계측 오류였다. 실패 로그를 보존했다. 계측기는 새 ISSUE의 실제 repeat 경로로 바꾸었으며 RTL의 예전 상태 alias를 되살려 검사를 우회하지 않았다. 최종 채택 여부는 동일 ROM 위상과 연속 일정, 독립 검사·STOP·최종 ACK·VBlank 결과를 함께 보고 판단한다.

최종 source02/joint03/fixed01/normal01은12프레임 관측(고유 기록 프레임3개)이며 전부 통과했다. 매 실제 read에서 파생한 unit 순서가 독립 validator job 순서와 같고, private RAM 쓰기가 정확한 token의 완료 공개보다 앞서 끝났으며 최대 저장 credit은2였다. E1·E9 payload와 batch 경계도338과 동일했다.

오류 주입17개(1/4/5/6/7/11/12/15/16/18/20/23/24/25/26/27/28)가 통과했다. source/E9/ROM/expected RAM/private CRC/record build/공통 WAIT 중 STOP, 조기 최종 ACK, expected 불일치, 주소 범위 초과, 잘못된 token, 완료 공개 전 final scan을 검사했다. 모든 경우 fault 뒤 RAM freeze·완료/lease 차단을 확인했다. case28은expected RAM grant를8클록 막았을 때 write enable과 cursor가 정지함을 확인한 뒤 STOP한다. 이는 grant 복귀 후 정상 완료까지 검사한 별도 사례는 아니다.

aperture의tile ping-pong·wide3418·wrong token·STOP과 raw0/final7개+private STOP/reset1개도 통과했다. 실제 후보 M4 ELF의4개 BG/COMMIT/membership/STOP 검사, synthetic source4프레임의좌우 SHIFT·nonmap·stall·SHIFT build STOP을 통과했다. standalone source test의27개 경고는 사용하지 않는26개 **output** 연결과 연결 개수 경고이며 입력 누락은 없다. 새 전체65816 CPU 실행이나 물리 지속60fps 검증은 아니다.

최종 분석은baseline466파일을 재해시하고 총1369개 증거 경로를 pin했다. `tools/analyze_nes_execute346.py`로 재현하며 `analysis/execute346-verification.json`에 기록했다. 보존 경로는`probes/nes-execute346/{source02,joint03,fixed01,normal01,map03,directed01,armguards01,guards01}`이며 초기 실패도 남겼다. production227/GBC164/saveSRAM은 변경하지 않는다.

## 채택 판단과 다음 경계

346은기능 검사 통과와 별개로 **공동 후보를 거부**한다.338/336의4.022994145ms·1866comb 부족을 유지하며346의수치를 선택 기준으로 바꾸지 않는다. host의−27comb와source 출력 공유만으로345의host1015/source647 감소 예산을 달성할 근거가 없다는 것을 확인했다. SUPPLY 상태 이름이나 FSM 추출 옵션을 다시 조정하는 실험은 근거가 없다.

다음 구조 비교는338의기존 fixed-block scan/history 비교를 사용해 nonmap 반복 형식을 선택하는 방식과340의variable run을 비교하는 것이 타당하다. MASK·SHIFT를 유지하면서 region/offset/run/pending 경로 자체를 실제로 대체할 수 있는지71프레임 wire 최악값·ARM decode 비용부터 확인한다. 이는 아직 구현·채택하지 않은 후보이며 압축 회귀 가능성을 포함한다. host 쪽도 작은 목적지 cursor 공유 대신 packet/admission·queue/SPI·plan의실제 삭제 목록과 독립 검사 유지 비용을 다시 제시해야 한다. 동일 ROM 위상의881.853µs 요청 지연과post-ROM 비용을 함께 줄이지 못하면 일반 ROM 개선만으로 선택하지 않는다. 자동 merge나추가 FIT 반복은 하지 않는다.
