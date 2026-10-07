# NES 다음 작업 인계 — 068 이후

현재 **NES-DIAG-SAFETY-068 / CF68**. PR22 병합 `4d8868f2e324870137606058719fee36a6ff10db`에서 `codex/nes-diagnostic-safety-068`로 진행했다. [068 결과](../../analysis/DIAG-SAFETY-RESULT.ko.md), [계약·재현](../../docs/nes-diag-safety-contract.md), [기계 요약](../../analysis/diag-safety-verification.json)을 먼저 읽고 [067 Sol 인계](../../docs/development/NES-067-SOL-HANDOFF.ko.md)의 보존·운영 지침을 적용한다. 그 문서의 CF67 및 다음 구현 표는 이력이고 이 문서가 현재 상태다. 실제 모델 선택은 사용자가 앱에서 한다.

## 이번 진전과 근거

초기 대기 guard를 memory_reset/MCU_RDY에 연결했다. 첫 에지 이후 1600개의 완전한 간격을 기다려 8MHz에서 200µs, 10MHz에서 160µs다. reset/PLL 상실에서 즉시 준비를 해제하며 대기 중 클록 정지에서는 준비되지 않는다. 전원이 reset 해제 전에 안정됐다는 조건이고 전압 센서는 아니다.

읽기 활성 신호 `reading_active`를 별도 레지스터로 유지한다. 합성된 one-hot ACTIVE→HOLD의 두 상태 비트 OR를 샘플 시점 CE/OE 제어에 쓰지 않는다. SETUP→ACTIVE에서 켜고 HOLD→RELEASE에서 끈다. 실제 글리치 관측이나 전체 아날로그 검증은 아니다. 전체 pin 모델 정상 4경우에서 각 쓰기/읽기 344064 bytes와 취소 36회, setup/hold 변형 3개·126ns 범위 밖 대조를 확인했다. 첫 read-setup 변형은 활성 비트를 켜지 않아 READ_CONTENT에서 실패했으므로 인정하지 않고 올바른 변형으로 새 실행했다.

Guard 정상 2/실패 대조 2, 실제 physical boundary의 대기 우회 실패를 검증했다. 최종 실제060 C bounded wave는 72312응답 비트다. load 256 pin bytes와 TB96KiB 준비 후 CHECK 256 bytes, 181µs 동안 강제 입력의 핀 접근 금지, START 두 장벽, PLL 상실/복구를 확인했다. 전체 C SPI80/96KiB 성공 시험은 아직이다.

새 fit03는 **2400LE / 195LAB / 1479registers / 44M9K / 135physical / 0virtual / PLL1**. 3corner 30내부 summary가 양수이고 최소 hold는 0.140ns다. 최종 DB 복사본의 분석 전 114DB+QSF/QPF/SDC 해시를 고정했다. 3168개의 routed PSRAM 경로, 37 dynamic output, 16DQ input을 추출하고 reader CE/OE source가 reading_active인지 확인했다. 이전 fit02 reader는 이 구조 검사에 실패한다. IO delay0은 FPGA 경로 분석 overlay이고 생산 SDC의 외부 제약이 아니다. PCB 각 leg20ns+추가5ns의 미측정 가정에서 최소 예산62.313ns, leg60ns 대조−17.687ns다.

WRITE 중 8MHz 정지+locked=HIGH에서는 CE가 tCEM8µs 제한을 넘는 반례가 남는다. locked=LOW 뒤 정지 클록에서도 핀 해제·이미지 무효화는 통과한다. 같은 입력에서 유도한 84MHz 카운터를 독립 클록 차단으로 오인하지 않는다. 실제 PLL 감지 시간/독립 차단 근거 없이 clock_halt_safe를 true로 바꾸지 않는다.

## 다음 작업과 완료 조건

1. 외부 예산의 전압/부하·PCB·주파수 및 클록 고장 정책 미확인을 검토한다. PSRAM 외 SPI/SNES와 비동기 lock→핀 해제 경로는 별도다. 실제 전기적 승인은 없다. 회로 변경 시 관련 단위/파형/fit와 식별자를 갱신한다.
2. 새 MCU 후보에서 CF68을 승인하고 CF61/67/44/0을 적재 전에 거부한다. `nes_menu_diagnostic.c`, menu_return materializer, ARM builder의 새 파생 후보로 SD/native 오류·RESET/USB 보호·복귀·실제 ELF callsite를 회귀한다. 동결065/066 파일을 직접 바꾸거나 CF61 쌍과 혼합하지 않는다.
3. `nes_board_session.py`, `nes_board_session_replay.py`, `board_session_tb.sv`의 새 파생 실행기로 최종 후보 전체 C80/96KiB, 모든 byte/tag/응답 비트, 마지막 ACK/FINISH/status/STOP을 검증한다. 새 startup 때문에 TB는 memory_ready 뒤 시작해야 한다.063 trace를 새 회로의 전체 성공으로 계산하지 않는다.
4. 같은 fit/ARM의 Standard ASM·압축 C 모든 byte 복원·marker·manifest를 만든다. 이어 실제 SD 원본/base/menu와 독립 백업/복원 조건을 확인하고, 외부 실기에 패키지→SD TXT·화면 관측·GBC 회귀로 진행한다. 준비 단계/ARM/FPGA 버전을 각각 기록한다. 실제 SD 경로는 아직 확인되지 않았다.

## 파일·동결·재개

`tools/nes_diag_safety.py`가067을 파생하고 startup guard 및 등록형 reader를 추가한다. `nes_diag_startup_checks.py`, `nes_diag_safety_memory_checks.py`, `nes_diag_safety_wave.py`가 단위/핀/C 파형 검사다. `nes_diag_io_extract.py`→`nes_diag_io_paths.tcl`→`nes_diag_io_budget.py`가 FPGA 경로와 예산을 분석한다. 절대 경로 명령은 계약에 있다. Questa 출력은 새 ASCII TEMP 폴더, 기존 Starter FLOAT1seat를 순차 사용한다. license smoke/상속 uncounted 경로를 재시도하지 않는다.

최종 로컬 증거 `probes/nes-diag-safety-068/evidence-final/`: **850파일**, manifest `4d9a5b64465e552558ec26321d76e9c70a4a4cb786f619d06af258f31de474f1`. 초기 `evidence/` 545파일 manifest `1f064615bd1e809188fce1cd201a8c87419e3127920cc936de0db46146f1081d`는 중간 근거로 보존한다. fit01 duplicate snapshot.sv, IO collector QSF 버전행/EOF 기대, read-setup 변형의 잘못된 assertion 및 이전 reader 구조 실패를 보존했다. QSF의 정확한 버전행·report/cache 외 입력 변경은 거부한다. 최종068 및 기존067 verifier가 통과했다. `freeze_nes068.py`, `freeze_nes068_final.py`, 044–067 finalizer를 다시 실행하거나 동결 폴더를 수정하지 않는다.

## 보존·현재 gate

실물 FXPAK Pro Mk.III Rev.D / STM32F401RCT6 / EP4CE15F17C8N / IS66WVE4M16EBLL-70BLI×2 / IS62WV5128EBLL-45HLI는 확인 완료다. 재분해·사진·ID 질문은 없다. 실기는 외부에 있고 PC USB 연결이 어렵다는 사용자 조건을 따른다.044 LINK SCREEN 순환·GBC 정상 보고, 전체 코어059의959LAB/4여유·마지막8프레임은 별도다. GBC152/originalNES334 해시를 보존한다.

준비도는 **5완료/6부분/1미완료**이며 노력·일정 완료율이 아니다. H06 외부 승인 미완료, H08/H09 물리 시간/가시성, H11 새CF68쌍, H12 실제 백업/복원은 남는다. installable=false / newARM=false / fullSPI=false / hardware=false. 불확실 DATA/ACK 재시도 금지, true=안전 메뉴 복귀 가능, base/native SD 실패의 RESET/USB 보호·SD 금지를 유지한다. 주요 진전에서 commit/push/한국어 PR, 본문은 작업 목표→작업 내용→작업 결과다. 사용자 병합 보고 후 PR 상태를 갱신한다.
