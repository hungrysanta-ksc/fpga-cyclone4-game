# NES421: 남은 reset·I/O 및 무시된 loader 예산 감사

419 Lite 배치와 기존 224 `io02`에서 같은 측정 스크립트가 추출한 음의 recovery/removal 경로를 `(corner, 종류, 출발·도착)` 기준으로 비교했다. 각 39개가 **완전히 동일**하다. 21개는 core reset→sink bridge, 12개는 core 내부 mailbox release, 6개는 sink ROM fault 동기화 경로다. 224에서도 이미 존재하던 경계지만, 경로 집합 동일성이 새 보드의 전기적 안전이나 비동기 reset release의 완전한 MTBF 승인은 아니다. payload 음의 reset 경로 0개와 epoch reset 576개 양수는 420의 별도 범위다.

무시된 `*|loader|state*` max-delay는 224에서도 이미 집합이 비어 있었다. 현재 loader의 one-hot `phase`에서 `loaded_bytes`까지를 SDC 변경 없이 3개 코너 각각 171경로 측정했다. slow 85C 최대 data delay **5.524ns**, 일반 setup 최악 **+0.351ns**다. 기존에 적었던 5.3ns 가이드보다 **0.224ns 길다**. 무시된 가이드를 조용히 고쳐 통과로 처리하지 않는다. 같은 소스에서 phase/byte count 소유권을 확인해 실효 가이드와 실제 timing을 함께 판단하고, 필요하면 회로를 수정한 뒤 동일 보드 FIT/STA를 재검증한다.

기존 제약의 미제약 입력 54·출력 56포트는 ROM·SNES·SPI 등 외부 경계이며, 420의 조건부 디지털 envelope와 실제 장치·보드 조건을 구분해야 한다. 실제 70ns PSRAM·SNES·SPI 및 PCB의 물리 보장, reset 위상·정지 클록을 전체 signoff한 것은 아니다. 측정 전용 TSV·원본 해시와 재현 계산은 `analysis/nrom421-audit.json`을 참고한다. Lite FIT만으로 배포 package를 승인하지 않는다.
