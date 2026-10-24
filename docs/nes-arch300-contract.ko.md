# NES300 — 공통 descriptor 끝 주소·정렬 RAM·OBJ 선행 공급

NES299 구조 검토를 실제 RTL/ARM에 연결한 PR131의 후속 실험이다. production227/GBC164/saveSRAM은 변경하지 않는다. 기준298, 기능289, 성능287과 기존 ARM296을 보존한다.

## 실제 교체 범위

`nes_arch300.py`는298 생성 RTL에 다음 변경을 적용한다.

- host의7개 `startpos+outlen` 표현을 원본 descriptor의17bit exclusive end로 통일한다. 같은 끝 주소가 일반 명령의 domain/alignment와 receipt mapping에 사용된다. overflow를 좁은 합으로 숨기지 않는다.
- 일반 descriptor receipt를 `first,count` 대신 `first,end`로 전달해 `end-first` 후 validator의 `first+count` 복원을 없앤다. 공유 포트의 map 경로는 원래 count 의미를 유지한다. validator는 descriptor 모드에서 `end>first`와 독립 domain을 확인하고, map 모드에서 기존 count·순서 검사를 유지한다.
- 기존 immutable header와 DMA view는 유지한다. 이것은 원본 범위 산술·전달의 공통화이며, NES299가 검토한 모든 admission/header/queue 제어를 하나의 새 record로 대체한 구현이라고 부르지 않는다. 외부로부터 받은 unchecked end를 신뢰하는 변경이 아니다.
- phase RAM을 valid0=0,valid1=256,CRC=448,receipt=512,H2=680,offset=712,map=768로 재배치한다. CRC/bank base를 정렬하고 기존 주소 선택기가 이 배치를 사용한다. 1KiB/두 clock 포트 및 source scratch512..1023을 유지한다. 별도 FPGA RAM을 추가하지 않는다.
- frame clear는512..677와768..1023의422B만 지우며 H2/context를 보존한다. raw0 무효화는148..165와404..421로 바꾼다. 초기 clear는1024B이며 기존818B보다206host cycles 늘어난다. 이 초기화는 source admission 전이고 per-frame clear 바이트 수는 동일하다.
- manifest의 압축 cursor·확장 cursor·RLE·checked_byte, 독립 persistent/fresh/map 비교, CRC tap, STOP write gate와 최종 ACK는 유지한다. 원래 byte echo를 다시 도입하지 않는다.

`native()`는 기존 ARM296 실행에 BG E9 송신 직후 `service296()`를 연결한다. prefill 중 실제 packet을 먼저 송신한 뒤 OBJ 생산을 진행하고, 기존 최대두 planbank 공급 루프가 증가한 plan 길이를 보도록 한다. 기존 E2 대기 서비스는 남겨 fallback 역할을 한다. 새 plan buffer·credit·별도 실행 프로그램은 없다. 기존 mixed batch 예약/정렬, BG 부분완료와 최종 END 구별을 유지한다.

## 독립 검사와 관측

원본 명령 순서와 payload, metadata8570B,receipt754B,CRC64B,실제 map consume와 receipt 수,4credit,최종ACK 및 finish→commit을 기존 oracle와 비교한다. 주소가 바뀐 논리 oracle 읽기만 변환하며 STOP 이후 비교는 **물리1024B 전체**를 유지한다. host RAM 쓰기는 새 유효 영역과 초기화 상태로 제한하는 assertion을 둔다.

새 guard68/69는 descriptor end가 시작 이하/독립 domain 밖인 경우를 주입한다. frame clear 중H2/context680..715에 쓰면 즉시 실패하는 assertion도 추가한다. 기존 독립 CRC 누락·범위/manifest 오류·STOP·최종ACK guards를 유지한다. 실제 source/phase 입력 fixture는298과 동일하다.

실행과 전체 Lite 합성은 동일 descriptor/RAM RTL에 결합하고, 제한 ROM에서 기존 ARM296 ELF를 그대로 쓴 분리 실행도 비교한다. 이는 ARM 공급 변경과 RTL 변경의 효과를 구별하기 위한 것이며, 다른 후보의 유리한 구간만 합산하지 않는다.

## 초기 실패 기록

transform01은 생성기에서두 개의`cursor==817`을 단일 치환으로 취급하여 사전 검사가 중단됐다. V_CLEARALL/V_CLEARFRAME을 각각 지정해 수정했다. test01은 testbench가 옛`ordinary_count` 포트를 참조해 elaboration 실패했고, test02는 옛RAM 상한867 assertion 때문에 초기 clear에서 실패했다. 모두 보존한다. 이 실패를 통과 결과로 세지 않는다.

제한된 shell에서 FLOAT wrapper의 PC 식별이 실패했으나, 기존 승인된 권한·동일 라이선스 경로에서는 정상 실행됐다. 새 라이선스 구매·전역 설정 변경은 하지 않았다. 라이선스/hostID/private log는 Git에 넣지 않는다.

## 범위와 판정 원칙

actual M4 명령·IRQ·shared SPI·tile ROM 경쟁을 실행하지만 시간은CPI1/84MHz,source timing replay,IRQ 진입/복귀 할당,기존 ordinary65816 trace와 map/tile/display bus 모델을 포함한 일정이다. 실물 MCU 사이클/WCET·전체 live65816·fullRUN·최종71/heavy7 일정·FIT/STA·실물60fps가 아니다. native71 생산 성공과 최종 통합71프레임 성공을 구분한다.

whole Lite 목표는15408comb,시간 비교는16.666667ms다. 정상/제한 각각의 회귀와 새 비용을 그대로 보고하며 소규모 주소/FSM/seed 합성 반복으로 목표 달성을 추정하지 않는다. 실제 수치·선택 실행·최종 판정은 아래 결과에 기록한다.


## 합성 결과와 ARM 크기

|항목|298|300|변화|
|---|---:|---:|---:|
|whole Lite LE|22583|22578|-5|
|whole comb|17683|17678|-5|
|FF|9022|9022|0|
|RAM bits|307808|307808|0|
|comb 부족|2275|2270|-5|
|host own comb|2100|2103|+3|
|validator own comb|1327|1310|-17|
|ARM text bytes|27458|27490|+32|
|ARM BSS bytes|47100|47100|0|
|live observed stack bytes|1288|1288|0|

host+validator의14개 감소와 wrapper/다른 계층의9개 증가가 합쳐져 whole5개 감소다. parent/child 계층을 중복 합산하지 않는다. 두 FSM은 정상 추출됐다. 처음부터 목표한2275개 중0.22%만 회복했으므로 소규모 RAM 정렬/범위 산술만으로 회로 목표를 해결했다는 주장은 불가능하다. FIT/STA는 실행하지 않았다.


## 실제 ARM·IRQ·ROM 일정

|조건|298 ms|300 ms|차이 ms|
|---|---:|---:|---:|
|정상905|79.689998254|80.268082226|+0.578083972|
|정상906|56.212189082|56.551957732|+0.339768650|
|정상907|15.473814312|15.532449972|+0.058635660|
|제한905|104.876059654|104.876059654|0|
|제한906|116.900688084|116.900733538|+0.000045454|
|제한907|17.468381286|17.468335832|-0.000045454|

제한907 초과는0.801669165ms다. 한 NES clock(45.454ns) 차이를 descriptor 처리 가속이나 실물 시간 이득으로 계산하지 않는다. 정상907 여유는1.134216695ms로 줄었다. 정상907 ARM697093→697636명령, SPI1176→1188B; 제한907 ARM699344→699406명령, SPI1236B 동일이다. E9 wire payload는 기존 계획 순서를 유지한다.

정상907의 실제 service trace에서 `before_size=47,plan_at=41`이다. 이6B는 내부 plan stream의3B batch header와3B BG 부분완료 명령이며 SPI6B를 의미하지 않는다. 새 service가49,175명령을 수행하는 동안 이 BG 완료 packet은 아직 송신되지 않는다. 즉 ‘BG 데이터 batch 송신 직후’는 ‘BG 부분 완료까지 발행한 뒤’와 다르다. cold/normal 회귀와 일관되는 의존성이다. 시간 차이 전부를 이 명령 수로 단순 환산하지 않으며, 제한 ROM에서는 변환 창/후속 소비가 지배하여 거의 같은 완료 시간이 된다.

따라서 현재의 성공한 E9 직후 service 호출을 채택하지 않는다. 기존296 대기 서비스를 참조로 유지한다. 수정 검토가 필요하다면 BG 부분완료 발행·실제 DMA 공급을 막지 않는 실행 위치와 유효 ROM 창을 함께 다뤄야 하며, 그 변경만으로 회로2270개까지 해결한다고 가정하지 않는다.

## 판정

기능 보존과 회로5개 감소는 확인했지만, 정상 시간은 회귀했고 제한 시간 초과는 해소되지 않았다. NES300을 시간·회로 공동 목표 해결안으로 **미채택**한다. host+validator만3413comb이고 다른 회로를 유지하면1143comb 이하가 필요하다. host2103개를 전부0으로 가정해도 전체는15575comb로167개 부족하다. host 단독 정리나 같은 주소 산술의 미세 수정에 전체 회복을 배정할 수 없다.

검증된 원본 descriptor 범위 의미와RAM layout/clear/STOP 증거는 보존하되, broader packet/header/queue/plan 제어의 실제 제거와 새로운 독립 검사 경계를 포함한 구조 근거 없이 다음 MAP/FIT 반복으로 넘어가지 않는다. functional289/performance287/isolated297/latest298 및production227 기준을 보존한다.


## 최종 선택·재현

SELECT test03/window01/isolated01/guards01/native01/armguard01/h2guard01/irqguard01/board01/analysis01. 정상3+제한3+새RTL/기존ARM296 제한3의9개 live 일정,44개 RTL guards,새 ELF의 native71+6생산 guards/8대기 STOP guards/9H2/8IRQ 사례33exceptions PASS. 단일 whole Quartus Lite MAP PASS. native71은1039명령73260B/fixture read0이며 live71로 세지 않는다.

분리 실행 isolated01은 새 RTL에 기존 ARM296 loaded ELF를 사용했다. 제한905/906/907이 각각104.876059654/116.900688084/17.468381286ms로298과 정확히 같다. 따라서 주소·범위 RTL 자체의 일정 이득은 없다. 새로운 ARM 공급 위치는 normal 회귀를 일으켰고 restricted의1clock 차이는 목표 해결 이득이 아니다.

새 RTL은nes_mux260/nes_validator278/nes_joint266 세 파일이다. live/guard/whole 입력을 대조하고 원래E1/E9 wire bytes·순서를 실제 전송 기록으로 확인했다. CRC tap은 byte-identical이며 독립 domain/duplicate/CRC/persistent/manifest/seal/12read/STOP gate의 유지도 source anchor로 확인했다. 분석 입력425개와 분석기 자체 SHA256을 기록했다. 전체 own 합은17678comb로 합성 summary와 일치한다. fixed4827/outside12851/허용2557이며 현재 부족2270개다.

공개 결과: [검증 JSON](../analysis/arch300-verification.json), [정상](../analysis/arch300-normal.csv), [제한](../analysis/arch300-restricted.csv), [RTL 분리](../analysis/arch300-RTL_only_restricted.csv). 재현 도구는 `tools/probe_nes_live300.py`, `probe_nes_live300rtl.py`, `guard_nes_arch300.py`, `map_nes_arch300.py`, `analyze_nes_arch300.py`다. raw 실행과 실패는 workspace의 `probes/nes-arch300`에 보존한다. 기존 승인된 FLOAT wrapper를 쓰며 합성은Lite만 사용한다. 자동 merge하지 않는다.
