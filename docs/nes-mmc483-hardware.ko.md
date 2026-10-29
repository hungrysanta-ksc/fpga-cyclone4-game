# MMC482 실기 성공·게임 비용 기준선483

**실제 SMB3(J)에서 시작·약60초 실행·877회 최종 표시 완료·STOP/base·메뉴 복귀를 확인했다. 평균14.60fps다.** 성공 범위는 실제 게임 경로 진입이며60fps 달성이나 전 게임 호환성은 아니다. [원문 해시·계산 JSON](../analysis/mmc483-hardware482.json) · [다음 작업 순서](nes-mmc483-next-plan.json).

## 실기 결과

| 항목 | 결과 |
|---|---|
| 조합 | ARM482-01 / FPGA482-01, profile7b / status3, 엄격 SMB3 CRC5a04eed7 |
| ROM | 전체393216B 적재·readback 일치, verified1·오류0 |
| SNES 시작 | boot_reason1 READY,5tick=50ms,440poll; STOP 전 boot_last=01fca903 |
| 표시 관측 | DISPLAY_NEXT232720ms→DISPLAY_STOPPED292780ms、60.06초 |
| 최종 완료 | 877프레임·EA877, 평균14.6021fps·68.4835ms/표시 |
| 5초 bin별 완료수 | 92,55,57,60,82,67,56,74,88,89,87,70; frame 시작 기준 배정 |
| 오류 | run/ROM/receiver/video/plan/CRC/driver 오류0, input abort0 |
| 입력·SPC | NES에서 완료한 버튼 변화18건, 최근16건에 A/START/방향키 포함. SPC init 결과A9·unmute 확인 |
| 복귀 | STOP 오류0·base_restored1·safe_to_reload1·사용자 정상 메뉴 복귀 보고 |

사용자는 실행 성공·정상 메뉴 복귀를 보고했고 새 영상은 없다. 월드맵/1-1 진입, 실제 청취 음질, 모든 sprite/bank/IRQ를 확인했다고 확대하지 않는다. screen_error169는 SPC 결과A9이며 run_error가 아니다. legacy screen_frames0/phase_mask0도 표시0회를 뜻하지 않는다. 여기서 표시 완료수는 검사·SEAL·최종ACK 뒤 EA까지 완료한 수다.

원래480은 같은 ROM에서 stage0으로5초 timeout이었고482는50ms에 stage3 READY가 됐다. 다만 동등한 loader 오류 논리와 보드 배치가 함께 달라졌으므로 **이 한 번의 성공으로480의 물리 실패 원인을 특정 논리나 타이밍 경로 하나로 확정하지 않는다.** qualified vector flags0/1도 이번 성공에서 관측되지 않았다. 순간 신호 미관측을 실행 부재로 단정하지 않는다.

## 시간을 쓰는 곳

| 전체 단계 | DWT 합계 / 완료877회 | 해석 |
|---|---:|---|
| 입력 수신 | 17.16ms | 입력 검사·전송·IRQ/guard/대기 포함 |
| 계획·타일 공급 | **32.32ms** | 순수 ARM 계산뿐 아니라 계획 발행·생산 완료 대기 포함 |
| SEAL·최종ACK | 18.44ms | 출력 전송·독립 검사·소비/표시 대기 포함 |

단계 합은67.92ms이며 전체68.48ms와의 차이는 부팅·retire/guard·종료 시 미완료 단계 등을 포함한다. 각 단계는 마지막 프레임이 실패한 지점까지 같은 방식으로 닫힌 것이 아니다. op/quiet는 이 단계 안에 중첩되므로 더하거나 모두 제거 가능한 비용으로 빼지 않는다.

- 10ms tick의 거친 분해에서 계획 단계는 planner−callback 약14.22ms, callback0.55ms, BEGIN1.60ms, finish16.03ms다. **계산과 후속 tile/descriptor 공급 대기가 모두 크다.** 함수별 실제 cycle 분해는 다음 검증 대상이다.
- E8은78289회/1,565,780B, 전송 함수 안의 측정 약9.76ms/표시다. E0은61578회/1,231,560B, 약7.67ms다. E8/E0의 필요 진행 확인·descriptor 회수와 불필요 반복을 구분해야 하며 전부 삭제할 수 없다.
- E0 관련128µs quiet 대기 누적은 약7.03ms/표시다. 그중 최종ACK4.31ms, drain2.36ms, credit0.35ms이며 위 단계에 포함된다. 대기를 줄이면 반복 SPI가 늘거나 VBlank 도착 시각이 달라질 수 있어 전체 시간으로 비교한다.
- 실제 native SPI는6,180,018B/195873거래다. 현재 관측 전송 횟수를 고정하면2.625MHz의 이상적 wire만 **21.48ms/표시**다. 필요 없는 상태 반복을 줄이면 이 양도 달라지므로60fps 불가능성 증명으로 사용하지 않는다.
- group 재사용2243/26340=**8.52%**로 문양의27/28=96.43%와 다르다. budget의 OBJ 항목 누적23548·mapdirty 행 누적1672도 관측됐다. 문양24fps와 게임14.60fps를 같은 장면의 성능 퇴보율로 계산하지 않는다.

현재 평균에서30fps까지 약35.15ms,60Hz까지 **51.82ms/표시**를 줄여야 한다.60Hz는 약75.66%의 전체 지연 감소가 필요하다. 한 CRC 함수나 quiet 대기만 고쳐 달성할 규모는 아니다. 입력17ms도 목표보다 길어 계산·공급·입력·VBlank 일정을 함께 검토해야 한다.

## 종료 경계

유효 입력 COMMIT878건 중 최종 표시877건을 셌다. 마지막 generation899는60초 deadline에 걸려 완료로 세지 않는다. native_result1은 정상 제한시간 종료다.

window sent=retired=12709지만 실제 E1 전송은12710회다. 실제 transfer 뒤의 runtime guard가 deadline을 발견하면 wire 계수는 증가하고 send의 software sent 증가는 실행되지 않는다. 이 때문에 window_error3·sink_error2와 ACK 미확인이 남는다. driver 실패0·deadline1·마지막 SEAL 요청·run/STOP 오류0을 함께 확인했으며 단독 숫자를 새 통신 오류로 해석하지 않는다. **sent=retired만 보고 물리 큐가 비었다고 주장하지도 않는다.** 마지막 packet의 실제 수신/표시는 미확정이고 STOP/base/menu 복구는 정상이다.

## 다음 작업

1. **기준선482를 보존한다.** 이번 분석에는 새 RTL/ARM/합성을 하지 않는다.480 실패와481 기각도 그대로 둔다.
2. 현재482 RTL에 actual M4 planner의 함수별 비용과 E8의 busy/descriptor/credit/finish 상태를 연결한다. 먼저 기존 게임 입력·실제 C/linked ARM 재생으로 조사하며 계측만 늘린 실기 전달본을 반복하지 않는다.
3. 게임에서 group 변화가 많아도 계산량이 줄어드는 ARM 경로와 tile 공급/finish 일정을 함께 선택한다. 반복 E8/E0·상태 해석·대기를 줄일 때 독립 검사·4credit·ROM/IRQ 중재·STOP·최종ACK를 유지한다.
4. 동일 ROM/입력 조건으로 전체 수신→계획→표시를 비교한다. p95·capture 누락·NES 실시간 속도·VBlank/ROM 위상은 현재 로그만으로 확정하지 않는다. 다른 단계로 시간이 이동한 후보는 성공으로 세지 않는다.

회로는 전달482의 Lite15254LE/14049comb/8392FF/256608bits,154LE 잔여를 재사용한다. 관련 setup/hold+0.133/+0.132ns지만 전체 CDC/IO 승인은 미완료다. ARM Flash636B와 동일 RUN31848B는 여유의 상한/기존 사용량이며 full stack/IRQ나 추가 RAM 여유를 증명하지 않는다. MMC4/5·지속60fps·NES 제품 공개도 미완료다.

원문3TXT는 `probes/nes-mmc483/hardware482-01`에 byte 그대로 보존했다. `tools/analyze_nes_mmc483_hardware.py --raw <원문 폴더> --out <새 JSON>`으로 source hash/단계·거래·byte·quiet·종료 경계를 재계산한다.
