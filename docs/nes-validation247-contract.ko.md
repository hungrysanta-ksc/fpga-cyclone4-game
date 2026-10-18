# NES247: 범위 검증 실행과 map·manifest 공동 예산

기존16bit 범위 bitmap 갱신을 현재 수신기에 이식해 실행했다. 본문은5818→5886B(+68), 추가 영속 상태는0B다. warm69의 map 외 mark 합계는100.805→85.730ms로14.95% 감소했다. 조건부 wire+측정 routine 합의 최대는25.163→24.175ms,16.67ms 초과는27→26프레임이다. **전체60fps 구현은 아직 아니다.**

map manifest만 압축하는 모델도 현재 map decoder를 유지하면14프레임에서 새 manifest decoder 시간이0이어도 부족하다. 따라서 이를 독립된 새 opcode로 구현하지 않았다. 범위 검증+exact packed map+정확한 manifest 압축을 함께 계산하면 가장 빠듯한954에서 **두 새 decoder에 남는 시간은1.748512ms**다. 실제 두 decoder 실행 시간과 나머지 전체 경로 비용은 아직 없다.

## 구현과 수명

기존 `nes_rangemark247.py`의16bit prefix mask 방식을 재사용했다. 한 번에 최대16개 unit의 received 중복 여부를 확인하고, received 및 선택된 target-valid word에 OR한다. 기존 per-bit 반복을 대체하며 section admission·append·coverage·service·최종 display ACK는 유지한다. 새 알고리즘으로 세거나 과거4KiB 크기 gate를 재사용하지 않는다.

현재 received는7E1280..1325의166B, valid는7E1340..13e5와13e6..148b의각166B다.16bit 단위 주소를 짝수로 맞추고 bank offset0/166을 사용한다. 최대 unit1327에서 마지막 word는164..165라서 옆 bank를 침범하지 않는다. 실제 정상 자료가 시작 위치mod16의0..15 모두를 통과했다.

범위가 여러 word를 가로지르면 앞 word 갱신 뒤 뒷 word의 중복을 발견할 수 있다. 이때 부분 staging은 되돌리지 않고 기존 terminal rejection으로 이전 표시를 보존한다. 실패 뒤 새 정상 packet을 받아 이어가는 경로는 없다. immutable mailbox, 두 bank 선택, 초기화/STOP 무효화, 최종 display ACK 소유권은 바뀌지 않았다.

34B prefix table을 포함한 순증은68B다. DP70/72/74의 기존 mark scratch를 재사용한다.6KiB 저장 설계의5984B 본문 공간에 대입하면98B가 남지만, **4/5/6KiB나98B는 절대 한도가 아니다.** 새 이미지의 storage MAP/FIT/STA는 실행하지 않았다. 기존240의 미배치와 전체 M9K/mapper 여유 문제도 남는다.

## 실제 검증

SELECT `validation-build02/test02/fault01/protocol01/coverage01/analysis02`.

- C+65816/Mesen 실제71 display commits/1100 ACK, C reference4,066,624 checks, map290,816B와71개 command 목록 일치.
- 정상387개 range chunk마다 independent bit별 oracle로 received166B+valid 양 bank332B 전체를 대조했다. 합192,726 byte checks, 양 bank0/166 및 시작 정렬0..15 모두 관측했다. 대상 외 bit·반대 bank도 비교한다.
- 새 overlap6건: BG/OBJ/CGRAM/raw 중복, BG/OBJ의 첫16bit 경계를 일부 처리한 뒤 발생하는 중복. 실제 표적 packet의 marker 진입·오류 반환을 확인하고 두 partial 경우는 다음 chunk 진입도 확인했다. 모두 이전 display 보존·terminal rejection.
- 기존 프로토콜·STOP12건과 pattern coverage8개 lane에서 미수신 validity 거부를 새 바이너리로 통과했다. 총26 오류·STOP 시험이다. 이전255mask/38fault 전체를 이번 바이너리에서 다시 실행했다고 주장하지 않는다.
-426DMA/132,270B,178 pattern bulk chunks/12,944B, 최대DMA1312B/목록13개, warm multi-VBlank952/955가 같다.
-752개 미초기화 주소는 기존 독립 oracle이 허용한 미사용 pattern gap에만 속한다.

build01은 이식 source assertion에서 old validity operand 수를3으로 잘못 예상해 중단됐다. 실제 load/store2개에 맞춰 assertion을 수정한 build02가5886B다. 실패 설명과 pass 디렉터리를 보존한다. test01은 정상 PASS, test02는 같은 바이너리에 bitmap 전체 대조 관측을 추가한 PASS다. analysis01 PASS 뒤 joint355개 비교와 coverage8 검증을 더한 analysis02를 선택했다. 중간 결과를 덮어쓰지 않았다.

## 실제 시간 변화

|warm69|5818B 기준|5886B 범위 갱신|
|---|---:|---:|
|non-map mark 합계ms|100.805084|85.729797|
|non-map mark 최대ms|3.251996|2.721016|
|map mask 합계ms|329.030552|329.040423|
|manifest 합계ms|63.026725|63.026725|
|coverage 합계ms|72.356403|72.356403|
|조건부 전체 합계ms|1149.060288|1133.994872|
|조건부 최대ms|25.162990|24.175062|
|조건부16.67ms 초과|27/69|26/69|

짧은 범위에서는 준비 비용이 더 들어12프레임의 mark 시간이 증가했고 최대 증가는0.070772ms다. 따라서 모든 frame이 빨라진 것은 아니다.954는0.988766ms 절약했다. 같은 map routine의 미세 시간 차이도 실제 관측값 그대로 보존하며 완전히 같은 clock trace로 간주하지 않는다. manifest/coverage 합은 정확히 같다.

조건부 합은 실제 mark/mask/manifest/coverage와 기존 ready4 wire 시나리오를 더한 것이다. source/ARM, 나머지 dispatch/copy, 전송 공백, 최종DMA/display를 전부 포함하지 않고 실제FPS나 모든 overlap 일정의 한도가 아니다.

## 정확한 manifest 압축 모델

가상 mode3 packet에서 각 token의 하위7bit+1은 출력 길이1..128이다. 상위bit1은 zero run,0은 뒤따르는 literal이다. 모든 token은 packet 안에서 완결되고 packet offset은 누적 decoded offset과 같아야 한다. 끝에서 정확히256B가 되어야 하며, **zero로 생략한 위치까지 현재 receipt와 비교해야 한다.** 누락이나 불필요한 수신을 허용하는 subset/hash 검사가 아니다.

기존 dense240+16과 압축의 실제 payload+packet framing 비용을 비교해 더 작은 쪽을 고른다. cold dense는 기존 형식을 유지한다. warm69 모두 모델에서 압축이 선택됐고, mask를 유지한 ready4 합계 절감은13,815 clock-byte다. bitmap71개 재구성과 Python malformed7건 및 전체zero/전체FF 양성 검사를 통과했다. 이는 실제 새 sender/CPU decoder·version 호환·STOP 시험이 아니다.

현재 map decoder를 유지하면 압축 manifest의 새 decoder 허용 시간이14프레임에서 음수다.954는−6.095155ms다. 그러므로 manifest 압축만 추가해 해결됐다고 볼 수 없다.

## 세 변경의 공동 비교

앞선 spantrade02의5가지 map 형식과 이번 실제 mark/coverage 시간, 각 형식의 **실제 확대된 쓰기 집합**으로 만든 manifest 모델을 결합했다. 넓은 span에 원래 sparse manifest를 붙이지 않았다. ordinary DATA ready grouping은 map/manifest packet 수를 동시에 바꿔 다시 계산하며 op7 bulk를 이중 계산하지 않는다.

`두 decoder 허용 시간 = 1000/60 − 새 ready4×8/2625 − 실제 새 mark − 실제 coverage`

|warm69 모델|ready4 최대|두 decoder 허용 시간 최소ms|음수 frame 수|
|---|---:|---:|---:|
|literal exact64|4974|−0.994345|3|
|packed exact64|3976|1.748512|0|
|packed gap16/64|4027|1.593083|0|
|packed gap96/64|5884|−3.696280|17|
|packed gap96/236|5800|−3.440280|15|

355개 조합 중 exact packed가 추가 값 전송 없이 가장 나은 최소 여유를 보인다.954는 map45records/2packets,manifest111B/1packet이다. **1.748512ms는 두 decoder가 공동으로 사용해야 하는 잔여 상한**이며, 빠져 있는 source/ARM/dispatch/대기 등을 위한 안전 여유까지 확보한 수치가 아니다. 나머지 회로·메모리 비용도 승인되지 않았다.

## 다음 작업

전체 후보 선택 전, exact packed map+정확한 compressed manifest의 **공동 decoder**가 이 상한에 접근 가능한지 packet admission·범위 검사·receipt·복사/DMA 설정·service·최종 검증을 포함해 계산하고 최소 경계에서 실제 측정한다. 기존 generic DATA DMA/op7 pattern bulk를 새 기능으로 세지 않고 immutable mailbox 수명과STOP 간격을 명시한다.1.75ms를 넘거나 전체 미측정 비용을 위한 여유가 없으면, 또 다른 작은 bitmap/opcode 수정 대신 전송·변환 위치나 겹침 경계를 다시 비교한다.

5886B 결과는 개선 근거로 보존하되 P2 전체 경로 후보는 미선정이다. source449/rowshift·ROM 저장·mapper 공동 배분,952 순서/9554198>4192,새 입력 ARM RUN/IRQ,firstfault·CDC/IO·final display lease-retire가 남는다. 생산227·functional240 미배치·기각241/246·GBC164·save SRAM 및 기존 자료를 보존했다.

재현 도구는 [builder](../tools/nes_validation247.py), [정상 oracle](../tools/test_nes_validation247.py), [overlap 오류](../tools/test_nes_validationfault247.py), [coverage 오류](../tools/test_nes_validationcoverage247.py), [분석기](../tools/analyze_nes_validation247.py)다. 공개 [집계](../analysis/validation247-verification.json), [실제71프레임](../analysis/validation247-frames.csv), [공동355비교](../analysis/validation247-joint-frames.csv)에 모델과 실제 실행을 분리했다. 원본 ROM·덤프·실행 로그는 private probe에 보존한다.
