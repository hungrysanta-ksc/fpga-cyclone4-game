# NES 현재 인계 — 080 mini·부트 ROM·최종 화면

080은 embedded mini·부트 ROM 준비와 최종 문구를 bounded/전량 비교 경로로 연결했다. 플랫폼881검사·인과대조2·ARM 호출이 통과했으나 SD 초기화 전 구간과 실제 가독성은 미완료다. SDREPORT080은 compile-only, P1 부분·준비도4완료/7부분/1미완료를 유지한다.

[080 결과](../../analysis/REPORT-PLATFORM080-RESULT.ko.md)와 [P1–P6 계획](../../docs/development/NES-077-PROCESS-REVIEW.ko.md)을 먼저 읽는다. 사용자는 GitHub 장애로 PR28을 병합하지 못했으나 후속 작업을 명시적으로 승인했다.079 head `53a36abb83e0d51de6a645c41eb15e4e0fc3a99c` 위의 `codex/nes-report-platform-080`이 현재 브랜치다. PR28 → 080 순서로 병합하며 후속 PR의 base는 우선079 브랜치다.079 병합 뒤 master로 전환한다.

## 완료한 경계

- mini153544/boot65535바이트를 실제 legacy decoder와 전 바이트 비교했다. 기존 caller가 마지막FF를 버리는 출력까지 보존한다. 고정 mini·boot 입력과 nativeSD/FatFS/타이머/메모리/SPI/079checkpoint10파일은 동일하다.
- INITB/DONE/PROGB 대기와 RLE 입출력을 제한했다. 부트 ROM256바이트 단위 전량 재읽기,24줄 clear/비교, 준비·최종 문구의 UART 없는 readback을 연결했다. 공유 오류 이후 화면/SD 재시도와 active/fault 상태 재진입을 거부한다.
- 플랫폼881검사/인과2와 ARM132160바이트 SHA `79f97dd91001954ab753222d839dd7a9f2f5949b60e2a79ff661c7b21be56e2a` 호출 검사 통과. 새 모형의 report writer는 stub이다. 실제 전체 FatFS/native 근거185/timer5/인과3은079에서 동일 소스로 재사용하며 새 실행으로 세지 않는다.
- 최초smc.h 누락·기존fpga_get_done 미선언·Make 의존성 실패와 초기855검사를 보존했다. 최종normal-03/negative-03/ARM-02. 빌더079 재사용으로 obj-report079 폴더지만 ID는SDREPORT080이다. 설치용이 아니다.

## 다음 작업 — 실제 SD 초기화와 전체 연결

1. `main → file_init → f_mount → sdn_initialize`는 아직080 이전에 실행된다. ACMD41 무한 루프, 느린 명령의 타이머/UART 종료·응답 검증을 별도 report-only 경로에 연결한다. active077은 초기화를 거부하므로 단순 활성화·guard 삭제·오류 reset으로 우회하지 않는다.
2. 카드 초기화→mini 준비→실제 writer/native→재읽기→최종 화면의 단일 플랫폼 사건 시험을 만든다. 이번881의 GPIO/SRAM/시간/USB/보고서 저장은 모형이므로 native 전체 결합으로 확대 해석하지 않는다.
3. 초기화·mini·저장 실패를 구별할 화면/시간 경계와 정상044 복원 절차가 준비되면 보고서 전용P3/외부실기를 판단한다. SRAM 비교나500ms 실행 기회는 실제 화면 소비 ACK가 아니다. 미확정 물리 원인을 사전 확정하라는 순환 조건은 금지한다.
4. CF68은 별도P2 전기/클록과 같은쌍P3 필요. 이후P5 정상속도/영상/자원과P6 게임통합 순서 유지.044/GBC·전체NES959LAB/4여유·071쌍과 분리한다.

## 보존과 공개

- private `probes/nes-report-platform080/evidence/`, metadata `analysis/report-platform080-verification.json`, verifier `tools/verify_nes_report080.py`. 완료한 finalizer 재실행/044–080 동결편집 금지.079 증거5052파일/manifest81c3ff5b7af8911c27d0429ca25a6670b11f0dfd90dc0e6027b7b0ce17a95b13 그대로다.
- 같은 입력4개·LED·분해·PC USB·부품명 재요청 금지. 정상044와HW002 TXT성공 펌웨어는 별개다. 기존1000tick/10000poll 저장 예산에7×500ms가 포함되며 화면 표시마다 재개방하지 않는다.
- 한국어PR 작업 목표/작업 내용/작업 결과와 달성/미달성/다음 종료조건을 유지한다. 순차 병합은 사용자에게 맡기며 GitHub가 불가해도 검증된 로컬 커밋과 선행 관계를 보존한다.

---

아래는074 당시 역사적 기록이며 위077·075/076 결과가 우선한다.

# NES 다음 작업 인계 — 074 이후

현재 전달본은 **SDINFO074-BASE069 LED 오류 관측용 수집기**다. 사용자는073의 HW004000.TXT0바이트와 검은 화면을 보고했다. 정확한 원인은 미확정이며074를 저장 수정 성공으로 표시하지 않는다. [074 결과](../../analysis/SD-FAULT074-RESULT.ko.md), [실행 안내](../../docs/SDINFO074-RUN.ko.md), [검증 메타데이터](../../analysis/sd-fault074-verification.json)를 읽는다. PR27은 이번 시작 시open/미병합이며 같은PR로 업데이트한다.

## 다음 진행과 구분

- 사용자는 외부 실기에서 실행한다. 다음 입력은 새HW005nnn.TXT/파일크기와 카트리지 Ready·Read·Write LED60초 영상이다. LED가 보이는지 비동기 질문을 보냈으며 답이 없다면 보인다고 단정하지 않는다. 분해/PC USB/이미 확인한 부품 질문은 금지한다.
- 074는 단일 firmware133332바이트 SHA `031725700f3e9c58abc1001f9d53cdbe89a1587e5e552a77951434d136953271`. 원본 독립 백업과 firmware.before-sdinfo072.stm은 그대로 유지한다. 현재 진단 펌웨어로 원본 백업을 덮지 않는다.
- 새 stage는1수집/2생성/3쓰기/4sync/5닫기/6재열기/7재읽기/8닫기/9화면. 첫 오류에서 원자적 단일 word의 오류·단계를 고정하고 MCU LED로 표시한다. 안내 표를 참조한다. 최종 BLOCKED에서만 잡으면 이미 단계가 달라질 수 있어 mutation으로 금지했다.
- SD/FatFS/runtime11입력은073과 동일하다.074는 UART 없는 관측 플랫폼·호출 전 RAM 표식·ID만 바꾼다. RESET/USB/쓰기권한 회수/native fault 뒤 추가IO 금지/재시도 금지를 유지한다. SysTick 정지/CPU lockup에서도 깜빡인다고 주장하지 않는다.
- 원인 확정 전 CMD24 gap/CRC 샘플/busy/예산을 무작정 바꾸지 않는다. 실제 SD command/data/CRC는073·074 통합에서도 모형이다. 코드 조사가 관측을 대체하지 않는다. LED 오류와 단계로 가설을 좁히고 actual lower-call 실패를 재현한 뒤 수정한다.

## 증거·재현·보존

공개 prepare074는 pinned069→기존 prepare073→별도074변환이다. 실제 materialized source의 collector52/writer23/platform6/report29·runtimeLED162·늦은 capture mutation1·FatFS40·ARM actual callsites 통과. LED 표시의 실물 관측은 아직 없음. 별도 sourceZIP은 실제 빌드입력과 mini 대응소스를 포함한다. NES쌍/RTL/fit/Questa는 새로 실행하지 않았다.

`probes/nes-sd-fault-074/evidence/`1519파일 manifest `2be1006b6365414d2246e1dc38655126e3f2b00405871422f1f7a9626d37165b`. 동결 이후 audit의 objdump 경로 encoding/helper 위치 오류를 공개 verifier에서만 수정했다. sibling `audit-addendum/write_report.txt`는 같은 frozen ELF의 보충이며 공개meta SHA로 고정한다. final audit/073 audit 통과. freeze/finalizer 재실행이나044–074 증거 편집 금지. 과거ZIP verifier는 초기판이고 현재 공개 verifier와 addendum을 사용한다. 초기 Make dependency 실패/후속 통과 보존.

다음 완료 조건: 사용자 LED로 소프트웨어 최초 오류·단계를 확정→해당 실제하위 경로 수정/인과대조→비어있지 않은 새TXT framing/CRC/전체검사→원본 복원/메뉴/GBC 확인. 이후 actual menu 분류와 외부전기/clock/backup gates를 해결한다. 파일 이름/0바이트/모형 통과를 실기 성공으로 보고하지 않는다.

## 고정071/069/068 기준

071 RBF510856 SHA `45dcb3f3908b427b66f3fe52f14e56c80efae58d422af95b322580bd57f0a572`, packed212523,069 ARM179336 SHA `268bc38df477516cbcee19f17b192151b79c6e011dc801756d1ad02fc0262499`. fpga_nl8.bi3,표식 NES VERIFY 069 80.nh1/96.nh1,로그 `/sd2snes/nes-verify-last-069.txt`를 같은 쌍으로 유지한다.065/066/072 firmware와 섞거나 timestamp header를 정규화하지 않는다. 071manifest `a70297c41f163eacdf9423e9c93ba8abb5a828aa9bf05e3112eadde7d5848cbd`,374파일 audit 재통과. [071 결과](../../analysis/CF68-PAIR-RESULT.ko.md)/[계약](../../docs/nes-cf68-pair-contract.md)에 원본db114/관측incremental17 제외·ASM/CPF·C복원510856+66309·오류13·로컬preflight23가 있다.

070180224bytes/901152frames/50464224응답bit/ACK/FINISH/STOP은 디지털 보드 세션이며 actual MCU/SD/화면 proof가 아니다. [070 결과](../../analysis/CF68-SESSION-RESULT.ko.md)를 따른다.068최종 fit03 2400LE/195LAB/1479regs/44M9K/135핀/PLL1/최소hold0.140ns와069 ARM·95helper 회귀를 현재 source 경계에서 유지한다. 전체NES059의959LAB/4여유/마지막8프레임은 별도 근거다. START/불확실DATAACKretry/native 공유오류 뒤SD/base 금지,RESET/USB 보호를 보존한다.

## 알려진 실기·준비도·게시

FXPAK Pro Mk.III Rev.D / STM32F401RCT6 / EP4CE15F17C8N / PSRAM IS66WVE4M16EBLL-70BLI×2 / SRAM IS62WV5128EBLL-45HLI는 실물 확인 완료다. 부품/사진/분해/PC 직접연결을 다시 요청하지 않는다. 외부기기 패키지→사용자실행→TXT/영상으로 진행한다.044 LINK SCREEN1→2→3→1·자동종료 없음·GBC 정상 플레이와 GBC152/originalNES334 해시를 유지한다.

준비도5완료/6부분/1미완료는 작업량 비율이 아니다. H06외부/H08H09실물가시성·시간/H11설치/H12실제복원은 남고071 installable/hardware/clock_halt_safe=false다. 주요 진전마다 명시적stage/commit/한국어PR 세절과 목표달성/미달성/다음완료기준을 남긴다. Questa는 기존 Starter FLOAT wrapper로 실제 필요 job만 실행한다. 이번072는 새 Questa/Quartus를 실행하지 않았다. 실제 모델 변경은 도구로 주장하지 않는다.
