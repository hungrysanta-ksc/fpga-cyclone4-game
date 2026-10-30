# NES497 — 실제 M4 bulk 소비 대기와 다음 export 허용 조건

[검증](../analysis/bulk497-verification.json) · [도구](../tools/test_nes_bulk497_arm.py) · [496](nes-schedule496-contract.ko.md) · [PR138](progress/pr-138.md).

실기493·9.57fps와 기존 바이너리를 유지한다. 이번에는 실제 linked493 M4의 plan/window/complete485를 2bank·연속tile 묶음 endpoint에 연결했다. 실제65816과동일시계로동작하는통합은아직미완료이며 새제품 구현·합성·전달본은없다.

## 실제 실행과 범위

기존 시험 endpoint는 E9마다 타일을 즉시 개별 job으로 만들었다. 새 endpoint는 실제 E9 CRC8/CRC16·압축/일반 plan 형식을 읽고 입력batch를 대기시킨다. 동일kind·연속offset·2048B 이하는 열린chunk에 누적하고 경계/END에서발행한다. 열린chunk도bank 하나를차지하며최대2개다. E1 수신시 이전bulk가아직pending이면실패시킨다. 이는 실제RTL 실행이 아닌독립모델이다.

고정905..916의219계획을실제ARM emit/finish로실행했다. 소비지연0/12000/100000 instruction 단위의36조건모두32chunk·2bank 이하였고순서/목적지/길이를독립그룹과대조했다. FINISH는모든bulk 소비후에만성공했고bulk_pending이해제됐다. 표시ACK를제공하지않은상태에서retire는SPI를발행하지않고거부했다. 실제최종표시ACK 성공·메뉴복귀를새로실행한시험은아니다.

E8 CRC/다른generation/동일token 내용변경/과거token/잘못된ACK/accepted/STOP after E9/STOP after bulk/모호한E1 실패의9반례도거부했다. 실패후finish 재호출은추가SPI를발행하지않는다. source byte·입력계획hash는JSON에고정했다.

| 지정 소비지연(instruction) | E0 | E8 | wire B | 실행 instruction |
|---|---:|---:|---:|---:|
| 0 | 44 | 141 | 6241 | 1841382 |
| 12000 | 63 | 154 | 6881 | 2234352 |
| 100000 | 215 | 245 | 11741 | 5218850 |

모든조건의 E9는33회,E1은32회로같다. 실제ARM 분기와128us 대기루프를실행했지만 테스트DWT는instruction clock이다. 표는12개타일공급구간의초기화/거부된retire를포함하며ordinary·SEAL·입력수신·SPI 실제전송시간·IRQ·ROM생산시간·65816실행을포함하지않는다. CPU cycle/ms/FPS로환산하지않는다. 지연에따라조회량이바뀌므로495의고정poll수wire절감투영을전체개선으로사용할수없다.

## 다음 입력 허용 조건의 수정

선택 source의 nes_source_tile192는 `drained=arb_idle`이다. 이는현재ROM중재요청이없다는뜻으로END/계획완료가아니다. 타일사이나첫계획전에도성립할수있어 `waiting_display && reader_drained`만으로새export를허용하면안된다. nes_direct206의END `ev && er`와generation을묶은완료조건이추가로필요하다. 이결론은고정source추적이며새RTL을구현한결과는아니다.

후보 경계는 다음과 같다.

1. 현재generation END 수락과ROM drain을확인한뒤다음collector geometry의export 시작만허용한다. 기존display lease의epoch/generation은유지한다.
2. ARM은기존계획완료후receiver를재사용하더라도이전표시identity를video/sink 문맥에서확인해야한다. guard 서비스의중첩SPI 호출방지·새입력오류귀속·STOP/cold 복구가필요하다. 추가RAM과Flash를아직확정하지않았다.
3. 다음입력이COMPLETE가되어도D3 prepare/COMMIT은이전최종ACK와EA retire 완료뒤에만허용한다. FPGA도잘못된조기COMMIT을독립적으로거부해야한다. export시작허용과COMMIT허용을한신호로합치지않는다.
4. END/drain/새export 진행중/old retire/새COMMIT 각경계의STOP·epoch변경·늦은응답을검사하고실제M4·source·65816 일정에연결한다. 실기493 Flash148B/136LE,실험495 Flash96B/287LE 예산을각각유지하며면적·시간개선은새전체측정전까지미확정이다.

S9는진행중이다. 다음공정은이M4 endpoint의소비완료를실제65816 사건에연결하고생산준비를실제ROM/IRQ 일정에묶는것이다. 기존496의4credit 모델을전체실행으로승격하지않는다. 선택로컬은temp/nes-bulk497-arm02,첫양성시험arm01도보존했다. 정상493/489·GBC/save·독립검사·STOP·최종ACK·VBlank·메뉴복귀 기준은유지한다.
