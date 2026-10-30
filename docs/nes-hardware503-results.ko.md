# MMC502 실기 수신 분석503

[측정 JSON](../analysis/hardware503-mmc502.json) · [502 구현](nes-capture502-contract.ko.md) · [현재 계획](nes-audit499-plan.json) · [PR139](progress/pr-139.md).

## 판정

사용자는 실행·메뉴 복귀 정상과 분명한 프레임 개선을 보고했다. 실제 로그는 **60.07초 동안 최종 표시636회, 평균10.59fps /94.45ms**다. 이전493의575회·9.57fps보다61회, 관측 평균은10.61% 높다. 같은 동선의 재측정493 로그나 이번 장면 영상은 제공되지 않았으므로 이것을502만의 인과적 가속률이나 첫 레벨 전용FPS로 해석하지 않는다. 60fps는 미완료다.

**502를 현재 기능 실기 기준으로 선택한다.** 384KiB 적재/CRC/readback·profile7b·START·부팅50ms·입력 흔적·STOP·base 복구가 정상이고 사용자가 실제 메뉴 복귀를 확인했다. CRC/failed transfer/ROM/receiver/video 오류와trace abort는0이다. 전송된 바이너리의 hash는 로그에 없으므로 candidate/profile/ROM CRC와 전달 manifest를 연결한 판정이다.

## 처리 비용

| 관측값 | 493 | 502 | 차이 |
|---|---:|---:|---:|
| 최종 표시 /60.07초 | 575 | 636 | +61 |
| 평균fps | 9.57 | 10.59 | +1.02 |
| 전체ms/표시 | 104.47 | 94.45 | −10.02 |
| DWT 수신 포함ms/표시 | 28.97 | 22.14 | −6.83 |
| 계획·타일 공급 포함 | 33.05 | 31.32 | −1.73 |
| SEAL·최종ACK 포함 | 41.33 | 40.27 | −1.06 |
| 전체driver wire 투영ms/표시 | 32.20 | 29.99 | −2.21 |
| 조회 제외wire 투영 | 17.96 | 18.02 | +0.06 |
| D0 조회횟수/표시 | 100.48 | 33.46 | −67.02 |

수신 단계가 가장 크게 줄었다. raw/수집 경계 수정 뒤 D0 입력 준비 조회가 감소한 관측과 일치하지만, 동일 장면이 아니므로 모든6.83ms를 특정 회로의 절감으로 확정하지 않는다. E1/D1 본문 전송량이 실기에서도 동일 비율로 줄었다는 주장도 하지 않는다.

5초 **frame-start 기준** 묶음은61,85,50,41,39,36,48,53,75,65,44,39회다. 장면별FPS·최종 표시 간격p95가 아니다. 단계 DWT에는 실제 ARM·IRQ·guard·SPI/ROM 대기가 들어 있으며 이를 개별 원인으로 분해하지 못한다. driver op와 quiet는 단계 내부에 중첩된다. CREDIT9.88ms/DRAIN1.88ms/FINAL_ACK8.95ms를 위 표에 다시 더하지 않는다.

## 수집 거부와 남은 불확실성

이전493의 마지막16개 전이에는 fetch01/04/06 거부8episode가 있었다. 이번502에는8개 전이(거부4/회복4)가 있고 **fetch/compact/raster/ROM 오류 필드는 모두0**이다. 기존 fetch 결함이 이번 보존 이력에서 사라진 점은 bounded 수정과 사용자 체감 개선을 뒷받침한다.

남은 거부4개는 candidate display mask0, 회복은24(0x18)다. 렌더링 비활성 전환과 양립하지만 이 값은 오류 발생 순간의 mask가 아니다. raw patch validity 같은 모든 거부 조건이 history 오류 비트에 담기지도 않는다. 따라서 거부를 모두 정상 공백으로 면제하거나 전체 거부율/손실시간을 산출하지 않는다. generation694와637 commits의 차이도 전체 손실 프레임 수가 아니다. 필요한 경우 새 계측은 이 미분류 경계만 겨냥한다.

## 60초 종료 경계

trace637회 수신·commit 중 최종 표시636회이며 마지막 SEAL만 미완료다. runtime result1·window2·sink2, ACK 미공개·pending1·flags3·정상 identity와CRC/전송 실패0의 정확한 조합을 확인했다.

493의window3(post-transfer guard)와 달리502의window2는 window IO 전 guard 또는 wait의 제한시간 거부 경로다. 실제 전달502 ARM ELF로 정상/guard deadline/postguard deadline/진짜IO 실패4조건을 실행했다. guard deadline은1/2/2, 진짜IO 실패는3/3/2로 구분되고, 실패에서는 표시 확정·재호출 추가SPI가 없었다. 로그 반례16개도 거부했다. SPI/시계는 모델이므로 실제 종료 순간 재생은 아니며 마지막1건을 정상 표시636회에 더하지 않는다. `screen_error169`는SPC_INIT_RESULT_165이며 일반 화면 오류가 아니다.

## 다음 순서와 예산

1. A1의 bounded 수정과 첫502 실기 성공을 기준으로 삼고, 미분류mask0 전이·동일 장면 성능 검증은 열린 항목으로 남긴다. 변경 없는Questa/전체FIT/부팅 재시험은 하지 않는다.
2. **A2: 반복되는 입력·출력 본문과 늦은DMA/표시 대기를 함께 줄일 예산을 작성한다.** SEAL·최종ACK40.27ms, 계획·공급31.32ms가 우선이다. 중첩 시간을 독립 절감분으로 더하지 않는다.
3. 모든D0/E0/E8 조회를 제외한 관측wire도18.02ms/표시로16.67ms를 넘는다. 조회만 제거하는 후보로60fps를 주장하지 않는다. 본문wire15.84ms·framing·수신/복원·IRQ/ROM·VBlank를 같은 일정에 넣고 실제 삭제할 제어를 명시한다. 이 투영은 마지막 미완료 시도·70/73 op도 포함하므로 프로토콜 불가능성 증명은 아니다.
4. 전체 평균에서60Hz까지77.78ms/표시가 남는다. 보드는502의15,287LE/14,135comb/8,399FF/51M9K·121LE 여유,관련setup+.353ns/hold+.142ns다. ARM Flash148B/RUN31848B이며 전체 stack/IRQ·reset/CDC/IO·MMC4/5 승인은 미완료다.

**사용자 요청에 따라 다음 NES 시험판부터 RESTORE 폴더를 포함하지 않는다.** 사용자 백업과 기존ZIP은 보존한다. 새 후보의 firmware/FPGA·필요한marker/안내·고유로그 이름만 전달하며 동작상STOP/base/menu 복구는 계속 유지한다. 이번 분석에서는 새ZIP이나 펌웨어를 만들지 않았다.

## 보존·재현

원시3TXT는 `probes/nes-hardware503/run01`에byte/hash 그대로 보존했다. receipt.json·termination01/result.json이 근거이며 [분석기](../tools/analyze_nes_hardware503.py)와[종료 검사](../tools/check_nes_hardware503_termination.py)로 재계산한다. 원시로그/ROM/save/바이너리는Git에 넣지 않는다. 502 제작 시점의hardware_verified=false는 불변 스냅샷으로 두고 실기 판정은이503 문서/JSON을 따른다.
