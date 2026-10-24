# NES328 — ARM 선행 manifest 분리와 expected/receipt 진행 공유

325의 단일 압축 확장, tile 두 chunk 선행 생산, native65816 소비를 기준으로 삼는다.327 ARM만325 RTL에 적용한 경로와,327 직접 expected scan에328 주소·진행 공유를 추가한 경로를 별도로 실행한다. 같은 ARM load image를 사용하므로 두 경로의 차이는 RTL과 이에 따른 실제 IRQ·credit 일정이다.319는 역사적 비교 기준이다.

재현 도구는 `probe_nes_joint328.py`다. `NES328_ARM_ONLY=1`이 유지할325 RTL+선행 ARM 경로이며,0 또는미설정은미채택공동RTL 진단이다. `NES319_FIXED=1`과 `--rom-window 1`은고정시작/ROM 위상,고정해제후window1/0은제한/정상연속일정이다. 실제실행인자와raw log는 `probes/nes-joint328/batch01.ps1`,추가오류검사는 `extra-guards01.ps1`에보존한다. 기본실행만으로모든새오류검사가선택됐다고가정하지않고joint cases1..13과ARM cases3,5,6,10,11을명시한다.

## 삭제·유지 경계

host ingress의 별도9bit `manifest_byte313` 저장을 삭제했다. header 검사를 완료한 뒤에만 `active305.start`를 expected 진행 위치로 재사용한다. op15/10/11의 저장 위치는 이 레코드에서 만든다. 원래 header start의 순서·범위 검사는 덮어쓰기 전에 유지하고 다음 packet의 record load가 새 start를 공급한다. 별도 header 복사나 주소 복원 RAM은 추가하지 않는다.

validator의 별도12bit receipt cursor를 삭제하고 clear/expected cursor를12bit로 넓혀 공유한다. receipt의8단위 진행과 final expected의1단위 진행은 같은 레지스터를 사용한다. receipt 완료에서는 반드시0으로 돌려놓은 뒤 V_ACTIVE로 돌아가며, final scan은0에서 시작해24display+166ordinary+256map을 검사한다. receipt의 exclusive end와 map 순서 경계는 유지한다. count 공유가 범위 검사를 대신하지 않는다.

expected queue RAM의 B포트는 ingress 저장과 terminal scan이 순차 소유한다. actual receipt/persistent validity/CRC는 기존 phase RAM 포트를 사용한다. 두 RAM의 동시 접근을 한 포트라고 계산하지 않는다.327의 동기 E_READ/E_CAPTURE, independent expected와 실제 staging read/consume CRC의 분리, 최종12display reads/token ACK를 유지한다. STOP·fault는 진행과 RAM write를 차단한다. ARM 선행 발행은 storage credit만 반환할 수 있고 actual consume 또는 최종 seal을 대신할 수 없다.

따라서 이번 변경은 두 중복 진행 레지스터와 그 주소 입력을 실제로 교체하지만, ingress RLE FSM·receipt read/modify/write·checker FSM 전체를 삭제한 것은 아니다. shared cursor의 단위 선택·load enable·주소 선택 비용도 전체 합성에 포함한다. 레지스터 감소를 조합 논리 절감으로 간주하지 않는다.

## 검증과 비용의 적용 범위

고정 시작/ROM cycle 비교와 제한·정상 연속 일정을 각각 실행한다. 실제 Cortex-M4 명령, SPI 응답, IRQ,2슬롯,ROM backend,staging 경쟁을 함께 진행한다. CPI1/84MHz 모델이며 물리 ARM 계측은 아니다.65816은325에서 실행한 동일536B ROM과 bus trace를 재사용하며 이번에 새 live CPU 실행이나 전체 pixel 검증을 했다고 주장하지 않는다. VBlank/final ACK 경계는 같은 소비 trace 및 RTL 검사에 포함한다.

opcode별 payload와 E9 byte 동일성, ELF PT_LOAD 동일성, simulation/wholeLite 입력 hash, 독립 expected·소비CRC 변조, source/plan/E1/E9/ROMpending/확장/scan/receipt/expected저장 중 STOP과 RAM freeze를 검사한다. 전체 회로는 Quartus Lite MAP이며 FIT/STA 및 실물60fps 달성 판정은 포함하지 않는다.

## 실측 결과

제한연속 ARM 단독의 마지막consume은279.302716ms,완료는279.655644ms로tail0.352928ms다. 현재시작과앞부분일정을고정하고이tail전체를0으로두는민감도에서도초과1.111869571ms가남는다. 이는새실측이나전체스케줄의불가능증명이아니며,최종검사구간만의최적화예산이목표에부족하다는현재일정의산술이다. ROM 공급·DMA 준비 등앞부분의일정개선도필요하다.

결과는 `analysis/joint328-verification.json`에 소스·실행·전체MAP hash와 함께 확정했다.328 전체MAP은22,691LE/17,876comb/9,005FF/307,808bits로325 대비+74LE/+74comb/−16FF/0RAM이다. 후보 회로 부족은2,468comb이며325의2,394보다 나쁘다.327 대비로도+64comb/−19FF다. 회로 공유안은 이 비용 때문에 채택하지 않는다. ARM만 적용한 경로의 회로 비용은 RTL 동일성 확인 후325 전체MAP과 연결하며 새 절감 수치로 세지 않는다.

## 완료한 분리 검증

|907 일정|325|325 RTL+선행 ARM|328 공동 RTL+선행 ARM|
|---|---:|---:|---:|
|동일 시작/ROM 위상 ms|26.186594848|25.968779280|25.963779340|
|제한 연속 ms|18.314098410|18.131464238|18.131464238|
|정상 연속 ms|14.370236646|14.338555208|14.328964414|

채택하는 시간 후보는325 RTL+선행 ARM이다. 회로는기준과완전히같으므로17,802comb/2,394부족이다. 제한연속의60Hz 초과는1.464797571ms다.328 공동RTL은시간추가효과보다회로회귀가커서미채택이다. 동일위상 비교의ARM 단독이득과RTL 추가효과는다음과같다.

|frame|ARM 단독 duration 차이 ms|RTL 추가 duration 차이 ms|
|---|---:|---:|
|905|-0.031908708|-0.005045394|
|906|-0.035135942|-0.004999940|
|907|-0.217815568|-0.004999940|

제한연속은이전프레임완료가다음시작을움직이므로절대완료와duration을분리한다.

|경로|907 시작 ms|첫 BG 출력 ms|완료 ms|map manifest release ms|
|---|---:|---:|---:|---:|
|ARM만|261.524134|274.905315|279.655644|271.438327|
|공동RTL|261.519134|274.905315|279.650644|271.433315|

|경로/일정|SPI 3프레임 B|SysTick/EXTI|관측 stack B|
|---|---:|---:|---:|
|arm-fixed01|21819|36/68|1304|
|arm-window01|21819|27/71|1304|
|arm-normal01|21441|18/62|1304|
|joint-fixed01|21819|36/68|1304|
|joint-window01|21819|27/71|1304|
|joint-normal01|21441|18/62|1304|

ARM PT_LOAD는분리경로와공동경로에서동일하다. text29,394B/BSS47,376B/data0B이며325보다408B/28B 증가했다. BSS와stack은시험ELF 범위이고production SRAM 보증이아니다. ARM만적용한경로의모든RTL hash가325와정확히같고,공동경로의변경RTL은wholeLite 입력과결합했다. opcode별payload/E9 및CPU trace도비교했다.

공동경로13fault는기존11검사에receipt RAMwrite 중STOP과expected ingress 저장중STOP을추가했다. ARM만적용한채택후보는partialE1/조기finalACK/독립expected 변조/실제consumed CRC 변조/expected 저장중STOP의5fault를새일정에서검사했다. expected 변조fault3,CRC 변조fault7,STOP·조기ACK fault4를확인했고RAMfreeze·lease/seal/finalACK 비노출을검사했다. aperture의tile pingpong/3418B/wrong token/partialSTOP도PASS다.

327→328 host 자체는2,410→2,436comb/717→708FF,validator는1,040→1,061comb/202→192FF다. 두경로에서FF19개를없앴지만두블록comb47개가늘었고나머지mapping까지전체64개가늘었다. 주소단위가서로다른clear/receipt/expected 진행의선택과active record 추가load를남긴구조이므로register 공유만으로큰회수예산을잡으면안된다. 정확한합성물리원인전체를단정하지는않는다.

325 기준host+validator3,426comb에서이둘만으로부족2,394를해결하려면합계1,032까지줄여야한다. 이번328은3,497로오히려늘었다. 다음구조검토는제거할제어모듈·RAMport·신호소유권을명시하고BG ROM 대기와함께예산을잡는다. 단순카운터·FSM·seed 반복실험은후속목표로잡지않는다. 새FIT/STA나실물60fps 승인은없다.
