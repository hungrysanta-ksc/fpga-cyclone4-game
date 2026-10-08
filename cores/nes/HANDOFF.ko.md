# NES 현재 인계 — 082 초기화부터 저장·최종문구까지 단일 실행

082에서 실제081 초기화→첫 mount→080mini→FatFS/native CMD17/24 저장·재읽기→최종문구를 단일 호스트 실행으로 연결했다. 667검사·인과대조2 통과, 생산 소스/081 ARM은 불변이다. 외부 관측·시간/결과표·044복원은 남으며 설치 불가, P1 부분/준비도4완료7부분1미완료다.

[082 결과](../../analysis/REPORT-SESSION082-RESULT.ko.md), [공정 계획](../../docs/development/NES-077-PROCESS-REVIEW.ko.md), [관측 계약](../../docs/nes-report-observation078-contract.ko.md)을 먼저 읽는다. 현재 가지는 `codex/nes-report-session-082`다. PR32 병합 master `648d399865e6746397037ecb3bbb4e6f5c9c51fc`에서 시작했으며 PR31은 닫힌 대체 이전 기록이다. 다음 PR은 master 대상이고 자동 병합하지 않는다.

## 완료와 보존

- 실제 final081 init→strong disk_initialize 상태 전달→file_init/FatFS 첫 CMD17→boot/mini→writer의 create/write/sync/close/open/readback/close→terminal을 한 번의 세션으로 실행했다. 단계 사이의 재초기화/오류 reset 없이 FAT16/32×SDSC/SDHC 네 조합 통과. 3072바이트를 실제 writer와 카드 FAT 체인 독립 검사로 확인했다.
- 정상 native 명령은 FAT16 read11/write10, FAT32 read12/write10. SRAM587접근·7×500ms·최종문구 확인. 모든43 응답 위치/587 SRAM 위치 고장, 화면 변조/타이머/누적예산/wrap/초기화/카드/논리 code7을 포함해667검사다. 정상CRC 내용변조는 code7 실패문구, 공유 오류는 추가IO 없이 RESET/USB 보호 종료다.
- 원래081 생산 소스 불변, 기존 ARM132320바이트 SHA `5931eec90956022104b8aa42851525b52b3f3a805d50a48ca71c33357357649d` 재사용. 새 펌웨어082/ARM빌드/실행/RTL/Questa/fit/ASM/실기는 없다. 실제 MCU startup과 TV 표시, 전기 타이밍은 검증 밖이다.
- 최종normal-04/두negative-04. 새302파일 manifest `14023cb52e2239380743a891a2795d73e32bccab8657ce343d8b8df1f2692112`. 최초 file_status 헤더 오류와 code7에 대한 잘못된 시험 기대를 보존했다. 기존081 verifier도 통과. 044–082 동결 archive 및 완료한 freeze/update 스크립트는 재실행/편집하지 않는다.
- 재현은 tools/test_nes_report_session082.py와 개인 고정081 증거가 필요하다. tools/verify_nes_report082.py는082/081 증거와 공개 소스 해시를 검사한다. 개별079/080/081 검사를667개에 합산하지 않는다.

## 다음 작업의 종료 조건

1. 초기화/mini 실패까지 케이스 밖에서 구별할 관측 흐름과 시간·결과표를 완성한다. 현재는 SD 초기화가 mini보다 먼저이므로 초기 고장은 검은 화면이다. mini 준비·초기 표식을 SD 앞에 놓을 수 있는지 실제 소유권/시작 전제를 검토한다. 순서 변경 시 해당 생산 소스와 최종 ARM을 다시 검증한다. fault 이후 공유IO로 실패화면을 강행하지 않는다.
2. 500ms는 렌더링 기회이며 읽기ACK가 아니다. 총60초/1백만poll, 저장1000tick/10000poll와7×500ms 예산을 유지하고 실제벽시계·startup 한계와 구분한다. 최초오류, RESET/USB, 파일쓰기 권한 회수, 불확실한 DATA/ACK 재시도 금지를 보존한다.
3. 정상044/HW002성공 펌웨어의 역할을 구분한 기존 자료로 설치/복원 파일·해시·순서표를 준비한다. 관측 계약과 함께 보고서전용P3 통과 여부를 판단한다. 현재 설치 파일은 없다. 사용자0바이트 원인을 미리 확정할 필요는 없지만 동일한 비구별 패키지는 보내지 않는다.
4. CF68는 별도P2/동일쌍P3, 전체NES4LAB/P5/P6도 별도다. 기존GBC152/원본NES334 및074–081 source pin은 유지한다. 같은파일/LED/분해/PCUSB/확인한 부품 질문 금지. 실기는 외부이고 패키지→사용자실행→TXT/영상 회수다.

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
