# NES361 — 실제 EA 수신·공유 SPI·private cache 연결

338 RTL·355 ARM과359 host 절감을 유지한다. 5tag hint를 실제 공유 SPI receiver와 cache/ROM 경로에 연결해 **시간 이득은 확인했지만 회로 부족은 커졌다**. 후보는 선택하지 않는다. 남은 source·host 공동 실행기 교체는 구현 완료하지 않았으며, 그 절감을 이번 결과에 넣지 않는다.

## 실제로 연결한 것

기존 EA는7B 최종 plan retire 명령이다.360의24B hint를 그대로 보내면 충돌하므로 receiver가 길이·소유 phase를 구분하도록 바꿨다.7B는 기존 ended/accepted/generation/CRC8/A5 검사 후 retire만 수행한다.24B는 input lease 중 generation/epoch/serial·5tag 범위·CRC16을 통과할 때 private ROM 작업만 시작한다. malformed/truncated hint는 retire나 DMA를 실행하지 않는다.

별도 SPI shifter와 별도 CRC16을 추가하지 않았다. 기존 shared receiver의 byte/count/payload CRC를 재사용한다. hint80bit 저장과 launch/complete CDC,7bit byte cursor,cache port mux 및 소유권 검사는 실제 추가 회로로 모두 청구했다. 일반2slot credit은 차지하지 않는다. tag bus는 launch 전에 확정되고 complete까지 고정된다. 캡처 namespace는 입력 lease 동안 고정되어야 한다. 물리 CDC/STA 검증을 했다는 뜻은 아니다.

source tile 경로의 cache 요청 포트를 hint/일반 tile이 공유한다. hint는 input lease 또는 이어지는 display lease 안에서만 진행하며, 일반 tile plan은 hint가 소유한 포트를 동시에 사용하지 않는다. CRC 승인된 hint도 E9/DMA/display 권한을 만들지 않는다. STOP·immutable epoch 변경·소유권 상실은 cache를 닫고 physical READ16을 drain한다. 기존 independent expected/read CRC·coverage·receipt 공개·최종 ACK는 변경하지 않았다.

## 실제 ARM 입력과 일정의 연결

직전 프레임의 actual ARM commit RAM을 보존하고, 현재 source SPI가 전달한 첫 N5 block을 producer에 넘긴다. 별도 실제 M4 ELF가 그 상태와 block을 해석하여24B packet을 만든다. 미래 plan이나 미리 정한 tag 배열을 실행 입력으로 쓰지 않는다. source decoder 명령 비용은 기존과 같고 hint reset+6회 증분 scan/CRC에3631명령이 추가됐다. epoch/serial과 packet은 두 일정에서 동일하다.

생성기 object는360에서 검증한 text1916/BSS74/관측stack56B를 사용한다.355의 실제 output firmware load image는 그대로다. **완성된 firmware foreground 루프에 hint 함수를 링크한 것은 아니다.** source 입력 실행은 기존의 명령 비용 replay이며, 받은 block에서 M4 helper를 실행해 결과와 비용을 그 시점에 반영한다. TB가 실제 공유 SPI pin에24B를 송신한다. 추가 IRQ는 실제233 handler66명령과 예외24cycle 할당을 청구한다. 기존 output ARM/IRQ와2slot 처리 자체는 실행한다. 전체 MCU WCET/모든 IRQ 선점/foreground SPI driver 비용 증명은 남아 있다.

## 전체 처리 시간

|일정|359 기준|361 후보|차이|60Hz까지 남은 시간|
|---|---:|---:|---:|---:|
|연속 warm907|20.689706ms|19.700809ms|-0.988897ms|3.034142ms|
|동일 시작·ROM 위상 warm907|25.051563ms|24.070347ms|-0.981216ms|7.403680ms|

각 일정에서905/906 준비 프레임도 실행했다. 고정 일정은 기준과 모든 start time/ROM cycle이 같다. 연속 일정은 이전 프레임의 비용 변화가 다음 시작 위상에 반영된다. 두 표 행끼리 빼서 최적화 이득으로 계산하지 않는다.

연속 warm의 시작 ROM cycle은 기준5677152→후보5677309이다. hint SPI 시작/종료/fill 완료는 각각1.502499/1.583642/1.636230ms이다. 입력 전송을 밀어낸 시간과 뒤따르는 ARM·DMA·credit·poll/IRQ 비용을 전체 종료 시각에 포함한다. output E1 명령·DMA 순서·E9 plan bytes는 기준과 같다. warm source 전송668B에 hint24B가 추가되고 output 전송은 진행 응답 증가로1084→1098B가 되어 총38B가 늘었다. 이는 cache와EA 결합 후보의 전체 시간 차이이며 EA만의 순수 이득으로 분리한 값은 아니다. 첫 준비 프레임은15.227µs 느려졌고, 고정 위상의 두 번째 준비 프레임도8.227µs 느려졌다.

BG cache 이득 뒤에도 OBJ가 병목으로 남는다. 연속 첫 OBJ plan은8.585374ms, 첫 OBJ tile은16.848775ms로 그 사이8.263401ms가 있다. 이 차이는 해당 plan의 ROM/cache/실행 대기 전체이며 순수 ROM pin 시간으로 부르지 않는다. BG5tag만 앞당겨 모든 후반 지연이 사라진다고 가정할 수 없다.

## Quartus Lite 전체 비용과 실제 삭제 여부

|whole MAP|LE|comb|FF|RAM bits|15408comb 대비 부족|
|---|---:|---:|---:|---:|---:|
|338 선택|22144|17274|9018|307808|1866|
|359 host|22083|17213|8999|307808|1805|
|360 cache 용량|22234|17364|9005|308832|1956|
|361 EA 수신 포함|22499|17576|9093|308832|2168|

359 host 대비+363comb/+94FF/+1024bit,360 용량 대비+212comb/+88FF다. shared CRC 재사용으로 별도 CRC engine은 피했지만 hint 경계 자체의 비용은 사라지지 않는다. helper만152comb/88FF이며 whole 차이와 단순 합산하지 않는다. 캐시 유효80B는 물리128×8 M9K 전체로 청구한다. 초기 STOP 보강 전map01은17604comb였고 최종map02만 비교에 사용한다. 합성 최적화에 의한 차이를 소스 제어 삭제로 세지 않는다.

source encoder·source transport·host flow·validator 본문이359와 동일함을 해시/내용으로 확인했다. 따라서 **광범위한 source·host 제어 삭제는0**이며, 이번 후보는 추가 연결의 비용을 밝힌 결과다. 기존3,806comb 영역을 이미 새 공동 실행기로 바꿨다고 주장하지 않는다.

중복 없는 최종 분할은 source-host3806, checker/aperture1250, queue/SPI792, plan459, 나머지(hint/cache 포함)11269comb다. 목표15253comb를 유지하고 queue/SPI를650으로 제한하면 source-host 상한은1625이다. 각각2181/142개, 합2323개를 더 삭제해야 한다. 이는 합격 상한이지 달성 예측이 아니다.

source encoder1349+transport394를 무료로 전부 없애도 host에서438개를 더 줄여야 한다. 실제 대체 row/query/CDC 실행기는0비용이 아니므로 필요한 host 감소는 더 크다. 작은 tag controller를 계속 덧붙이는 방식은 전체 면적 목표를 충족하지 못한다. 다음은 기존 source codec와 host payload/RLE/RAM 진행을 phase별 단일 실행기로 **실제 삭제·대체**하는 구조를 증명해야 한다. NES query/plan cursor, collector cancel/DONE drain,5KiB history, H2와 겹치는2×66B row slot의 소유권 전환을 모두 포함한다. RAM clock mux나 미구현 절감은 허용하지 않는다.

## 검사·실패 보존·채택 판단

실제 shared SPI/plan endpoint/EA/source cache/arbiter/READ16 guard60건을 실행했다. 정상80B, 중복,1..23B 잘림, 초과 길이, CRC/namespace/tag 범위, mutable/lease 오류, physical fill STOP drain/validity 폐기, 각24byte 위치 STOP 뒤 꼬리 차단, 기존7B retire를 포함한다. 전체 일정에서는 actual read→unit→private write→ACK 공개 순서,2credit,12B 최종 표시 read를 다시 검증했다.

window01은 기존 cache용 ready-gated 진단이 순차 cache에 맞지 않아 종료했다. 실제 physical core grant·응답 검사로 바꾸고 재실행했다. window02는 전체3프레임을 통과했지만 guards01에서 STOP 뒤 wire tail 승인 결함이 재현됐다. receiving latch를 추가해 command 시작을 관측하지 않은 꼬리를 거부했다. window03은 한글 경로를 Windows cmd 코드페이지에 전달한 harness 오류로 종료했다. ASCII cmd→UTF-8 Python runner로 수정했으며 license 문제가 아니다. guards03에서는 end_sealed를 여러 클록 유지한 fixture 오류가 마지막 retire 검사에서 드러났다. 실제 한 클록 펄스로 수정한guards04와 STOP 해제 뒤 늦은 DONE까지 확인한guards05가60건을 통과했다. 이 실패들과map01/02를 보존한다.

선택은338/355 그대로다. 후보의 시간 이득은 확인했지만 회로 gate를 실패했으므로 시간·회로 동시 개선, production 또는 실물60fps로 승인하지 않는다. 독립 검사·STOP·최종 ACK·VBlank 계약을 유지한다. ordinary65816 trace와 tile/display 모델을 포함한 검증이며 새 전체65816/VBlank 실행 증명은 아니다. FIT/STA,전체 firmware ingress/IRQ,71프레임 확장, hint deadline/fallback, 실물은 남아 있다. Production227/GBC164/saveSRAM은 변경하지 않는다.

근거: analysis/hint361-verification.json, probes/nes-hint361의window04/fixed01/guards05/map02 및 원시 로그. PR131에 기록하며 자동 merge하지 않는다.
