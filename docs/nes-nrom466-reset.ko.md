# NROM466: sink reset 후보 보류

457에 기존451의 sink admission 로컬 reset 변경을 적용했다. QSF 지정 입력66개 중 nes_sink_bridge165.sv만 달랐으며 예외·핀·seed는 변경하지 않았다. 직접 raw_cancel reset이던 host_ready·idle_ss[1:0]·idle_write[1:0]를 기존 local release 체인의 reset으로 해제한다. 취소의 비동기 출력 차단은 유지한다.

단일 Starter FLOAT 순차 시험에서 16개 위상의 진입·취소·정지 클록·재시작이 통과했고, 전체 보드의 기준/메모리 클록 중단·sticky 차단도 통과했다. Lite 전체 FIT는 14,846LE/13,618comb/8,037FF/185,824 RAM bits다. 목표5개 상태의 모든3코너 recovery 최소 +9.049ns/removal 최소 +0.506ns를 확인했다.

다른 관련 동기 경로 check_next[18]→reader check_response_address[8] setup이 −0.091ns로 회귀했다. hold는 +0.141ns다. 이 후보는 채택하지 않으며 467 전달본에는 기존457을 사용한다. raw CDC/IO 전체 signoff로 계산하지 않는다. 표시 공동 회귀의 최종 상태는 analysis/nrom466-reset.json에 별도 기록한다. 단일 fit 결과이며 seed 반복으로 해결하려 하지 않았다. 원본 보고서·소스·로그는 probes/nes-nrom466에 보존한다.

표시 공동 회귀는 FIT의 동기 setup 회귀가 확정된 뒤 불필요한 실행을 줄이기 위해 해당 시험 소유자의 Questa 자식만 식별하여 중단했다. 드라이버는 실패 종료하며 이는 제품 프로토콜 실패나 표시 PASS가 아니다. 취소 이유와 로그를 보존하고 wrapper가 seat를 반환했다.
