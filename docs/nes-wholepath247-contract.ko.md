# NES247: 같은 스크롤의 전체 비용과 map/slot 갱신 원인

최신 P1 후속은 [raster 의미 투영과 병렬 재배치 경계](nes-relocation247-contract.ko.md)다. 아래 결과는 해당 단계의 근거로 보존하며 다음 순서는 [247 계획](nes-wholepath247-plan.json)을 따른다.

2026-10-18. PR127의 merge `b6958f24fbe2173d0879da07ef56fe3b507b5420`를 fetch한 `origin/master`와 대조했고, 깨끗한 checkout에서 `codex/nes-wholepath-247`을 만들었다. PR127에는 추가하지 않는다.

**P0의 프레임별 비용표·갱신 원인 분석을 완료했다. P1 비교는 진행했지만 전체 여유가 입증된 구현 후보는 아직 없다.** 생산227, 미배치 기능 기준240, 기각241/246은 그대로다. 새로운 RTL/FIT/ARM/SNES 실행이나 설치물이 아니라, 기존 증거를 연결하고 기존 C의 결정을 관측한 결과다. 전체 목표와 P2/P3 진입 조건은 [PR127 회고](nes-pr127-retrospective.ko.md)를 유지한다. 현재 순서는 [247 실행 상태](nes-wholepath247-plan.json)가 갱신한다.

후속 P1의 최신 결과는 [입력·DMA 결합과 bank 수명 검토](nes-schedule247-contract.ko.md)에 있다. 아래 초기 map 모델의5/4burst 결과를 보존하며, 후속 정렬·유효gap 모델은3/2개를 남긴다. 다음 실행 순서는247 계획의 `next_action`을 따른다.

## 산출물과 증거 수준

- [71프레임 비용표 CSV](../analysis/wholepath247-frames.csv): 905..975의 각 행에 phase, generation, 목적 bank, source 조회/생성/대기, SPI 입력·출력·제어, SNES upload/commit과 갱신 원인을 연결했다. `UNKNOWN`은 미측정이며 0이 아니다. 희소 count 열의 빈칸은 해당 분류의 관측 0건이다.
- [검증 요약 JSON](../analysis/wholepath247-verification.json): 합계, 5개 잔여 프레임, P1 표현 비교, 증거 해시. 상세 private 결과와 CSV의 해시도 포함한다.
- `tools/observe_nes_wholepath247.py`: 봉인231 C의 map write 직전·slot 선택 뒤에 관측을 추가한다. 기존355개 geometry/raw/metadata/packets/plans 파일과 cost.csv가 byte exact, 기준 비교4,066,624건을 유지했다. 새 C replay이지 새로운 전체 게임·ARM·65816 시험이 아니다.
- `tools/analyze_nes_wholepath247.py`: 봉인240 cycle, 236 wire 모델, 231 C 비용, 232 실제65816 결과를 frame/generation으로 연결한다. 소비한 입력372개를 pin하고 기존 manifest의 해당 항목만 대조했다. 전체 과거 archive 재검증을 성능 진전으로 세지 않는다.

905는 source와 목적 bank가 cold, 906은 source warm/다른 목적 bank cold, 907..975가 warm69다. 각 프레임의 별도 장면 전환 표식은 없으므로 UNKNOWN으로 남겼다. 관측 창은 첫 레벨 스크롤이며 전체 장시간 장면을 대체하지 않는다.

## 전체 비용을 더하는 방법과 더할 수 없는 값

240의 `total=prepare+blocked+ackwait+transfer`를71행 모두 확인했다. 이미 입력 SPI와 겹친 값이다. 공유 wire 시간에 이 total을 다시 더하면 입력 전송을 중복 계산한다. `prepare`도 ARM/SNES와의 전체 실제 스케줄에서 얼마가 가려지는지는 미측정이다. source의 query와 encoder는 같은 source 도메인/RAM 포트를 사용하며, 두 transport bank가 생성과 이전 block 전송을 겹치게 한다. 그 동작을 전체 경로의 자유로운 병렬성으로 확대하지 않는다.

236 ready4 비용을 입력 payload, block framing, 입력 제어, 출력 DATA payload/envelope, BEGIN/SEAL, plan payload/제어, pattern 제어, final 제어, ready polling으로 분해했다. 매 행 합계가 기존 ready4와 정확히 같다. 입력/출력/상태/plan은 **같은2.625MHz SPI**를 쓰므로 wire 시간은 직렬로 소비한다. 232의 single-tile bulk fixture bytes를236의 grouped pattern 모델에 추가하지 않는다. 두 스케줄은 다르다.

ARM 변환 시간·SPI gap·전체 새 입력 RUN/IRQ 여유·runtime commit·capture-to-display age는 UNKNOWN이다. 232의 `seal_master_cycles`는 fileRPC 대기를 포함하므로 SNES CPU 실행 시간이나 실제 commit 시간으로 환산하지 않는다. 실제232 VBlank 횟수는 재사용한 실행 증거이고, upload `charge=bytes+96/command+fixed`는 별도 모델이다. source/ARM의 준비와 inactive WRAM 수신은 겹칠 가능성이 있지만 단일 ARM 실행·SPI 서비스·VBlank·bank 소유권이 제한한다. 아직 전체 경로 시간 상한은 없다.

| 프레임 | source240 prepare ms | ready4 B / wire ms | map 전송 B → DMA B | OBJ DMA B/명령 | 총 charge / 초과 | 실행 VBlank |
|---|---:|---:|---:|---:|---:|---:|
|952|1.554|4509 / 13.742|480 → 1824|512 / 9|4752 / 560|2|
|954|1.678|5341 / 16.277|720 → 1680|384 / 1|4272 / 80|2|
|955|1.458|4488 / 13.678|704 → 1664|448 / 4|4400 / 208|2|
|963|1.532|4649 / 14.168|800 → 2000|96 / 1|4240 / 48|2|
|968|1.599|4321 / 13.169|528 → 1968|352 / 8|4720 / 528|2|

map 전송은 DATA payload의 펼친 구간이고 envelope를 제외한다. DMA는 유효한 inactive WRAM 사이의 gap을 기존232 규칙으로 합쳐서 더 많은 bytes를 복사한다. 이 표의 DMA/초과값은 기존233과 일치한다. 새 결과는 그 비용을 만드는 map/slot 변화와 같은 프레임의 source/SPI를 연결한 부분이다.

## 갱신 원인: 이번 관측에서 확인한 것

warm69의 map 변경1,362word는 동일 주소의 physical tag 변경674, 전에 기록하지 않은 주소504, 같은 패턴의 팔레트/priority 변경184로 나뉜다. physical tag 변경은 해당 주소의 내용 변화이며 새로운 고유 타일 수가 아니다. 같은 의미인데 slot 번호만 바뀐 map 변경과 같은 tag의 row/alternate shape 변경은 각각0건이다. source row bytes와 exception bytes 변경도0건이었다. 이 정적인 행 특성을 다른 게임·매퍼의 생략 조건으로 사용할 수는 없다.

수평 ring의 공통32열 이상에서 동일한 의미를 가진 행이 다른 group ordinal에 나타난 경우는 총2건, 잔여5프레임에서는0건이다. 따라서 group 재배치를 이 창의 주원인으로 선정할 근거가 없다. 이는 모든 group 이동의 부재 증명이 아니라 명시한 일치 기준으로 조사한 결과다. 225 ringmap과211 resident slot을 새 기능으로 다시 만들지 않는다.

map의 현재 변경16B granule은 합계1,079개, 실제 전송은1,915개다. 그중836개(43.66%)는 현재 프레임 변경 없이 목적 bank를 따라잡는 전송이다. 1,915개 모두 실제 목적 bank와 다른 byte를 포함했으며, granule 전체가 이미 같은데 전송한 사례는0개였다. 다만 granule 내부와 DMA gap에는 같은 byte가 포함된다.

**955는 현재 map 변경0word인데 목적 bank의100byte가 달라44granule/704B 전송이 필요하다.** 마지막 표시와 같다는 이유로 이 전송을 생략하면 틀린 화면이 된다. 이번 분석의 부정 대조다. dirty union/최종 displayACK→commit을 제거하는 최적화는 허용하지 않는다.

pattern write416건/9,744B는 강제zero69건/1,104B, 같은 key의 다른 bank 채우기121건/2,560B, 빈 key entry에 할당188건/4,864B, 기존 key 교체38건/1,216B다. 기존 키의 retained hit는6,714건이다. slot 선택 관측은 같은 프레임 exact-key dedupe 뒤에 있고 dedupe 호출을 hit로 중복 집계하지 않는다. nonordinary shape write는0건이다. 원인별 합계가 실제 plans/tile bytes와 매 프레임 일치한다. zero 반복 제거만으로 큰 구조를 해결했다고 간주하지 않는다.

## P1: 세 경로의 비교와 실제로 계산한 표현 모델

| 후보 | 이번 근거·이득 범위 | 자원·시간 제약 | 판정 |
|---|---|---|---|
|A:240 전용 query/encoder 제한적 단순화|source row/exception 변화0은 활동량 근거. query·고정5741B scan의 일부가 필요 없는지 조사할 수 있음|전체15898LE/1003LAB/54M9K. 최소490LE/40LAB과 확장 여유를 회수할 실제 공유안 없음. wire5341B/5bursts도 남음|미선정. sequencer 자동 선택·opcode/seed/FIT 반복 금지|
|B:fetch 의미를 보존하는 field/row 전달|고정 배열의 map17,890B·raster30,340B 변경을 의미별로 구분. 압축된 표현은 byte동일성 대신 복원 의미로 판단|수집 시점의 비교/보관/overflow와 MMC4/5·CHR-RAM 의미를 실제 포트/제어 비용으로 제시해야 함. PPU write만으로 복원 불가|미선정. 아래 출력 map 묶음은 표현 비용의 제한적 모델이며 입력 RTL은 아님|
|C:입력·출력·변환 위치 공동 변경|954 map 출력1328clock-B를 실제 로컬 생성/전달로 옮긴다면 그 항목을 제거할 여지가 있음. 무료 신규 제어를 가정한 잔여4013B|새 로컬 map 작업957cell/frame 및 slot/row 의미, source 경로 교체, parallel aperture 경합/ROM 접근, FPGA/SNES 계산·메모리는 UNKNOWN. ARM→SPI 재공급은 우회 아님|미선정.236의 출력-only 기각을 전체C 불가능성으로 확대하지 않음|

두 출력 map 표현을 작은 Python encoder/parser로 모델링했다. 모두 **기존 목적 bank의 완전한4096B map**으로 복원됨을71프레임 확인했다. 기존19B packet envelope, payload240B 한도, 동일 ready1/4 시나리오와 같은 DMA setup96을 가정했다. 새 protocol 버전·CRC/cancel decoder·실제65816 시간은 구현하지 않았다. cold 두 bank는 기존 full literal을 유지하는 조건이며 아래 표는 warm69만이다.

1. **16B 묶음:** 기존 dirty granule을 `(offset16, value16B)`로 묶어 packet당13개. 유지 상태 증가0B. 새 granule 탐지 기능이 아니라 이미 있는231 dirty 목록의 전송 표현 변경이다.
2. **word 변경:** 마지막 표시와 달라진 word를 양bank pending에 누적해 `(offset16,value16)` packet당60개로 전달. 2048word bitmap256B×2가 필요하여 기존 map bitmap32B×2 대비 **448B 증가**한다. 별도 inactive map4096B 복사나 미래 프레임을 보지 않는다. SNES 최종 bitmap/coverage와 cold·partial 수명은 구현 검증이 필요하다.

| 표현 | 최대 ready4 B | 최대 ready1 B | 최대 SNES charge | charge4192 초과 | ARM 추가 상태 |
|---|---:|---:|---:|---:|---:|
|기존236/232|5341|5941|4752|5/69|0|
|16B 묶음 모델|4759|4939|4752|5/69|0|
|word 변경 모델|4219|4359|4724|4/69|448B|

16B 묶음은 wire 여유를 키우지만 마지막 DMA burst를 해소하지 않는다. word 변경도 다른 프레임을 추가 실패시키지는 않지만952/954/955/968이 남는다. 963은4178charge로 겨우14 아래다. 233 여유1616B에서448B를 빼면1168B, 최소1024 대비144B뿐이며 새 입력 RUN/IRQ 비용은 아직 포함되지 않는다. SNES232 body는3910/3936B, 기존 여유26B라서 새 decoder를 단순 추가할 공간이 있다고 가정할 수 없다. 두 표현 모두 FPGA 면적을 줄이지 않는다. 따라서 **어느 것도 단독 P2 후보로 승인하지 않는다.**

## 다른 장면 자료의 재사용 범위

| 기존 자료 | 사용 가능한 범위 | 이번71행과 합치지 않은 이유 |
|---|---|---|
|229 capture96frames/70scroll|첫 레벨 입력·PPU bank/mask·RGB 기준|230 이후 end-to-end geometry는905..975의71개만 있음|
|178 transition/clip|실제 코어의 START 뒤 mask00/18 및 선택 화면 거부 원인|첫 레벨 지속 스크롤·새231/240 shared pipeline 비용 아님|
|225·227 synthetic30frames|scroll/wrap/raw/bank 전환의 C→65816 픽셀 기준|실제 SMB3 프레임 번호와 연결되지 않은 합성 자료|
|181 rawsteady|7행 raw/큰 변경·STOP 등 기존 소비기 경계|옛 소비기·옛 예산.232/240 비용으로 이전 불가|
|227 hardware60.06s|게임·사운드·메뉴 정상,465 display 완료와 구간 로그|영상과71frame의 같은 캡처 시각 대응이 없음.7.74/s는 제어된 FPS가 아님|

자료는 있으나 추가 실제 heavy scene의 새 전체 경로 표본은 아직 없다. 이를 채우려고 실기227/044나 오래된 합성 suite를 재실행하지 않았다.

## 다음 작업의 구체적 경계

P0은 이 범위에서 완료, P1은 부분 완료다. 다음은 **16B 묶음의 wire 여유 + 실제 inactive pattern/map 작업의 선행 가능 구간 + source240를 대체/축소하는 처리 위치**를 한 스케줄과 상태 소유권으로 묶어 검토한다. 새로운 후보를 확정했다는 뜻은 아니다. 특히952/968의 OBJ9/8명령과 map gap 복사를 마지막 VBlank 앞에 옮기려면, 단순히232 final coverage를 앞당기지 말고 각 구간의 bank/token/유효 bytes·마지막 쓰기 시점·STOP drain을 현재 경로에서 확인해야 한다. 기존 source/ARM/SNES 작업의 겹침을 실제로 유지할 수 있는지와3910B ROM 교체 범위를 함께 제시한다.

그 결과 전체 LE/LAB/M9K, 새 입력 RUN/IRQ, SNES 코드/WRAM, SPI gap·실행시간·mapper 여유를 가진 **한 후보만** P2로 선정한다. 이번 word bitmap448B를 근거 없이 생산에 추가하거나, 단순화240 FIT를 먼저 돌리거나, source/표시 ACK를 합치지 않는다. 이번 분석에서 wire 개선만으로는 잔여 burst가 없어지지 않는다는 중단 근거를 확보했다.

## 재현·실패 보존

private ROM·봉인 probe가 필요하며 공개 clone 단독으로 재현된다고 하지 않는다. 새 빈 출력 디렉터리에서 observer를 실행한 뒤 analyzer를 실행한다.

```text
python tools/observe_nes_wholepath247.py --out <new-private-observer> --rom <private-SMB3-J-ROM> --gcc <existing-gcc.exe>
python tools/analyze_nes_wholepath247.py --observer <observer> --out <new-private-result.json> --summary <new-summary.json> --ledger <new-ledger.csv>
```

선택은 observer03/analysis06. observer01은 sandbox의 compiler 시작 WinError623, observer02는 `.inc` 복사 누락으로 compile 실패했다. 해당 디렉터리·build log는 보존했다. observer03은 include 복사와 narrow-C용 ASCII short path를 사용한다. analysis01의 괄호 문법 오류 뒤 analysis02 기본표,03 표현 모델,04 manifest 검증,05 공개 요약/CSV,06 CSV의 LF 출력으로 확장했다.05와06의 수치·모델 결과는 같다. 앞선 결과를 덮어쓰지 않았다. RTL/Questa/license/FIT, 새ARM·SNES·실기·FWZIP은 실행하지 않았다. 원본 ROM/trace/binary/raw log/license와 관측 map의 physical identity 값은 공개 Git에 넣지 않는다.
