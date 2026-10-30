# NES496 — 실제 묶음 규칙과 다음 입력 소유권 확인

[검증](../analysis/schedule496-verification.json) · [495](nes-status495-contract.ko.md) · [PR138](progress/pr-138.md).

실기493·9.57fps를 유지한다. 이번에는 시간 모델의 타일 묶음 오류를 수정하고 실제 lease RTL의 다음 입력 차단을 확인했다. ARM/FPGA 제품 구현 변경·새 합성·설치 ZIP은 없다. 실제 ARM polling을 공통 시계에 연결하는 S9는 진행 중이다.

## 시간 모델 교정

기존 fixture는 12프레임의219개 타일 계획마다bulk를 발행했다. 실제tile_bulk206의 같은kind·연속slot·동일generation·2048B 한도 규칙을 적용하면32개다. 타일3824B와 순서·목적지를 바이트 단위로 재구성해 대조했고 전체packet은583→396개다. sequence/token을 새 묶음에 맞춰 재부여하되 ordinary payload는 유지했다.

실제 기존48965816을 실행한4조건 모두 표시/ACK/VBlank 검사를 통과했다. 기존495의 원본요청과12개 최종픽셀도 정확히 같다. 같은 시작 시각에서full/short 모두657.420086ms,4ms 이동에서653.411988/653.428471ms였다. 앞선757.253156ms와의 약99.83ms 차이는 **이미 존재하는 FPGA 묶음을 모델에 반영한 교정**이지 새 회로의 성능 향상이 아니다. EB 진행응답의 실기 개선 증명도 아니다.

남은 차이는 명확하다. 실제 ARM complete485는bulk_pending에 대해E0 drain을 수행한 뒤 다음bulk를 제출하고 FINISH는 모든bulk 소비를 기다린다. 현재fixture의4credit 공급은 이 M4 실행을 재현하지 않는다. E8·busy-poll·128us quiet/IRQ·ROM 생산 시각도 아직 공통시계에 없다. 따라서 이번 숫자를 실기FPS나 전체시간 하한으로 사용하지 않는다.

## 다음 입력의 실제 차단 지점

선택 보드의nes_capture_lease201는 waiting_display 동안export_permitted를0으로 만든다. nes_live_joint의native_export.enable이 이 신호에 직접 연결돼 있다. 다음collector 캡처는 진행해도ARM으로의 다음export 시작은 이전표시retire까지 막힌다. ARM receiver만 조기에IDLE로 바꿔도 다음입력 전송은 시작되지 않는다.

실제lease RTL에서 frame1 export→frame2 capture→reader drained→frame1 retire→frame2 export를 실행했다. 이전generation1 유지,drain만으로export 불가,정상retire가 다음collector를release하지 않음,generation2 전환,stale retire 차단,STOP 취소를 통과했다. waiting_display gate를 제거한 잘못된 구현은 첫lease 검사에서 거부됐다. 보드 연결은source 고정검사이며 전체파이프라인 시뮬레이션은 아니다. Questa Starter FLOAT1좌석으로 순차 실행했다. 첫 샌드박스 실행의host 조회 실패는 보존하고 기존 승인 wrapper를 정상 환경에서 실행했다. 추가 라이선스 문제는 아니다.

## 다음 구현 순서·예산

1. 실제M4 E8/complete485/E0 대기를 실제chunk 완료와 연결해 한개pending bulk·2bank 소유권을 시간 모델에 반영한다. 저장credit·receipt·queue ACK·최종display ACK를 각각 기록한다.
2. 입력 겹치기는source export 시작과새입력 COMMIT을 분리하는 후보로 검토한다. reader drain 후다음geometry 전송을 허용하더라도 새COMMIT으로 이전display generation을 덮어서는 안 된다. 이전ACK/EA 뒤에만새lease를 확정하는 소유권과STOP/epoch/실패시cold 복구가 필요하다. 단순히gate를 제거하는 구현은 이번negative 시험이 거부한다.
3. ARM은 receiver/video가 별도workspace지만SEAL 뒤에도r.generation과retire/consumed를 사용한다. 이전identity 고정과서비스guard의SPI 재진입 방지,다음입력 수신오류 귀속이 선행돼야 한다. 기존video.generation 재사용 가능성은후보이며새코드로검증하지 않았다.
4. 정상493 Flash148B/136LE,실험495 Flash96B/287LE를 초과하는 비용은 기존제어의실제삭제와함께 계산한다. 큰두번째frame RAM 추가를 전제하지 않는다. 전체이득·부팅경계 확인 후에만새paired 실기를 준비한다.

재현 도구는 [묶음/CPU](../tools/test_nes_schedule496.py), [lease/negative](../tools/test_nes_lease496.py)다. 로컬 선택은temp/nes-schedule496-test01과nes-lease496-test01이며원시결과·실패는보존한다. source·요청·픽셀 비교와비용의한계는공개JSON에고정했다. 기존493/489·GBC/save·STOP·독립검사·최종ACK·VBlank·메뉴복귀 기준은유지한다.
