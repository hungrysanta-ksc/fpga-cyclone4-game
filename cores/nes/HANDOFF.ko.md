# NES 다음 작업 인계 — 067 이후

현재 **NES-DIAG-MEMORY-067 / CF67**. PR21 병합 `ea6d576a6df176eabde7744a851168c515040191`에서 `codex/nes-diagnostic-memory-067`로 진행했다. [결과](../../analysis/DIAG-MEMORY-RESULT.ko.md), [계약/재현](../../docs/nes-diag-memory-contract.md), [다음 6.1 Sol High 작업 상세 인계](../../docs/development/NES-067-SOL-HANDOFF.ko.md)를 먼저 읽는다. 사용자 모델 변경 예정은 기록했으며 앱 모델을 임의 변경하지 않았다.

## 완료한 범위

진단 전용 쓰기/읽기 SETUP와 읽기 샘플 후 HOLD/RELEASE를 구현했다. 정상4경우 전체344064바이트 쓰기/읽기,각9취소,세 보호 제거 및126ns 범위 밖 실패 대조를 통과했다. 실제060 C GPIO bounded load/CHECK72312응답 비트,PLL상실/복구/START두 장벽도 통과했다. CHECK96KiB는TB loader 준비이며 새 전체SPI 성공 세션은 아니다.

새067 fit는2372LE/184LAB/1466registers/44M9K/135physical/0virtual/PLL1.3corner30내부summary 양수,최소hold0.150ns. 외부54input/744paths·49output/1355paths는 미제약이다. 단위·wave·fit 생성 소스 동일성을 verifier로 확인한다. 기존061 fit를 재사용한 결과가 아니다.

## 다음 순서

1. 같은067 회로의 PSRAM/SPI/SNES 외부 min/max와 전원tPU150µs·클록 정지/CE최대8µs 조건을 확정한다.0/2/20ns 시험점은 실제PCB 측정값이 아니다. locked를 강제로 내린 시험으로 실제PLL 감지시간을 승인하지 않는다.
2. 최종 회로로 전체C80/96KiB 적재/전byte비교/마지막ACK/FINISH/status/STOP을 재생한다.065 MCU의CF61 조건을 새CF67 후보에 연결하고 구형거부/복구/실제ARM호출을 회귀한다. 기존 소스와 동결 trace는 새 파생 실행기의 입력으로만 쓴다.
3. 같은 소스의Standard ASM/압축 roundtrip/새ARM manifest를 만든 뒤 실제SD 원본/base/menu·독립 백업/복원 조건을 확인한다. 외부 실기에 패키지 전달→SD TXT 회신으로 진행한다. 현재 installable=false라 새SD복사를 요청하지 않는다.

## 보존할 기준

실물 부품은 모두 확인됐다. FXPAK Pro Mk.III Rev.D/STM32F401RCT6/EP4CE15F17C8N/IS66WVE4M16EBLL-70BLI×2/IS62WV5128EBLL-45HLI. 추가분해·사진·ID질문은 필요 없다.044 LINK SCREEN순환·GBC정상 보고와 전체코어059959LAB/4여유·마지막8프레임은 별도다.066은061FPGA/065ARM의 오프라인쌍으로 보존하며 새CF67과 혼합하지 않는다.

준비도5완료/6부분/1미완료를 유지한다. H06외부IO는 미완료이며 내부timing·부품식별로 승격하지 않는다. PREPARED SD와RAM/UART RESET-release는 실제화면복귀 관측과 다르다. base/nativeSD오류의RESET/USB보호·SD금지 및 불확실DATA/ACK재시도금지를 유지한다.

로컬067 evidence401파일/112DB파일은동결됐고 [요약](../../analysis/diag-memory-verification.json)에manifest가 고정돼 있다. `probes/freeze_nes067.py` 및044–066 finalizer를 재실행하지 않는다. 기존Starter FLOAT 한seat를순차 사용하며license/raw/ROM/DB는공개하지 않는다. 주요검증진전마다명시적stage·commit·push·한국어PR,본문은작업목표→작업내용→작업결과. 병합상태는다음작업에서새로확인한다.
