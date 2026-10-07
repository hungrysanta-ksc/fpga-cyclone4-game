# NES 다음 작업 인계 — 071 이후

준비 후보 **NES-CF68-PAIR-071**, MCU **NES-CF68-MCU-069**, FPGA **NES-DIAG-SAFETY-068/CF68**, 전체 디지털 세션 **NES-CF68-SESSION-070**이다. PR25 병합 `1245e0dff52c38c5713105138dcf7f9572c6931e`에서 진행했다. [071 결과](../../analysis/CF68-PAIR-RESULT.ko.md), [계약](../../docs/nes-cf68-pair-contract.md), [입력](../../analysis/cf68-pair-inputs.json), [요약](../../analysis/cf68-pair-verification.json)을 먼저 읽는다. 이071 지시가 아래 보존한070의 당시 다음 작업보다 우선한다. 모델/담당 변경으로 검증 수준을 낮추지 않는다.

## 071 완료와 고정 파일

068 동결850파일·DB114·입력21·report10을 대조한 뒤 새 ASCII 폴더에서 Standard25.1std.0 Build1129 ASM/CPF만 실행했다. 모두0오류/0경고, 원본은 동일하다. historical IO inventory는db만 기록했다. 원본incremental17은 별도 관측 목록으로 남기고 조립에서는 제외했다. 삭제하거나131개를 독립 고정된 DB로 쓰지 않는다. 새 RTL/ARM/map/fit/STA/Questa는 없다.

RBF510856바이트 SHA `45dcb3f3908b427b66f3fe52f14e56c80efae58d422af95b322580bd57f0a572`, 압축212523바이트다. 고정069 ARM179336바이트 SHA `268bc38df477516cbcee19f17b192151b79c6e011dc801756d1ad02fc0262499`와 묶었다. manifest 독립 SHA는 `5d5623c53a2a935c95d8648f65a30def715ff71531f90c51f23d46c39a0dfd02`다. `sd2snes/fpga_nl8.bi3`, 표식 `NES VERIFY 069 80.nh1`/`96.nh1`, CF68/protocol59, `/sd2snes/nes-verify-last-069.txt`를 유지한다. 표식을071로 바꾸거나CF61/065/066과 섞지 않는다. timestamp header를 정규화/재빌드하지 않는다.

정확한069 materialized runtime.c/h와 actual fpga.c에 포함된 programmer 본문으로 C510856바이트와 경계66309바이트,13오류 대조를 검증했다. 공개 helper와의 최초 동일성 실패는 LF 및 materialized header의SPI/TIMER/MENU enum3개 차이였다. 정확한 ARM 입력으로 재실행했다. 23사전 점검의 SD는 로컬 모형이다. C DONE은 실물 관측이 아니다. `true`는safe menu reload이며START/불확실한DATAACK재시도/native공유오류 뒤SD/base를 계속 금지한다.

## 071 동결과 재현

`probes/nes-cf68-pair-071/evidence/`374파일, manifest `a70297c41f163eacdf9423e9c93ba8abb5a828aa9bf05e3112eadde7d5848cbd`; audit 통과. 처음DB집합/runtime바이트 오류는 terminal 전사이며 raw 파일이 있었던 것으로 쓰지 않는다. 초기/최종 C 로그·실행 snapshots·원본 manifest와 제외incremental목록을 보존한다. `freeze_nes071.py`/044–071 finalizer를 다시 실행하지 않는다. 원본fit 경로는 로컬068 fit03-path.txt, 새 조립은TEMP `nes071-asm-01`, pair는 동결071의pair/다. 공개 clone에 바이너리/DB/ROM/로그는 없다. 재현 CLI는071 계약에 있다.

## 지금부터의 작업 순서와 완료 조건

1. 실제SD 원본 firmware/base/menu의 크기·SHA·형상·호환성과 독립 backup/readback/restore 수단을 확보한다. 기존 실제 분류 코드를 먼저 읽고 smc_id/sgb_id·plain mapper0/1/carttype0–2/offset/payload≤4MiB/특수 FPGA/SGB/EGBC 없음의 조건을 대조한다. parseableRLE/작은menu만으로 승인하지 않는다. 다음 개발은 원본 파일 검사 또는 **기존 외부 실기 SD→TXT의 읽기 전용 수집**으로 좁힌다. 실제SD를 확보하기 전에 호환성을 코드로 가정하지 않는다.
2. 게임/GBC·세이브의 별도 전체 백업과 변경6파일/복구base/menu의 제한 백업을 구분한다. preflight는 읽기 전용backup/rollback-plan이며 실제 설치/복원 실행기가 아니다. 현재SD/WP/카드/경로를 추정하지 않는다. 실제 복원·전원 손실 회복을 완료 처리하지 않는다.
3. 전압/PCB/비동기SPI/SNES/reset해제 전 전원 안정과 lockedHIGH 쓰기 클록 정지CE>8µs 반례를 검토한다.200µsstartup은voltage sensor가 아니고같은입력PLL은독립차단이 아니다. 임의delay/blanketfalsepath로 승인하지 않는다. 조건을 정리한 뒤 회복 가능한 제한 실기 패키지를 전달한다.
4. 사용자가 외부기기에서 실행해TXT·시간/LED·실제 메뉴화면/재진입/GBC를 각각 관측한다. firmware/FPGA 파일readback·CF68을 함께 확인한다. verified/STOP/base/menu-PREPARED와RAM/UART RETURN_READY_RESET_RELEASED는 화면 증명이 아니다. native/shared SPI/TIM2/SD 오류는RESET/USB를 유지하고추가SD/base를 금지한다. START/불확실한 재시도는 계속 차단한다.

준비도5완료/6부분/1미완료는 작업량 비율이 아니다. H11오프라인쌍은 진전했지만H06외부/H08H09물리/H11설치쌍/H12실제복원은 남는다. installable/hardware/clock_halt_safe=false다. 알려진부품/사진/분해/실기PC직접연결을 다시 요구하지 않는다. 기존044/GBC 기준과GBC152/originalNES334 해시는 유지한다. 주요 진전마다한국어PR 세절과목표달성/미달성/다음완료기준을 남긴다.

## 070 보존 인계와 재사용 한계

# NES 다음 작업 인계 — 070 이후

검증 후보는 **NES-CF68-SESSION-070**, MCU는 **NES-CF68-MCU-069**, FPGA는 **NES-DIAG-SAFETY-068 / CF68**이다. PR24 병합 `8528e15eb5115f16d4f44fb4deed11e3208649a1`에서 `codex/nes-cf68-session-070`으로 진행했다. [070 결과](../../analysis/CF68-SESSION-RESULT.ko.md), [재현 계약](../../docs/nes-cf68-session-contract.md), [기계 요약](../../analysis/cf68-session-verification.json)을 먼저 읽는다. [069 결과](../../analysis/CF68-MCU-RESULT.ko.md)와 [068 계약](../../docs/nes-diag-safety-contract.md), [모델 전환 인계](../../docs/development/NES-067-SOL-HANDOFF.ko.md)의 보호 조건은 유지한다. 이 인계가 과거 문서의 당시 현재/다음보다 우선한다.

## 이번에 확인한 경계

동결069 실제 C 캡처의 전체80/96KiB를 새 실행기로068 물리 top에 재생했다. RAM 사전 적재 없이 실제 WE로180224바이트를 쓰고 읽었으며,901152프레임과50464224응답 비트, 모든 ACK·마지막 ACK·FINISH·STOP·전체 RAM·핀 반환이 통과했다. READY201.0625µs 이후 캡처 원점을 시작하고8MHz SPI/PSRAM은 계속 실행했다. 원래 클록64프레임과 미사용 legacy/H1 영역을 멈춘8192프레임도 통과했다. 응답 비트 오류 대조는 첫 CF 응답 bit8에서 정확히 실패했다. 원시 `%t`는1ps 단위라 `ready_ns` label의 값은1000으로 나눠ns로 읽는다.

생산 SV15개는068 fit03과 같다. 디지털 PLL stub, reset-held H1 입력의 별도 클록 표현, CF68/F0/F1 뒤 미사용84MHz park는 시험 변경이다. 실제 GPIO polling·SD/CPU 지연·interrupt jitter·비동기 위상, 기본 FPGA 재설정과 메뉴 화면은 이번 보드 재생 범위 밖이다.069의95 helper/상위/오류 회귀·ARM 전체 링크와068의2400LE/195LAB/1479regs/44M9K/135핀/PLL1/내부 최소hold0.140ns를 같은 소스 경계에서 재사용한다. 새 ARM/map/fit/STA/ASM은 없다. 전체 NES059의959LAB/4여유/마지막8프레임은 별도 근거다.

## 다음 작업과 완료 기준

1. 066의 `tools/nes_pair_preflight.py`와 관련 ASM·C decoder 도구를 먼저 읽는다. 이 도구는 **061 RBF/065 ARM 해시·CF61·표식065·fpga_nlv**에 고정되어 있으므로 그대로 새 쌍에 호출하지 않는다. 기존 도구를 보존하고068/069용 파생 실행기로 분리한다.
2. **068 최종 fit03**을 새로운 ASCII 폴더에 복사한다. 원본 DB114파일, QSF/QPF/SDC와15개 SV의 해시를 검증한 뒤 Standard25.1 ASM/CPF만 실행한다. 원본 DB·동결 파일을 수정하지 않는다. Lite의 기존 실패나 새 fit를 이유 없이 반복하지 않는다.
3. 066 수정 encoder의 규칙으로 RBF 길이와 모든 바이트를 대조하고 실제 C programmer 복원을 검증한다. EOF padding·65535 경계·DONE 오류 대조를 유지한다. MCU는 고정069 ARM179336바이트 SHA `268bc38df477516cbcee19f17b192151b79c6e011dc801756d1ad02fc0262499`다. 표식06980/96·`fpga_nl8.bi3`·expectedCF68·로그069를 같은 쌍 manifest로 묶는다.065/066 CF61 쌍과 섞거나 timestamp header를 임의 정규화하지 않는다.
4. 실제 SD의 원본/base/menu 형상·카드/WP·시간/LED·독립 백업/복원을 확보한다. 모형의 복원 계획을 실제 복원으로 기록하지 않는다. START와 불확실한 DATA/ACK 재시도는 금지한다. native/shared peripheral 오류 뒤 RESET/USB를 유지하고 추가 SD/base 접근을 하지 않는069 보호를 보존한다.
5. 외부 전압/PCB/비동기 SPI/SNES, reset 해제 전 전원 안정, lockedHIGH 쓰기 클록 정지의 한계를 함께 검토한다. 전기 보증을 가정으로 닫거나 blanket false-path·같은 입력의 PLL을 독립 차단으로 취급하지 않는다. 회복 가능한 제한 패키지를 사용자가 외부 기기에서 실행하고 TXT·화면·메뉴 재진입·GBC 관측을 전달하는 방식으로 진행한다.

## 동결 근거와 실패 기록

`probes/nes-cf68-session-070/evidence/`의 **297파일**, manifest `8e03dbc0ef18b5ab9d2ba63bfde8612325b6bd9f5d32f35900b887ebe21fc00a`. `verify_nes_cf68_session.py --evidence <absolute>`는 private archive를 요구한다. 정상baseline64-02/parked8192-01/두full-01과mutation-response-01의 실행 snapshot, 입력 trace/fixture, raw 로그를 보존했다. 최초baseline64-01은 복사한 testbench의 top이 옛 이름이라 최적화에 실패했다. 제품/라이선스 실패가 아니며 모듈명·preflight 수정 뒤 통과했다.

`freeze_nes070.py`와044–070 동결을 재실행하거나 수정하지 않는다.067/068/069의 필요한 private 입력도 유지한다. FLOAT 한 좌석으로 순차 실행했고 정상 종료했다. 상속 uncounted license, 반복 smoke, 전역 서비스/환경 변경을 금지한다.

## 실물·진척·게시

FXPAK Pro Mk.III Rev.D / STM32F401RCT6 / EP4CE15F17C8N / IS66WVE4M16EBLL-70BLI×2 / IS62WV5128EBLL-45HLI는 실물 확인 완료다. 부품명·사진·분해·PC USB를 다시 요구하지 않는다. 실기는 외부에 있으며 패키지→사용자 SD 실행→TXT/영상으로 진행한다.044 화면 순환/GBC 정상 보고와 GBC152/originalNES334 보호 해시를 유지한다.

준비도 **5완료/6부분/1미완료**는 작업량 비율이 아니다. H10은 최신 CF68 전체 디지털 근거로 갱신했다. H06 외부 승인, H08/H09 물리 가시성·시간, H11 새 ASM/ARM 쌍, H12 실제 SD 백업/복원은 남는다. installable/hardware/clock_halt_safe=false다. 주요 진전마다 commit/push/한국어 PR의 세 절을 작성하고 사용자 merge 보고 후 상태를 확인한다. 모델·담당 변경으로 검증 수준을 낮추지 않고 실제 모델 변경을 도구로 주장하지 않는다.
