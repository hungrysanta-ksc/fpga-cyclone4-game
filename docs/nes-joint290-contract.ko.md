# NES290 단계별 출력과 공통 receipt 끝 주소

NES290 후보 미채택: H2/BEGIN과 닫힌 tile DMA 범위를 실제 planner 중 전송했다. 71프레임 명령 일치·fixture read0, 선행DMA는906의5개뿐이다. ARM/STOP/H2 및 정상·제한ROM3씩, RTL25·범위318 검사 PASS. 일반907 15.336589ms(+0.021591), 제한907 17.318156ms(-0.681492) vs289. 통일 receipt 끝 주소의 whole Lite 17764comb(+93), 부족2356; 고정 교체 경계4896(+43). ARM text+560/BSS+20/stack1304B. 공동 개선 실패로 native 기준289·성능 기준287 유지.

## 구현과 실제 효과

NES289의 native 생산기를 확장해 COMMITTED/raw 검사 뒤 선행 H2와 BEGIN을 보낸다. immutable certificate286을 사용하므로 아직 BG-key 배열로 사용 중인 raw table union을 읽지 않는다. 최종 native H2를 다시 계산해 선행 인증서32B와 같아야 SEAL로 진행한다.

완료된 E9 batch만 cursor로 한 번씩 읽고, 다음 slot/kind 또는2048B 경계로 닫힌 이전 DMA 범위만 전송한다. 닫히지 않은 범위는 유지하고 다음 planner 단계로 돌아간다. 마지막 범위는 전체 planner 완료와 raw/native 검사 뒤 flush한다. 기존 compressed E1/E9 바이트·token·순서는 각각 그대로이며 전송 시점만 바뀐다. BEGIN 자체는 조기DMA로 세지 않는다.

실제 M4의71프레임1039명령/73260B가 기존과 일치했다. 그러나 planner 완료 전 닫힌 DMA 범위는 **906번의5개**뿐이며 warm69프레임에는 없다. live3에서도 early_DMA_descriptors는0/5/0이다. 이 구조의 제한을 batch 크기나 임의 polling 지연으로 숨기지 않는다.

FPGA는 host의 `limit-first`와 validator의 `first+count` 경계를 끝 주소 규약으로 바꿨다. 일반과map 모두 exclusive end를 전달하며 validator는 end>first, domain, map 최대32, monotone map, 독립 CRC coverage를 검사한다. 기존 `*_count` 포트 이름은 호환상 유지했지만 이 후보 내부 값은끝주소이므로290 host와validator는 반드시함께사용한다. main host/validator FSM, header/parser/ACK·manifest 제어 전체를 제거한 구현은 아니다.

## 같은 일정과 전체 회로 비용

ARM84MHz·CPI1 가정, 실제M4 명령·IRQ/refill·공유SPI·tileROM 경쟁을 포함한 진단 일정이다. source280 시간 replay와65816 일반실행279 bus trace를 재사용한다. live65816/fullRUN/실물CPI/WCET는 아니다.

| 항목 | NES289 | NES290 | 차이 |
|---|---:|---:|---:|
| 일반907 | 15.314998ms | 15.336589ms | +0.021591ms |
| 제한ROM907 | 17.999648ms | 17.318156ms | -0.681492ms |
| ARM text | 26450B | 27010B | +560B |
| ARM BSS | 47060B | 47080B | +20B |
| 관측stack | 1296B | 1304B | +8B |
| 전체Lite comb | 17671 | 17764 | +93 |
| 교체경계 comb | 4853 | 4896 | +43 |

제한907의60Hz 예산 초과는0.651489ms다. 일반907 한 프레임은 전체60fps 증거가 아니다. 정상/제한은 각3프레임만 새일정으로 실행했으며,71프레임은 명령 생성 일치 시험이다. 채택하지 않는 후보의 normal71을 새로 돌려 목표 달성을 주장하지 않았다.

3개 프레임의 진단 시간 합계 차이는 일반 -0.175407ms, 제한ROM +0.414404ms다. 제한907만 빨라졌지만 905·906의 증가까지 포함하면 오히려 느리다. ROM 위상 변화가 포함된 warm 한 프레임을 순수 가속이나 최악시간 보장으로 해석하지 않는다.

전체Lite는22650LE/17764comb/9025FF/307808bits다. FF와RAM은 같고 comb93개 증가했다. host2370(+9), validator1118(+28), queue128(-1), plan570(+2), SPI657(-1), glue53(+6)으로 고정경계4896이다. 범위 밖12868도 전액 부담하며 후보예산2540, 부족2356이다. 전체 증가를 모두 host 변경 탓으로 귀속하지 않으며, 부분MAP을 전체에서 임의 차감하지 않는다. source상 산술 제거는 실제 회로 절감으로 이어지지 않았다. FIT/STA/seed 반복은 하지 않았다.

## 검증과 보존

SELECT native01(71+6 STOP/commit), armguards01(9 부분planner/frontier/STOP), h2guard01(9 최종H2), test02(3), window02(3), range01(318), guards01(25), board03, analysis01. 실제ELF 로드 코드/데이터/주소/BSS, 생성소스, simulator/board 경계 해시와 입력을 고정했다. packet 인터셉트 시험은 실제ACK 증거가 아니며 live worker의finish267 성공 뒤commit285 순서와 RTL STOP/최종ACK를 따로검증했다.

기존 directed guard harness에는 미사용 SPI progress_mode284/progress_irq284 출력 포트 경고3개가 남아 있다. 입력 누락은 아니며 이 guard를 IRQ 검증으로 세지 않는다. IRQ 출력은 별도의 실제 ARM test02/window02에서 연결해 실행했다.

일반descriptor만 end로 바꾼 초기 혼용 규약은board01에서17748comb(+77)였고test01/window01은그중간RTL이다. map까지 통일한board02는 생성문자열 주석이 같은 줄의range_valid assign을 가려undriven 경고로자동실패했다. 이결과는비교에서제외했다. 줄바꿈수정 후board03을합성하고최종test02/window02와오류검사를실행했다. 이전실패와중간PASS는덮어쓰지않았다.

생산227/GBC164/saveSRAM은변경하지않았다. 290은미채택진단이며기능연결기준289와성능비교기준287을유지한다.

## 다음 교체 경계

290의 조기BEGIN/범위 산술 이동은 미채택으로 보존한다. 동일 compressed wire를 유지한 채 host head/READ/ACK, descriptor dispatch, validator receipt/manifest 진행에서 실제 제거할 상태·레지스터·RAM port 소유권을 먼저 하나의 대체 경계로 확정한다. 원래4853comb 경계를2590 이하로 줄이는 제거 목록이 없으면 또 다른 cursor/끝주소/FSM 비트 미세조정은 하지 않는다. 독립 bounds/CRC/coverage, 4credit/token, STOP·최종ACK는 유지하고 native289의 생산·stack 비용도 전액 부담한다. warm69에는 이번 earlyDMA가 전혀 없으므로 고정 batch 분할을 이득으로 가정하지 말고 최초 완결 tile 범위와 planner/ROM 임계경로를 함께 검토한다. 실제 제어 교체 후보가 있을 때만 matched whole Lite와 normal71/heavy7/restricted 일정으로 재검증한다.
