# MMC480 실기 실패 분석·481 시작 진단

**사용자가 넣은 mmc480.nes는 정확한 대상 ROM이다. 적재·readback·START는 통과했고, SNES 표시 프로그램의 시작을 5초 기다린 뒤 실패했다. STOP·base 복구와 실제 메뉴 복귀는 정상이다.** 검정 화면의 근본 원인은 아직 확정되지 않았다. [실기 원문 해시·분석](../analysis/mmc481-hardware480.json) · [481 후보 검증](../analysis/mmc481-verification.json).

## 실기에서 확인한 사실

| 경계 | 결과 |
|---|---|
| ROM | 393232B, CRC32 `5a04eed7`, SHA256 `dbb1cb5e18b091ca9101b1c2f5a5d6bdbeaa4a30ae1a504251310f6765cabb49` |
| profile / 적재 | ID79 일치, 393216B 전체 적재·비교, verify_error0, verified/end_accepted1 |
| START / NES | start_sent1, observer3224→14208348, ROM 오류0 |
| SNES 시작 | boot_reason5 TIMEOUT, 44381poll, 500tick=5초; 처음/마지막 stage0·flags0 |
| 수신·계획·표시 | native_frames0, 비용 계측 진입 전 종료. 0값은 비용0이나 게임0fps 측정값이 아님 |
| 종료 | STOP 오류0, base_restored1, safe_to_reload1, 사용자가 검정 화면 뒤 정상 메뉴 복귀 확인 |

진행 로그는 DISPLAY_NEXT232730ms→DISPLAY_STOPPED237740ms→STOP_DONE237770ms→MENU_PREPARED241030ms다. 이번 실패는 게임 장면의 처리량 병목을 측정한 결과가 아니다. NES core가 실행됐다는 observer와 SNES 표시 CPU의 실행 증명도 구분한다.

## 모델의 빈틈과 추가 검사

480 공동 시험에서 실제65816 코드·DMA·CRC/coverage·최종ACK/STOP·57344픽셀 일치는 여전히 그 범위의 유효한 근거다. 그러나 Mesen은 로컬 SFC를 부팅했고 native console setup은 모델이었다. **실물 FPGA의 카트리지 ROM 핀을 통해 SNES가 부팅하는 경계는 증명하지 못했다.** 기존 시험의 부팅 ROM 한 바이트 task도 공동 실행에서 호출되지 않았다.

이번에 별도로 확인했다.

- 실제 C/FatFS 프로그래머로 **전달한480 BI3**를 풀어 RBF와 전체 byte 동일함을 확인했다. GPIO/DONE은 모델이므로 실제 재설정 성공의 별도 증명은 아니다.
- 실제 FIT의4096B MIF를 주소순으로 복원해 sink-program.hex 및 SFC의 코드·header/vector 매핑과 일치함을 확인했다.
- 실제480 보드 RTL에서 reset vector부터 초기화 영역·header/vector·미배치FF를 포함한 **4100회 SNES 핀 읽기**, address 위상 변화·버스 해제·status flags7·수동 milestone·STOP을 검사했다. 실제65816 실행이나 배선/전기 지연 시험은 아니다.

이 검사로 ROM 선택 오류·오프라인 압축 복원 오류·선택된 초기화 데이터 불일치는 배제했지만, 실물에서 읽기 신호/주소/출력과 reset 인계가 어떻게 보였는지는 아직 구분할 수 없다. flags0만으로 특정 핀이 고장났다고 단정하지 않는다.

## 481 후보와 전달 보류

프로필7a/상태 protocol3으로 구별되는 읽기 전용 진단 후보를 구현했다. 기존 낮은3bit 사건 표식은 유지하고 높은5bit에 RD·ROMSEL·WR·active·내부 drive의 SPI73 순간값을 싣는다. ARM이 이를 누적한다. **순간값을 못 본 것은 짧은 펄스가 없었다는 증명이 아니다.** 기존500tick timeout·START 순서·reset/STOP·독립 검사·최종ACK·base 복구를 우회하지 않는다. 계획 파일명은 mmc481.nes와 nes-*-mmc481.txt이며 동일 ROM을 쓴다.

ARM parser256종 flags·구버전/잘못된 ID/전송 실패 거부·누적과 전체 RTL4100read/응답/STOP은 통과했다. ARM text202313/data10040/BSS18552B, 파일212356B·Flash636B 잔여다. 객체 변경은 h1·verify의 ID/상태 파서와 menu/checkpoint의 이름 네 개다. 수신·계획·CRC/receipt 실행기를 교체한 것으로 계산하지 않는다.

| 후보 | 구현/전체 Lite FIT | 관련 setup / hold | 판정 |
|---|---|---|---|
| 01 | FPGA 사건 latch,15274LE | −0.034 / +0.138ns | 보류 |
| 02 | 동일 RTL, 해당 loader 경로 예산5.3ns 강화,15260LE | 다른 경로 −0.491 / +0.125ns | 기각, 강화 제약 미채택 |
| 03 | 별도 사건 latch 제거·기존 snapshot/ARM 누적,15264LE·14074comb·8392FF·256608bits | −0.228 / +0.168ns | **전달 보류** |

03은 원래479 SDC·클록·seed1을 그대로 사용했다. 세 배치 모두 보존했으며 seed 탐색·타이밍 예외 완화·부팅 대기 연장으로 통과를 만들지 않았다. 기존479의 관련 setup+0.235ns와 달리 새 진단 후보는 준비 조건에 미달한다. **481 ZIP은 만들거나 사용자에게 전달하지 않았다.** 이 후보들의 타이밍 실패를 실제480의 검정 화면 원인으로 소급하지 않는다.

## 후속482

481 기각 결과는 그대로 보존한다. 오류코드의 commands_blocked 선택을 계산 뒤로 옮긴482가 모든 이전 코드/동시 명령/STOP 전수 일치와 관련 setup/hold+0.133/+0.132ns를 통과해 [482 제한 진단 전달본](nes-mmc482-trial.ko.md)을 준비했다. 실제480 검정 화면의 원인을 확정하거나 부팅 복구/FPS 이득을 주장한 것은 아니다.

## 다음 순서

1. 실패 원문과 ROM 해시를 고정한다.480은 재설치/재시험 권고 대상에서 제외하고 성공 실기 기준476을 보존한다.
2. 482의 준비 조건 통과를 확인하고 해당 설치 안내를 따른다.481 기각 산출물은 전달하지 않는다.
3. 준비 조건을 통과한 새 번호/marker/로그·원복 ZIP만 전달한다. 사용자 설치 후 시작/메뉴 복귀와 신호 기록을 비교한다. 보드·SD의 PC 연결은 요구하지 않는다.
4. 실제 게임 표시가 시작된 뒤 수신·계획·표시 비용과 연속 FPS 최적화를 재개한다. 현재 성능 성공 기준은 제한 NROM476 약24fps이며 게임60fps는 미달성이다.

## 재현과 보존

공개 저장소에는 도구·메타데이터만 둔다. 원문3TXT는 `probes/nes-mmc481/hardware480-01`, 후보는 candidate01..03, 실행 원문/소스는 executed 아래에 보존한다. ROM/hex·SFC·도구·빌드 DB·라이선스는 Git 미포함이다. [재현 범위](../cores/nes/REPRODUCING.ko.md)의 로컬 입력을 복구해야 실제 빌드/시뮬레이션이 가능하다.

`analyze_nes_mmc481_failure.py`는 --logs/--rom/--out으로 실기를 재분석한다. `prepare_nes_mmc481.py`는 --board/--arm/--out으로03을 재생성한다. `test_nes_mmc481_bootbus.py --live <480 보존 소스> --board <03 board> --out <새 경로>`는 전체 재컴파일 모드이며 FLOAT wrapper 안에서 실행한다. `test_nes_mmc481_status.py --arm <481 src> --out <새 경로>`는 실제 parser를 검사한다. 분석기의 --programmer480에는 전달480의 실제 C 복원 검사 디렉터리를 지정한다. 분석기는 source/객체/MIF/FIT/STA를 묶어 `diagnostic_trial_ready`를 판정하며 이번 값은 false다.
