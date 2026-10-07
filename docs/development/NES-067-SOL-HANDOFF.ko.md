# NES067 → 다음 작업 인계

사용자는 이번067까지 Astra High, 다음부터6.1 Sol High로 진행할 예정이라고 명시했다. 모델 변경은 사용자가 앱에서 한다. 이 기록은 실제 선택된 모델을 도구로 확인하거나 변경했다는 뜻이 아니다. 모델이 바뀌어도 아래 완료 조건을 줄이지 않는다. 어려운 IO/CDC 판단은 근거와 미확인을 분리하고 추정으로 승인하지 않는다.

## 처음 읽을 순서

1. `AGENTS.md`, `cores/nes/README.md`, `cores/nes/HANDOFF.ko.md`, `docs/development/MILESTONE-WORKFLOW.ko.md`.
2. 이번 [계약](../nes-diag-memory-contract.md), [결과](../../analysis/DIAG-MEMORY-RESULT.ko.md), `analysis/diag-memory-verification.json`.
3. [확정 하드웨어](FXPAK-HARDWARE-REFERENCE.ko.md), [EBLL 타이밍 및 기존 반례](NES-PSRAM-TIMING-REVIEW.ko.md), [준비도](NES-HARDWARE-READINESS-REVIEW.ko.md).
4. 구현에 필요한 기존065 메뉴 복귀 계약,063 전체 보드 세션 계약,066 쌍/백업 계약. 역사 파일의 “현재”는 최신 인계를 덮어쓰지 않는다.

## 잃으면 안 되는 사실

- 실제 개발 저장소는 `repository-nes-milestone/`, 원격 `hungrysanta-ksc/fpga-cyclone4-game`. 오래된 `repository/`는 작업 대상이 아니다.067 시작점은 PR21 병합 `ea6d576a6df176eabde7744a851168c515040191`이다. 다음 시작 시 PR 병합 상태를 새로 확인한다.
- 실기는 FXPAK Pro Mk.III Rev.D, STM32F401RCT6, EP4CE15F17C8N, **IS66WVE4M16EBLL-70BLI 두 개**, IS62WV5128EBLL-45HLI. 제품/부품 재질문·재분해·추가 ID 펌웨어는 필요 없다. ALL/BLL 추정 대신 실제 EBLL Rev.D3를 쓴다.
- 실기는 외부에 있고 PC 연결이 어렵다. 회복 가능한 패키지 전달 → 사용자가 SD에서 실행 → TXT·관측 전달 방식이다. 지금은 새 SD 복사를 요청할 단계가 아니다.
- 실기 성공 기준은044 LINK SCREEN 순환·자동 종료 해소·GBC 정상 보고다.059의 전체 NES 코어는959/963 LAB·4개 여유, 마지막2진단8프레임이다.067의184LAB 진단 fit를 전체 코어 여유로 계산하지 않는다.
-067은 새 loader/reader와 CF67을 쓰는 **CPU/PPU 없는 진단**이다.065 ARM·066 쌍은 CF61용이며 그대로다. installable=false. “부품 식별 완료”, “내부 STA 양수”, “전체 메모리 byte 비교” 중 어느 것도 외부 IO/전체 SPI/실기 완료를 대신하지 않는다.
- START는 parser 거부와 boot.start=0 두 장벽을 유지한다. DATA/ACK 응답이 불확실하면 무조건 재시도하지 않는다. true 반환은 안전한 메뉴 복귀 가능 여부이며 검증 성공과 다르다. base/native SD 실패에서는 RESET/USB 보호와 SD 접근 금지를 유지한다.

## 수정 지점과 회귀 경계

| 다음 일 | 진입 파일 | 완료 조건 |
| --- | --- | --- |
| 외부 min/max | `tools/nes_diag_memory_timing.py`, 생성된 `board.sdc`/`output_files/board.sta.rpt` | 같은067 소스/fit에서 주소·CE/WE/OE·byte enable·DQ min/max/PCB 예산, PSRAM 입력·FPGA 수신 조건을 표로 대조. SPI/SNES 미제약 경계도 분류. 근거 없는 false-path/multicycle 금지 |
| 전원·클록 정지 | `tools/nes_board_diagnostic.py`의 원본 top 생성 및067 파생 확장 | tPU150µs는 전원 안정 사건 기준. 현재2FF reset 해제를150µs 대기로 오인하지 않음. locked가 계속HIGH인 클록 정지에서는CE가 유지될 수 있으므로 실제 감지/복구 근거 또는 회로 필요 |
| 전체 C80/96KiB | `tools/nes_board_session.py`, `tools/nes_board_session_replay.py`, `tests/nes-functional/board_session_tb.sv` | 새 후속 실행기에서067 materializer와CF67을 연결. 마지막ACK/FINISH/status/STOP, 모든 byte/tag 및 응답 비트 검증.063 원본·동결 trace를 덮어쓰지 않음 |
| MCU ID 연결 | `src/nes/firmware/nes_menu_diagnostic.c`, `tools/nes_menu_return.py`, `tools/build_nes_menu_return_arm.ps1` | 새 후보에서CF67 승인 및CF61/44/0 거부를 적재 전에 검증. 전체 메뉴/SD 하위/오류/복구·ARM 호출 회귀. 전체 생성 ARM과 실행 trace의 소스 해시 고정 |
| 쌍/실기 준비 | `tools/nes_pair_assemble.py`, `tools/nes_pair_preflight.py`와 새 파생 실행기 | 새 fit의Standard ASM/CPF,066의 수정 encoder 규칙으로 모든 byte C 복원, 새ARM/marker/압축 manifest. 실제 SD원본/base/menu·독립 백업/복원 조건 확정 후 전달 |

먼저 외부 timing/전원·클록 정책을 구체화하고, 회로 변경이 있으면 해당 단위/파형/fit부터 다시 검증한다. 안정된 최종 회로에 전체 SPI 회귀와 ARM 쌍을 한 번 수행하는 순서가 중간 산출물 반복을 줄인다. 반대로 외부 정보 대기만 있을 때에는 독립적인 CF67 host 거부/복구 테스트를 진행할 수 있다. 사용자 SD 경로를 얻지 못한 상태에서 원본을 가정하거나 실제 백업 완료로 쓰지 않는다.

## 시험과 실패 판독

-067 단위 정상4경우는0/2/20ns 몇 점의 민감도 시험이다. 연속 범위/실제 핀 지연 승인으로 확대하지 않는다. 각9회 취소 중 읽기4회는 READY 강제 주입이며 전체 정상 적재와 구분한다.
- `bad-write-setup`/`bad-read-setup`은 주소-late2ns, `bad-read-hold`는 출력 해제0ns에서 지정 assertion 실패가 정답이다. `outside126`은 보호125ns보다 큰 주소 지연의 경계 밖 실패다. simulator exit0만 보고 실패 대조를 PASS로 바꾸지 않는다.
- bounded C replay는 load256 bytes와TB96KiB준비 후CHECK256 bytes다. CF query는 TB가 수행한다. 전체80/96KiB SPI 성공도 새 MCU ID 검사도 아니다. fixture의 대기5→7클록은 새SETUP/RELEASE 비용을 반영한 자극 변경이며 전송 C 파형은 바꾸지 않았다.
- source hash는 단위 정상4경우·bounded wave·fit 사이에서 대조한다.067의 기존 단위 driver 실행 중 materializer에 fit CLI만 추가했으며 materialize 함수/두RTL/실행SV는 동일하다. 실제 생성SV와 실행 driver가 원시 근거다. 이후 실행기는 실행 시작 시 source snapshot을 보존한다.
- 정상 첫 단위/fit가 실패한 이력은 없으며 의도한4개 negative case를 보존한다. 새로운 실패가 생기면 raw log와 해당 실행 소스를 새 폴더에 남기고 수정 후 다른 출력 폴더로 재실행한다. 동결 finalizer를 다시 돌리지 않는다.

## 로컬 재개와 운영

이번 로컬 증거는 작업공간의 `probes/nes-diag-memory-067/` 아래다. unit01/fit01/wave01 path 기록과 동결 `evidence/`를 구별한다. 공개 verifier에 `--evidence`로 해당 동결 폴더를 넘긴다. Quartus DB112파일도 동결 evidence/fit/db에 복사하고 inventory로 고정했다. 기존 원본 TEMP fit는 보조 위치다. DB를 이어 쓸 때 별도 작업 폴더로 복사하고 검증한 원본을 수정하지 않는다.061 DB/066 bitstream으로 대체하지 않는다.

Windows 기본 shell 실행은 이번에 sandbox helper 초기화 오류로 시작 전 실패해 승인된 scoped 실행으로 진행했다. Node REPL도 초기화 실패했다. HDL/라이선스 오류가 아니다. 다음 호출에서 도구가 정상이라면 일반 경로를 쓰되 같은 환경 실패를 반복하지 않는다.

Questa는 이미 승인된 Starter FLOAT 한 seat와 기존 `probes/questa-license/probe_float.ps1`를 쓴다. wrapper를 소유한 작업만 종료하며 라이선스 파일/host ID/서버로그는 Git에 넣지 않는다. build/test raw는 private, 공개에는 요약·해시·범위만 넣는다. GBC152/originalNES334 및044–066 동결 manifest를 보존한다.

큰 검증 진전에서 명시적 stage·commit·push·한국어 PR을 만든다. 제목도 한국어, 본문은 작업 목표→작업 내용→작업 결과이며 달성 범위·정확한 부족분·다음 완료 조건을 적는다. merge/제품배포는 자동으로 하지 않는다. 새 PR 링크를 현재 인계에 연결하고 사용자 병합 보고 후 상태를 갱신한다.
