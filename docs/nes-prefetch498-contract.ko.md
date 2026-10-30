# NES498 — END/drain 이후 다음 입력과 이전 표시 identity 분리

[PR138](progress/pr-138.md) · [검증](../analysis/prefetch498-verification.json) · [직전 경계](nes-bulk497-contract.ko.md) · [구현 recipe](../tools/nes_prefetch498.py).

실험 후보이며 정상 실기493·9.57fps를 대체하지 않는다. 다음 입력 수신과 이전 표시 대기를 겹치는 코드를 실제 ARM과 FPGA에 연결했다. 전체 시간 단축·연속 프레임·실기 메뉴 복귀는 새로 입증되지 않았다. 새 설치 ZIP은 만들지 않는다.

## 구현한 소유권 경계

FPGA는 기존 NES 클록 END 수락 latch인 plan_batch206.closed를 외부로 노출한다. generation 검사에 통과한 END가 실제 수락되고 ROM reader가 drain된 뒤에만 기존 표시 lease를 유지한 상태로 다음 collector export를 시작한다. drain은 IDLE 시작 조건으로만 검사한다. 전송이 시작된 뒤에는 기존 lease/END 조건으로 유지하며 정상 ROM 접근 재개가 진행 중인 입력을 취소하지 않는다. arb_idle만으로 시작하지 않는다. 새 frame RAM이나 END 완료 latch는 추가하지 않았다.

ARM은 최종 표시 ACK 대기의 reason2/no-progress callback에서 기존 receiver를 재사용한다. source poll만 수행하고 COMPLETE에서 멈춘다. D3 prepare/COMMIT은 callback 안에 없으며 이전 full ACK 검사와 EA retire가 끝난 다음 runtime step에서만 실행한다. 이전 표시 번호와 통계는 receiver가 아닌 video/sink의 generation을 사용한다. 입력 중 IO·CRC·deadline 오류는 fail-stop으로 전파한다. credit/bulk 대기는 입력 callback을 실행하지 않는다.

FPGA의 D3 ack_accept에도 기존 export_permitted를 적용한다. 이전 lease가 살아 있는 동안 조기 D3는 기존 exporter의 거부 경로로 간다. 최종 ACK 확인은 ARM의 기존 full E0 검사, EA 완료와 lease 해제는 기존 FPGA 경로를 사용한다. 새 COMMIT gate 자체를 독립적인 SNES 최종 ACK 해석기로 설명하지 않는다.

STOP/reset·기존 독립 CRC/coverage·VBlank·SNES 프로그램은 유지한다. receiver를 미리 바꾸므로 이전 주석의 COMMITTED 상태 보존을 새 동작으로 인용해서는 안 된다. 실패 뒤에는 다음 BEGIN을 진행하지 않는다.

## 확인 범위

실제 linked498 wait callback은 이전 표시907을 보존하며 다음 입력908을46회 input transfer로 COMPLETE까지 받았고 D3는0회였다. COMPLETE 재호출 및 다른 wait reason에서는 새 입력 전송이 없었다. IO/CRC/deadline 및 첫 D2 뒤 service 취소·deadline의5반례는 모두 실패했고 새 COMMIT이나 실패 뒤 추가 SPI는 없었다. 정상 수신의6개 geometry 배열과 raw byte도 원본과 일치했다. 전송 endpoint와 tick은 fixture이므로 이 횟수를 실기 시간으로 환산하지 않는다.

실제 runtime post-SEAL/retire 시험은 다음 receiver가 COMPLETE908인 상태에서 표시907 기록과 EA907을 유지했다. 기존493 코드는 같은 주입 조건에서 generation 불일치로 거부했다. planner와 최종 ACK grant를 모델링한 경계 시험이며 실제 화면의 증명은 아니다.

실제 plan END 해석기·lease·exporter 시작 경계는 정상/foreign END/STOP과4개 잘못된 변경 검출을 통과했다. END 제거, drain 제거, 진행 중 drain 재검사, COMMIT gate 제거를 각각 검출했다. 고정 MMC3 fixture의 C/RTL/기존65816 공동 실행은2표시·68ACK·4bulk 소비·12928VRAM byte·STOP/observer를 통과했다. COMMIT12→최종ACK/EA12→COMMIT13→최종ACK/EA13 순서를 기록했다. 첫 RGB는495와 동일하다. 두 번째 전체pixel oracle이나 실제 SMB3 플레이 시험은 아니다. 두 세대의 COMMIT 경계를 확인한 기능 시험이며 실제 M4 instruction/IRQ와 공통 시계가 아니다. 장시간 캡처 무손실·물리 메뉴 복귀는 입증하지 않는다.

## 동일 보드 전체 비용

| 항목 | 실기493 | 실험495 | 실험498 |
|---|---:|---:|---:|
| Lite LE / 잔여 | 15272 / 136 | 15121 / 287 | 15132 / 276 |
| 조합논리 / FF | 14078 / 8392 | 14097 / 8394 | 14105 / 8394 |
| RAM / M9K | 264800bit / 51 | 동일 | 동일 |
| 관련 setup / hold | +0.183 / +0.168ns | +0.046 / +0.164ns | +0.084 / +0.147ns |
| ARM firmware / Flash 잔여 | 212844B / 148B | 212896B / 96B | 212984B / 8B |
| BSS / RUN workspace | 18572B / 31848B | 동일 | 동일 |
| SNES program | 기존489 | byte동일 | byte동일 |

495 대비 +11LE/+8조합논리/+88FlashB다. 실기493 대비 LE는140개 적지만 조합논리는27개, FF는2개 많다. LE 차이는 packing 결과이며 제어140개 삭제로 해석하지 않는다. 동일 seed/기존 제약의 전체 Lite compile 및 관련 timing을 통과했다. nominal 감사도 setup+0.084/hold+0.147ns다. 전체 reset/CDC/IO signoff는 여전히 미완료다.

ARM wait498 함수 자체는 stack24B, runtime step56B(기존64B)다. 실제 callback→수신/복원 실행에서 관찰한 최대 stack은728B다. 24B는 개별 함수의 정적 비용이고728B는 분리 실행한 callback 체인의 관찰값이다. 새 SEAL→receive 중첩과 IRQ를 포함한 최대 stack 여유를 뜻하지 않는다. Flash8B만 남으므로 추가 계측을 공짜로 취급하지 않는다.

loader의 check_failed→WRITE next-state 경로가 timing을 제한했다. commands_blocked로 개별 명령을 먼저 가린 뒤 조합하는 대신, 차단/비차단 조건을 각각 해석한 뒤 선택하도록 바꿨다. 추가 clock 단계나 reset/STOP/PSRAM pulse 변경은 없다. 해당 next-state의512조합 RTL 동등성과 blocked 검사를 없앤 mutant 검출이 통과했다. 공동 source/65816 실행의 보드와 비용 측정 보드 사이에는 이 loader 조건식 차이가 있음을 별도로 고정한다.

## 시간 판정과 다음 순서

현재 실기493의9.57fps만 유효하다. 498 전체 frame ms/FPS와 이득은 미측정이다. 입력 비용이 SEAL 대기 안으로 옮겨졌으므로 기존 receive/SEAL phase를 그대로 비교하거나 합산하면 안 된다. SPI 전송량 자체를 줄인 변경도 아니다. 입력이 진행되는 동안 ACK 확인이 늦어지는 비용까지 포함해야 한다.

1. **완료:** END/drain·이전 lease·새 COMMIT 경계와 반례를 보존한다. loader 조건식의 모든 차단/STOP/쓰기 drain 조합을 동등성 근거로 연결한다.
2. **완료:** 공동 실행에서 실제 source·queue·기존65816·STOP 경로를 확인하고 두 세대의 ACK→EA→COMMIT 순서를 기록한다.
3. **다음:** 동일 입력/시작 위상과 연속 일정에서 실제 ARM·공유 SPI·IRQ·ROM 경쟁·마지막 표시까지 연결한다. 동작 시간 모델의 한계와 별개로 실기 측정이 필요한 항목을 유지한다.
4. **후속:** 전체 이득과 부팅/복구 경계를 확보한 뒤에만 새 번호의 paired 전달본을 선택한다. README의 실기 상태와493 원복은 그때까지 유지한다.

초기 whole01은 잘못된 작업 경로, whole02는 source 하위 폴더 누락으로 compile 이전/도중 실패했다. 초기 whole03/candidate03은 모든495 입력 hash를 확인한 전체 source로 compile을 통과했지만 아래의 기능 실패로 기각했다. timing01의 nominal 제약 누락 결과는 폐기했다. timing02는 초기 후보의 제약 수정 기록이며 최종 선택은 whole07/timing05다. live01은 fixture가 새 callback을 덮어쓴 사실을 발견해 중단했으며 제품 실패나 라이선스 문제로 분류하지 않는다. raw 실패 기록은 로컬에 보존한다.

초기 candidate03/board02는 timing을 통과했지만 live02/03에서 다음 generation13 exporter의 error1/ABORT와 이전 lease fault가 발생했다. 당시 sink status는01 80 00 00 d0 00으로, 정상 상태를 시험이 과하게 제한한 문제가 아니었다. source의 drain을 연속 enable로 쓴 결함은 실제 exporter 경계의 negative control로 재현했다. candidate04의 외부 busy 유지 방식은 setup−0.313ns, candidate05의 IDLE 시작 분리는−0.285ns로 각각 보류했다. candidate06/board05는 동일 seed/제약에서 loader의 동일 의미 조건식까지 연결한 결과다. 실패를 재분류하거나 제약을 완화하지 않았다.

live04는 세 실행기가 정상 종료한 뒤 기존 후처리의1표시 기대값에서 실패했다. 기대값을2로 수정하고 원래 로그·RGB·ownership·consumer 산출물만 다시 검사한 postcheck01을 선택했다. 재시뮬레이션 성공으로 바꾸어 기록하지 않으며 원래 실패를 보존한다. 수정한 생성기를 시뮬레이션 없이 실행해2표시 기대값과 기존 실행의 host/native/runtime/RTL bench byte 일치도 확인했다. 선택 근거는candidate06/board05/whole07/timing05,ARM test04/identity03,boundary03,loader01,live04/postcheck01이다.
