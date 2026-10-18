# NES247: packed map·압축 manifest 공동 decoder 실행 — 기각

두 decoder를 새 진단용2472 수신기에 연결해 실제 C→65816으로 측정했다. 정상 화면 데이터와 오류·STOP 검사는 통과했지만 **이 CPU decoder 후보는 시간 gate에서 기각한다.** 본문은5886→5066B로820B 줄었으나 warm69의 조건부 최대 시간은24.175→30.575ms,16.67ms 초과는26→57프레임으로 늘었다.

가장 빠듯한954에서 map8.905322ms+manifest5.551544ms=**14.456865ms**다. 같은 실행의 mark/coverage를 반영한 두 decoder 잔여 상한은1.746649ms로12.710216ms 초과한다. 이전 모델의1.748512ms와의 미세 차이도 보존한다. 이 측정은 외부 packet 진입과 마지막 caller service를 더하기 전부터 실패한다. 따라서 그 나머지를 측정해 성공 여부가 바뀔 후보가 아니다.

## 구현한 경계

2472는 진단용 paired version이다. 기존2471 BEGIN/SEAL은 거부한다. 원본 SMB3(J), 생산227·GBC164·save SRAM은 변경하지 않았다.

- op9/section2는 mode3 뒤 offset16LE/wordcount8/값을 받는다. exact contiguous 범위를 최대32word/64B로 자르고240B packet에 묶는다. 불필요한 map word를 추가하지 않는다.
- 범위는 짝수 offset,1..32word,4096B 안,frame 전체에서 이전 끝 이상이어야 한다. payload 전체 범위를 확인한 뒤 receipt와 inactive WRAM을 갱신한다. 이 단조 비중복 조건이 receipt bit 중복을 막는다.
- receipt는 기존256B에16bit 범위 mask를 OR한다. 값은 CPU long-pointer word 복사로 옮긴다. 기존 packet 내 pending span/gap96/최종 generic append와 record별 service를 유지한다. 기존 generic DATA DMA나 op7 pattern bulk를 새 구현으로 세지 않았다.
- op10은 기존 dense240+16 manifest다. op11은 mode3 zero-run/literal manifest다. token 하위7bit+1은1..128B,상위bit1은zero다. 생략한zero 위치까지 실제 receipt와 비교한다. token은 packet 안에서 완결되어야 하고 decoded offset/256B 한도·최종 coverage를 검사한다.
- manifest 종류는7E1492..1493의2B에 기록해 혼합 형식을 거부한다. BEGIN에서 초기화하며 manifest 진입 뒤 map을 받지 않는다. 기존 확보 영역 안의 실제 사용+2B이고 새 전체 배열은 없다.
- RLE run마다 service를 호출한다. 첫 span/일부 manifest 처리 후 STOP은 terminal rejection되고 두 map 초기화 flag를 무효화한다. 최종 표시/retire 소유권은 기존 경로다.

PC C 송신기도2472로 연결했다. 독립 Python encoder와 실제 C packet 전체를 비교했으며 ARM 구현·stack 승인은 아니다. 기존 PC 이전map4096B/stale512B 외에 manifest 함수의 임시512B/240B 배열도 private fixture용이다.

본문5066B는 이전6KiB 저장의5984B 본문 공간에 대입하면918B 여유다. 이 산술은 새 합성 결과가 아니다. 시간 gate 실패로 새 MAP/FIT/STA/ARM build·설치물은 만들지 않았다.4/5/6KiB와918B는 절대 한도가 아니다.

## 실제 검증과 실패 이력

SELECT `jointdecode-build02/host01/test02/fault02/analysis03`.

- 실제71 display commits/1039 ACK,C reference4,066,624 checks,map290,816B 및71개 최종 command 목록 일치.
- C의 모든 packed span과 dense/RLE manifest가 독립 Python 모델과 byte exact다. 각 map packet의 값과256B receipt 전체를 실제 WRAM에서 대조한다. SEAL에서 metadata와 사용 pattern·map/raw VRAM을 기존 oracle로 확인한다.
-426DMA/132,270B,178 pattern bulk chunks/12,944B,최대DMA1312B/목록13개가 같다. warm multi-VBlank952/955도 남는다.
-2069 span record와3636 RLE run 각각의 service 진입·복귀 횟수가 일치한다. packet 내부 연속 service 복귀 간 최대는span11828 master clocks(약0.551ms),RLE15374(약0.716ms)다. 외부 전송/다른 명령을 포함한 전역 STOP 한도는 아니다.
-23개 실제 오류·STOP: span0/33word,odd/wrap/end/overlap/truncation/mode,cold map 누락,구 BEGIN/SEAL,RLE zero/literal 불일치·overflow/truncation/offset/mode,혼합 manifest,조기 SEAL,manifest 후 map,span/RLE/final STOP. 이전 표시 보존·terminal rejection을 확인했다.
- 허용된 미사용 pattern gap 밖의 미초기화 읽기는 없다. 선택한 정상·오류 실행에는 Lua assertion 파일이 없다.

**test01은 실패로 판정했다.** 첫5062B 구현이 packet 마지막 RLE token을16bit로 읽어1B overread했다. Lua callback assert가 기록되어도 Mesen이 계속 실행하며 consumer-result에 PASS를 쓸 수 있음을 확인했다. 해당 원본 PASS 파일을 성공 근거로 쓰지 않고 `audit-rejection.json`과 원본 로그를 보존했다. build02는token을8bit로 읽는다. 강화한 runner는 Lua 오류가 하나라도 있으면 성공 결과 작성 전에 실패한다. 이것은 허용 오독이나 emulator 무시 옵션으로 해결한 것이 아니다.

fault01은 마지막 STOP 이름이 기존 fixture의generation2 STOP 모드와 충돌해, 의도한generation3보다 먼저 멈췄다. 원본 bus/error를 보존하고 이름을 분리한 fault02에서23건을 통과했다. analysis01은 fault 결과가 아직 없을 때 실행해 실패했다. analysis02 PASS 후 실제 C packet 비용과 ready grouping까지 대조한 analysis03을 선택했다. 실패·중간 결과는 덮어쓰지 않았다.

## 시간 gate

|warm69|5886B 기준|5066B 공동 decoder|
|---|---:|---:|
|non-map mark 합계ms|85.729797|85.744697|
|map decoder 합계ms|329.040423|360.220270|
|manifest 합계ms|63.026725|329.700563|
|coverage 합계ms|72.356403|72.356403|
|조건부 wire+측정routine 최대ms|24.175062|30.574656|
|조건부16.67ms 초과|26/69|57/69|

이 표의 시간은 실제 routine 구간이며 pure copy instruction 비용만을 뜻하지 않는다. 전체 합에는 source/ARM/외부 dispatch/copy/전송 공백/최종DMA/display가 모두 포함되지 않는다. 실제FPS 또는 모든 overlap 일정의 불가능 증명이 아니다.

954의 실제 C packet은 map45record/2packet,manifest111B/1packet이다. 모델 ready4는3976 clock-byte다. 기존 ordinary DATA와 새 packet의 실제 payload/framing 차이 및 ready 그룹 수를 다시 계산해71프레임 모두 모델값과 일치시켰다. op7 bulk는 별도 제어/ready에 포함돼 이중 계산하지 않는다. wire가 줄어든 이득보다 CPU의 span 처리와 RLE 검증 비용 증가가 컸다.

## 결정과 다음 경계

이2472 CPU decoder는 배포·전체 FIT 대상으로 선택하지 않는다.5066B라는 크기 감소를 성공으로 취급하지 않는다. 안정된 진단 비교 기준은5886B validation이며 생산은227이다. RLE token이나 작은 bitmap/분기/seed 조정 반복으로 이어가지 않는다. 이 결과가 모든 packed 형식이나 DMA 복사 방식 전체의 불가능 증명은 아니다.

다음은 같은71프레임에서 **SNES가 record를 해석·검증하는 작업의 위치와 전달 경계**를 바꾸는 구조 비교다. 제한된 typed metadata/bulk 경계를 검토하되,각 범위/중복/receipt/CRC/token/STOP/display 검사와 상태를 누가 소유하는지 먼저 명시한다. ARM→FPGA 재충전 SPI 바이트·새 descriptor/ACK·RAM lifetime·CPU/LE/LAB/M9K를 모두 비용에 넣는다. 기존 tile aperture를 재사용하더라도 metadata 변환·검증이 공짜라고 가정하지 않는다.

입력은227 그대로 두고 출력만 병렬화하면19ms 이상의 입력 비용이 남는236 결론은 유지한다.449B 의미 raster+row shift를 보존하는 제한된 A와 출력 경계 재배치,변환까지 옮기는 B를 구분해 비교한다. 전체 planner 배열을 FPGA에 그대로 옮기는 방식과 full raw 재전송이 이미 부적합했던 근거도 재사용한다. 새 ARM 병렬 연결이나 공유 RAM을 가정하지 않고,구체적 전체 여유가 있는 후보만 최소 구현으로 진행한다.

240 미배치·mapper 여유,952 순서/9554198>4192,새 입력 ARM RUN/IRQ,host/NES firstfault·CDC/IO·final display lease-retire는 계속 열린 조건이다. 새 source RTL/FIT 또는 같은227/044 실기 반복으로 자동 전환하지 않는다.

재현: [builder](../tools/nes_jointdecode247.py),[PC 송신 fixture](../tools/prepare_nes_jointdecode247.py),[실제 replay](../tools/test_nes_jointdecode247.py),[오류·STOP](../tools/test_nes_jointfault247.py),[분석기](../tools/analyze_nes_jointdecode247.py). 공개 [집계](../analysis/jointdecode247-verification.json)·[71프레임](../analysis/jointdecode247-frames.csv)에 실제/모델/미측정을 구분한다. 원본 ROM·덤프·실행 로그는 private probe에 보존한다.
