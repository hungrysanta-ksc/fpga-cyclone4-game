# NROM450: 제한 표본의 reset 경로 분류

419의 `boundary165-paths.tsv`에 기록된 음수 recovery 표본 39행을 원본 RTL과 대조했다. 세 timing corner의 동일한 13개 종단이며 모두 NES 클록 `core_release|release_reset[1]`에서 출발한다. 이 파일은 전체 reset 경로가 아니라 추출 표본이다. 원래 STA의 최악 recovery −8.824ns와 표본 최악 −7.829ns는 범위가 다르다.

- 4개 종단은 mailbox의 `sr`/`dr` 로컬 해제 체인이다. 각 도메인 payload와 protocol은 그 체인의 뒤에서 해제된다. 비동기 해제의 물리적 metastability 가능성이 사라진다는 의미는 아니다.
- 2개는 sink의 로컬 해제 체인이며 payload/session reset을 구동한다.
- 5개는 sink의 `idle_ss`, `idle_write`, `host_ready`다. 원본은 공통 취소로 비동기 reset하고 로컬 reset 해제와 입력 idle 상태가 모두 만족될 때 admission을 허용한다. 이 구조만으로 해당 5개 레지스터의 recovery와 실제 admission 안전성이 증명되는 것은 아니다.
- 2개는 host 클록 `sink_rom_fault` 동기화 체인으로, 공통 core reset에 직접 비동기 해제된다. 로컬 동기 해제 적용을 후보로 검토할 가치가 있으나 즉시 STOP·fault 전달, 시작 지연, 재배치 비용과 전체 동작을 함께 검증해야 한다.

이 분류는 회로 변경이나 false-path 추가, timing 통과가 아니다. 각 체인의 실제 clock/reset 소유권과 assertion·release 순서를 확인한 뒤 기능 시험과 같은 보드의 Lite FIT/STA를 다시 수행해야 한다. IO 54개 입력·56개 출력의 미제약 상태 및 회로 전체 raw reset/CDC 문제도 그대로 남는다. `analysis/nrom450-reset.json`은 표본과 RTL 해시를 고정한다.
