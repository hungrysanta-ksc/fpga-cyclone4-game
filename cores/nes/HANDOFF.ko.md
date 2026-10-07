# NES 현재 인계 — 081 SD 초기화·FatFS mount

081은 보고서 전용 SD 초기화의 유한 대기·응답 검사와 실제 FatFS mount 상태 연결을 구현했다. GPIO 초기화/mount8558검사·인과대조2·최종ARM 호출 통과. 전체 초기화→native 저장→최종 화면의 단일 실행·외부 관측·복원 패키지는 남는다. SDREPORT081은 compile-only이며 P1 부분/준비도4완료7부분1미완료다.

[081 결과](../../analysis/REPORT-INIT081-RESULT.ko.md), [P1–P6 계획](../../docs/development/NES-077-PROCESS-REVIEW.ko.md)을 먼저 읽는다. 현재 가지는 `codex/nes-report-init-081`이다.

## Git 병합 상태

PR28은 master `1efd312dbb07339bdda2d300f838343a98991e67`로 병합됐다. PR29도 병합됐지만 대상은 이전079 브랜치여서 master에는080이 없었다. 원래080 head `85a656a80f80d455abad5dcf2317d303a6b0c175`를 그대로 master로 제출한 [PR30](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/30)을 만들었다. 081은 이080 head 위에서 시작한다. 이번 후속 PR도 master를 대상으로 하며 PR30 먼저 병합하면080 중복 차이가 자동으로 줄어든다. 이전079 브랜치로 병합하지 않는다. 사용자 병합 보고 뒤에는 merged 상태뿐 아니라 master 도달 여부를 확인한다.

## 완료와 보존

- 느린 SD 클록의 실제 bounded 타이머 반환 뒤 shared fault/소유권 재검사, R1/R2/R3/R6/R7 검사, 누적ACMD41 200tick/2048회, 응답1000클록/CMD7 busy100tick/250000회 제한. 전체60초/1000000poll 예산도 공유한다. 정상17명령/7990타이머 반주기다.
- CMD8 정상응답 SDv2 SDSC/SDHC·SDXC 범위. 구형무응답을 정상으로 추정하거나 응답 버퍼를 재사용하지 않는다. CSD/CID/RCA/용량은 전체 성공 후 게시한다.
- sdnative 원본 전체 prefix와 active077 초기화 거부 불변. 보고서만 strong `disk_initialize`→`sdn_report_mounted081`로 검증된 상태를 전달한다. 재초기화/오류 reset 없음. 실제 FatFS 새 mount가 이 함수를 요구한다는 점을 놓치지 않는다.
- 최종normal-06:8558검사,응답/추가클록 보호 제거2대조. 실제 FatFS mount지만 sector VBR은 모형이다. ARM02 132320바이트 SHA `5931eec90956022104b8aa42851525b52b3f3a805d50a48ca71c33357357649d`, main→init→mount→080boot→writer→079checkpoint7 연결 확인. 실제MCU/새RTL/Questa/fit/ASM 없음.
- 079 actual writer/native185·timer5와080boot881는 동일 소스 범위에서 재사용. 새081 전체 실행으로 합산 금지. 초기wrap시험 설정 오류/헤더·COFF링크 실패/ARM01 mount연결 누락/Make 최초 실패를 보존했다. obj-report079 출력명은 빌더 재사용 때문이며 실제ID081이다.
- 동결081 metadata `analysis/report-init081-verification.json`, `tools/verify_nes_report081.py`. 완료한 freeze/update 스크립트 재실행과044–081 archive편집 금지. 정상044/GBC와기존NES334 그대로다.

## 다음 작업의 정확한 종료 조건

1. 081 실제 초기화/상태연결과 실제FatFS/native CMD17/24 writer,080mini/최종문구를 **하나의 플랫폼 사건 시험**으로 연결한다. 상태 전달·첫mount·최종close/readback·fault후 추가IO금지를 같은 세션에서 확인한다. 이번 mount VBR 모형은 저장 경로 검증이 아니다.
2. main의 전원/클록/타이머/USB/CIC 시작 전제와 bounded runtime을 구분한다. 사전UART배너/file_init는 후보에서 제거했지만 모든 main 초기 설정이 bounded라는 증거는 없다. 초기화/mini 실패는 아직 검은 화면일 수 있다. 보호를 풀어 화면을 강행하지 말고 외부에서 구별 가능한 관측 계약을 완성한다.
3. 정상044 복원 자료/해시/설치·복원표와 관측표가 준비되면 보고서 전용P3를 판단한다. CF68 P2를 무조건 기다리거나 물리 원인 사전확정을 요구하지 않는다. CF68 진단은 별도P2+같은쌍P3가 필요하다.
4. 같은파일·LED·분해·PCUSB·부품 질문 금지. 실기는 외부에 있으며 새패키지→사용자실행→TXT/영상 방식이다. 정상044와HW002 TXT성공 펌웨어는 구분한다. 공유 첫오류/쓰기권한 회수/RESET/USB 보호,1000tick 저장예산과7×500ms는 유지한다.

## 재현과 인계 주의

`tools/nes_report081_prepare.py --evidence080 <고정080/evidence> --out <새후보/source>` → 기존 `tools/build_nes_report079_arm.ps1` → `tools/check_nes_report081_arm.py`를 사용한다. `tools/test_nes_report_init081.py`의 normal/no-crc/post-fault-clock은 각각 새 폴더에서 실행한다. 개인 frozen 입력 없이 공개 clone만으로 재현된다고 주장하지 않는다. 현재 사용자에게 설치할 파일은 없다.

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
