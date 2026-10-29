# NROM456: 455 reset 표본과 실기 경계

455의 420 방식 `inventory206.tsv`에서 서로 다른 NES/PLL 클록 사이 음수 recovery 표본은 576행, 중복 제거 시 종단 62개다. 이 데이터는 각 클록 쌍·corner의 top-N 표본이며 전체 경로 목록이나 안전 승인 판정이 아니다. 이름을 기준으로 나누면 로컬 reset release 체인 36개, clock guard 상태 19개, sink idle/admission 5개, sink ROM fault 동기화 2개다. 원본 전체 이름과 입력 해시는 `analysis/nrom456-reset.json`에 보존한다.

clock guard 상태 19개는 board 8MHz `power_release[3]`가 만든 공통 reset이 NES 기준 클록 상태에 비동기 해제되는 표본이다. 원본 guard는 20~22MHz NES 기준 및 168MHz memory 클록을 각기 사용하며, 감시 fault는 클록 복귀만으로 해제되지 않는다. 각 영역의 reset deassert를 해당 클록에 동기화할 후보는 합리적이지만, 기준 또는 메모리 클록이 멈춰도 차단되는 비동기 assertion·sticky fault와 startup 대기·두 클록 동시 중단의 알려진 한계를 함께 유지해야 한다. RTL·기능·전체 FIT/STA로 확인하기 전에는 해결로 세지 않는다.

455 raw recovery 최악은 core release에서 host tile bulk의 `hcancel` 로컬 release 체인으로 간다. 로컬 체인이라는 이유만으로 첫 단계·두 번째 단계의 회복, 배선과 물리적 메타안정성을 자동 승인하지 않는다. sink 5개와 ROM fault 2개도 별도 소유권 검토가 필요하다. 455 구현 보고에는 input 54·output 56 미제약 포트가 여전히 남아 있으며 그 경계의 전기적 데이터는 실측이 아니다.

이 단계는 기존 자료 재분류만 수행했다. SDC false path 추가, 회로 변경, 새로운 합성, 실기 또는 base/menu 복구를 수행하지 않았다. 실제 지속 60fps와 MMC4/5 비용도 미측정이다.
