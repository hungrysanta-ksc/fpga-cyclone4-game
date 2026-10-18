# NES247 P1 후속: 입력 표현·최종 DMA 순서·bank 수명 결합

2026-10-18. PR128, 생산227 / 기능 기준240(미배치) / 기각241·246 유지. [전체 경로247](nes-wholepath247-contract.ko.md)의 P1 후속이며 **제품 구현 후보는 아직 선정하지 않았다.** 같은71프레임에서 입력4종 × map 출력2종을 최종 DMA 정렬·유효 간격 병합과 결합했다. 단순 입력 압축 제거는 출력 wire 절약을 반영해도 예산을 넘고, full 입력 유지 조합도 SNES 잔여 burst와 FPGA 면적을 해결하지 못한다.

## 확인한 범위와 근거

[재현 도구](../tools/analyze_nes_schedule247.py), [요약](../analysis/schedule247-verification.json), [71행 비교표](../analysis/schedule247-frames.csv). 선택 schedule04; observer03/analysis06은 그대로 둔다. 이전 결과·observer 소스·실제232 bank dump 등 소비한457개 파일의 hash를 확인했다. 이전 봉인 전체를 반복 검사하지 않았다.

최종 DMA의 주소순 정렬만 모델링하며, planner의 slot 결정이나 bulk/token 수신 순서를 바꾸지 않는다. 두 target bank의 pattern 유효 비트를 처음부터 따로 추적한다. 기존 실제232 실행의 bank snapshot71개와 비교하여 현재 plan이 쓰지 않은 영역도 이전 target 내용 그대로인지 확인했다. 기존 SEAL의 used bitmap에 해당하는 **130,592바이트가 모델 VRAM과 일치**했다. 새65816/RGB 실행은 아니다. 사용하지 않는 C fixture 영역의 `0xA5`는 초기화 증거가 아니므로 유효 비트가 없는 간격을 DMA에 넣지 않는다.

병합 조건은 같은 section, 증가하는 주소, 간격≤96B, 합계≤4096B, 간격 내 모든 slot이 **현재 target bank/epoch에서 초기화됨**이다. 허용된11개 간격592B를 복사했다. 초기화 안 된 hole을 막는 반례도 확인했다. map/raw는 기존232의 최종 coverage와 gap 병합을 유지한다. 값은 기존4192 charge 기준이며 master clock 실행시간이나 FPS가 아니다.

## bank 유효성을 생략하면 과대평가하는 사례

|프레임|기존232 charge|정렬+유효 간격+16B map|정렬+유효 간격+word map|제약|
|---|---:|---:|---:|---|
|952|4752|4368|4340|OBJ gap32/32/64B의4slot 미초기화; word 조합도148 초과|
|954|4272|4176|4120|16B 조합 여유16; 실행시간 여유를 증명하지 않음|
|955|4400|4304|4262|OBJ gap32B 미초기화; word 조합도70 초과|
|963|4240|4240|4178|word 조합 여유14뿐|
|968|4720|4176|4134|유효한32B gap과 정렬로544 절감|

초기의 유효성 없는 낙관 모델은952를4208/4180,955를4240/4198로 계산했다. 최종 근거로 사용하지 않는다. 실제 유효성을 적용하면16B map은952/955/963의3개, word map은952/955의2개가 남는다. 모든 unused gap을 별도로 초기화하는 설계까지 불가능하다는 증거는 아니다. 그런 설계는 추가 쓰기·STOP·epoch 수명과 코드 비용을 포함해야 한다.

word map은 기존247의 양 bank word dirty bitmap으로 ARM retained state가448B 늘어난다. 233의1616B 여유에서1168B만 남으며, 새 입력 RUN/IRQ를 반영하지 않은 산술이다. 반면16B 묶음은 추가 retained bitmap0B다. 어느 쪽도 아직 SNES decoder가 구현되지 않았다.

## 입력·출력 비용을 함께 비교한 결과

입력 full/shift/literal은 기존236에서 실제 C 출력355파일이 동일했던 모델을 재사용했다. `shift`는 row shift를 유지하고 raster 압축만 제거한 경우다. `mask16`은 새 **표현 모델**이다. warm geometry를16B 단위로 비교해 `block index16 + changed mask16 + 바뀐 byte`를 보낸다. cold는 기존240B literal, header20B/geometry END10B/RAW END6B 및 raw literal을 유지한 크기 모델이다.71개 geometry5741B를 직렬화 후 복원하여 동일성을 확인했지만 새 version/CRC/serial/admission/ACK decoder를 구현한 것은 아니다.

whole-record248B 블록당 기존19B 전송·제어 비용, 기존 ready4/ready1 polling 시나리오를 포함한다. 출력 map 묶음의 packet 수 감소도 함께 반영했다. SPI60Hz 모델 예산5468.75B에 대한 **warm69개** 결과:

|입력|map 출력|ready4 최대B|ready1 최대B|ready4 초과 프레임 수|SNES 초과 수|
|---|---|---:|---:|---:|---:|
|full|16B 묶음|4759|4939|0|3|
|full|word|4219|4359|0|2|
|shift|16B 묶음|6340|6520|3|3|
|shift|word|5800|5940|1|2|
|literal|16B 묶음|7034|7214|20|3|
|literal|word|6494|6634|7|2|
|mask16|16B 묶음|6271|6451|6|3|
|mask16|word|5731|5871|3|2|

shift+16B는954/963/970, mask16+16B는951/954/957/963/967/970에서 초과한다. 출력 절약을 반영하지 않았던236의 수치만으로 단순화 가능성을 배제하지 않고 다시 결합한 결과다. full은 wire 시나리오를 통과하지만 실제 SPI gap/ARM 변환/consumer 대기 상한이 없고, source240의490LE/40LAB 부족도 그대로다. 새 단순 입력에240의 prepare cycle이나 면적 감소량을 부여하지 않았다. **8조합 모두 현재 P2 진입 조건을 충족하지 못한다.**

## 선행 업로드의 실제 소유권 경계

근거는 기존233 `nes_native_runtime165.c`와 공개 [runtime233 구성](../tools/nes_runtime233.py), [dirty212](../tools/nes_dirty212.py), [sparse232](../tools/nes_sparse232.py), [banked169](../tools/nes_banked169.py)다. 각 소비 파일 hash를 요약에 남겼다.

1. 현 runtime은 입력 COMMITTED → target BEGIN → planner/plan queue → finish drain → SEAL/display ACK → retire → consumed 순서다. 다음 BEGIN을 받는 중복 프레임 파이프라인은 없다. capture overlap만으로 ARM의 다음 target 준비가 겹친다고 간주할 수 없다.
2. 현재232의 received/valid bitmap은 WRAM에 수신 완료된 byte를 나타낸다. **VRAM DMA 완료 비트가 아니다.** 모든 SEAL coverage 검증 후 command list를 실행하므로 현재 gap copy는 이후 write에 의해 낡아지지 않는다.
3. 선행 DMA를 도입하려면 complete bulk의 token/epoch/bank를 먼저 검증하고 target만 쓸 수 있어야 한다. 뒤늦게 도착한 새 write가 먼저 DMA한 구간을 바꾸면 다시 pending으로 돌려 최종 drain해야 한다. 기존 valid bit만으로 이 상태를 대신할 수 없다. active CGRAM/OAM·bank 선택·표시 ACK는 최종 VBlank에 남는다.
4. STOP/epoch 변경은 일부 target이 이미 변경됐더라도 후보를 폐기하고 새 BEGIN 전에 소유권을 확정해야 한다. 부분 DMA를 display commit으로 취급하거나 기존 source lease를 먼저 retire할 수 없다. 현재 fail 경로는 resident/dirty/source를 abort하고 uncertain ownership 상태에서 다음 BEGIN을 허용하지 않는다.
5. `wait169`는 STOP/pad를 service하면서 현재 blank가 끝난 뒤 다음 blank 시작을 기다린다. inactive VRAM도 같은 VBlank 자원을 쓴다. 작업을 앞 VBlank로 옮긴다는 설명만으로 steady60Hz 대역폭이 늘지는 않는다. 이전 display 직후 남는 같은 blank 활용, 다음 source 준비 시각, upload+최종표시의 실행 비용을 함께 증명해야 한다.

따라서 이번 비교는 **SEAL 이후의 순서 변경**만 허용한다. 선행 DMA를 공짜 overlap으로 더하지 않는다. SNES body3910/3936B의26B 여유로 decoder/새 pending 상태/scheduler를 단순 추가할 수 있다고 가정하지 않는다. 기존 command-list 생성·전송부를 bitmap 기반으로 교체하는 범위를 검토할 수 있지만 scan 비용/코드 절감은 아직 측정되지 않았다.

## 결정과 다음 범위

P1을 지속한다. 이번에 배제한 것은 위의 정확한8조합이며, 전체240 단순화나 full B 전송·변환 재배치의 불가능성이 아니다. 다음은 **실제 병렬 aperture의 생산자·소비자 경계에서 geometry/raster 변환과 전송을 함께 옮기는 경우**를 현 full240 경로와 비교한다. 기존188 tile 전달만으로 map/raster 변환까지 해결됐다고 하지 않는다. ARM SPI refill 경유분은 그대로 비용에 넣는다.

후보마다 제거할 source/query/codec/transport와 추가할 RAM/logic/ARM/SNES 작업을 명시하고, 같은954/952/955 등 프레임의 ingress+egress+VBlank 비용과 ownership을 합산한다. 최종 DMA의 유효성 증명과 입력 압축의 기능 보존, FPGA 전체 여유/mapper/새 입력 ARM RUN/IRQ/SNES ROM 교체 범위를 함께 갖추기 전에는 RTL/FIT 반복이나 새 실기를 진행하지 않는다. 단순 mask/opcode 추가, unchanged227/044 반복, 생산227/GBC164/save SRAM 변경은 하지 않는다.

## 재현 및 실패 이력

```text
python tools/analyze_nes_schedule247.py --prior <private-analysis06/result.json> --observer <private-observer03> --out <new-private-directory>
```

private 봉인 자료가 필요하다. schedule01은 C oracle의 초기 `0xA5`를0으로 가정한 assertion 실패; 소스와 원인을 보존했다. schedule02는 SEAL descriptor222B와16B envelope를 혼동한 길이 assertion 실패; 소스·raw log를 보존했다. schedule03은 수명 기반 비교 PASS, schedule04는 같은 수치에 invalid gap 설명·cold literal 복원·observer source hash 검증을 추가했다. 새 product RTL/C/65816 코드, Questa/FIT/ARM 빌드/실기/FWZIP은 만들거나 실행하지 않았다.
