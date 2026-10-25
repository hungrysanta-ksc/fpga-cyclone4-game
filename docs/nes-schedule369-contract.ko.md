# NES369 row 계획 비용과 exact-key 우선 재사용

PR132의368 커밋 `039c63ee8ddd4933f01c390afb3dbc97a93dd8c7`을 기준으로 같은 브랜치에서 진행했다. 실행 원본은 private `probes/nes-source369`, 최종 증거는 `analysis/schedule369-verification.json`이다.

## 결과

실제 ARM·공유 SPI·IRQ·2슬롯·입력/출력 ROM 경쟁 일정에서 **905~911 처리 완료**, 다음 **908~912 캡처 5/5 승인**을 확인했다. 두 초기화 프레임과 다섯 warm 프레임이며,912는 시작 승인만 검사했고 그 프레임의 전체 내용·출력은 실행하지 않았다.368에서 거절된911 캡처가 승인됐다. 이번 제한된 연속 일정은 통과했지만 **909는60Hz 예산보다0.206790ms 길어 지속60fps는 미승인**이다.

## 실제 병목과 교체

368의909 row 계획41단계를 기존 SPI 응답1830개와 원래 ARM ELF로 정확히 재생했다. 모든 SPI 요청과 수신 바이트, certificate·metadata·plan은 기존 worker의 독립 oracle 검사에 일치한다. 이 재생은 새 처리 시간 측정이 아니다.

41단계의516431명령을 함수 PC별로 중복 없이 분류했다. `nes_resident211_slot`175561, `step286`142329, `tile`70600, `find221`50921명령이 주요 비용이었다. BG29단계는467467명령이었다. ARM.call 준비 구간과 내부 함수를 겹쳐 합산하지 않는다. `frame259`의5.021497ms는 SPI·credit·소비 대기를 포함하는 호출 구간이지 순수 CPU 시간이 아니다.

기존 `nes_resident211_slot`은 exact-key 재사용으로 바로 반환할 경우에도 `ordinary(q)`의 row16개·alt8개와 retained-key 형식을 먼저 해석했다. 이 분류는 재사용 반환값에 쓰이지 않는다. **기존 admission 검사와 완전한 key 충돌 비교는 앞에 유지하고, exact hit가 없을 때만 ordinary/retained-key를 계산**하도록 옮겼다. ABI·할당 순서·검사 기준·RAM 소유권은 바꾸지 않았다.368의 causal hint·CRC·미사용 bitmap 제거도 그대로다.

실제909의41단계를 전후 ELF로 각각 실행해 반환값과96개 전역 객체를 매 단계 모두 비교했다.113020명령을 줄였으며 상태가 동일했다. 할당CPI1/84MHz에서1.345476ms에 해당하지만, 이 값을 실제 일정 이득에 추가하지 않는다. 별도320개 descriptor 입력에서 generation/kind/mask/row/alt/64bit key와 여러 실제 snapshot을 대조했고,5개 STOP 시점에서 late step·commit 차단 및 전체 전역 상태도 일치했다.

## 동일 위상 비교와 연속 일정

907의 캡처를 사전에5371247 NESclock으로 고정하고 이후357368clock마다 시작한다. 기한에 늦으면 실패하며 readiness에 맞춰 시작을 미루지 않는다.907~909의 source 시작과 ROMcycle은368 대조군과 정확히 같다.910은 앞선 backlog 변화로 시작 위상이 달라 별도 구분한다.

|frame|368 ms|369 ms|변화 ms|동일 시작·ROM 위상|
|---|---:|---:|---:|---|
|907|12.037605|12.037514|-0.000091|예|
|908|13.002730|12.574099|-0.428631|예|
|909|18.218941|16.873457|-1.345484|예|
|910|12.028333|12.027151|-0.001182|아니오|

911은12.570599ms에 완료했다. 초기화905/906은85.318135/114.773782ms이며 직렬 시작·바뀐 선행 일정이므로 warm 이득에 합산하지 않는다.

|다음 캡처|승인|직전 source 마지막 local 저장 이후 여유 ms|
|---|---|---:|
|908|예|0.672470|
|909|예|1.763275|
|910|예|0.018160|
|911|예|1.227872|
|912|예|0.511790|

독립 read→unit→private write→publish,2슬롯 credit,프레임별12exact display reads/token과 실제 generation별retire를 대조했다. 입력/출력 ROM 요청·응답48774/48774,입력에서 시작한 요청·응답7224/7224,pending0이며 응답 값도 검사했다. 시뮬레이터 오류0·경고0으로 종료했다. source token의drained-session 회복은 기존 미완료 범위다.

## 전체 비용과 삭제 예산

ARM text34178→34186B(+8),data4/BSS48476B 동일,관측stack1288B 동일이다. 기능 테스트의 모든 DUT source 바이트가368과 같고,368에서 기능/whole QSF에 연결한13canonical·30공통 module과도 연결된다. **새 Quartus MAP은 실행하지 않았다.** 그대로인 RTL의 기존 Lite22710LE/17698comb/9171FF/292448bits를 상속하며 이번 회로 절감은0이다. 부족은2290comb,155여유 포함2445순삭제로 유지한다. FIT/STA는 실행하지 않았다.

기존 report의 disjoint self 비용은 source1352,source transport378,host2058,validator1040,SPI567,plan transport349,plan endpoint96comb이다. inclusive parent/child를 더하지 않는다. source+transport의1730개를 모두 없앤다는 비현실적인 가정에서도 여유 포함715개가 더 필요하다. 실제 삭제 승인은0이며, 압축 source·독립 검증·CDC·STOP·최종 ACK를 유지한 source/host/validator/SPI/plan의 넓은 교체 예산이 필요하다. ARM 시간 개선으로 회로 부족을 해결했다고 보지 않는다.

## 남은 범위와 다음 작업

실제 compiled M4 C/IRQ body를 실행했지만 CPI1/84MHz·24cycle exception과 주변장치는 할당 모델이다. ROM은 입력/출력 ready-gated stress이며 live NES CPU가 아니다. ordinary65816 trace를 재생하지만 map DMA·최종 표시는 bus model이다. 기존 VBlank firmware와 production227/GBC164/saveSRAM은 변경하지 않았다. 전체65816/VBlank·full firmware WCET·heavy7/71·여러 시작 위상·FIT/STA·실기60fps는 미완료다.

369의 exact-key 우선 재사용과368 source/collector 개선을 유지한다. 909의 0.206790ms 추가 단축을 위해 tile membership 재확인·step286·후반 ordinary/E2/credit/DMA 비용을 분리한다. 검사를 생략하지 말고 불변 descriptor/required 정보의 재사용 범위와 cold·STOP 무효화를 검증한다. SPI DMA/2buffer 후보는 실제 동시 실행과 메모리/포트 비용을 연결한 뒤 비교한다. 905/906 초기화와907 고정 시작을 구분하고, 다음에는 더 긴 연속/heavy7/71 및 여러 ROM 시작 위상에서 backlog를 검사한다. 전체2290comb 부족(155여유 포함2445순삭제)을 source·host·validator·SPI·plan 공동 교체 예산으로 맞춘 뒤 전체65816/VBlank·firmware WCET·FIT/STA·실기로 진행한다. 캡처 기한 완화·검사 삭제·부분 FSM/seed/FIT 반복은 하지 않는다.
