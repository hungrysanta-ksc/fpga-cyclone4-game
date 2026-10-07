# NES 현재 인계 — 079 저장 전 단계 표시

079에서 단계2–8의 문구 쓰기·전 바이트 비교/500ms 화면 기회/RESET 재유지와 실제 보고서 저장을 연결했다. 통합185·실제 타이머5·인과대조3·ARM 호출 검사 통과. SDREPORT079는 compile-only이며 부팅/file_init·가독성·복원 패키지는 남는다. P1 부분/준비도4완료7부분1미완료 유지.

[079 결과](../../analysis/REPORT-CHECKPOINT079-RESULT.ko.md)와 [P1–P6 계획](../../docs/development/NES-077-PROCESS-REVIEW.ko.md)을 먼저 읽는다. PR27은2026-10-07T16:13:56Z 병합됐고 master `249f37fbe02942f6109df3d785d797142030f959`에서 새079 가지를 시작했다. 과거 본문의 PR27open 표기는 당시 이력이다.

## 완료와 한계

- 전용 `SDREPORT079`, `/HW079nnn.TXT`,3072바이트 저장 시험 payload. 기존 입력4개 재수집 없음. 결과 파일만으로 성공 판단 금지.
- 실제074 writer/전체077 FatFS/native185검사와 actual077 timer5,보호 제거3인과 실패. 최종 ARM132104바이트 SHA `f80be9ac447edcc18d98354fc249286859b5971080baecd67a92e50b31813657`,main→run→writer→checkpoint7회 호출 확인. ARM 실행/물리화면 결과가 아니다.
- RESET LOW·USB IRQ off·SD offload0·블록 전송 없음·active/report권한이 선행조건. shared fault 뒤SD/SRAM 금지,첫오류 보존. 표시7×500ms도 기존1000tick/10000poll에 포함. budget재개방 금지.
- mini는RESET 해제마다 PPU/font/WRAM 초기화 후24행 DMA를 반복한다. SRAM비교는화면ACK가 아니며500ms는미검증 표시기회. 초기boot/file_init,최종legacy bootprint와물리가독성은다음범위다.
-077 native8개/mini는해시동일,068 RTL·071쌍·044/GBC 불변. 새Questa/Quartus/ASM없음. CF68전체코어/4LAB자원조건과분리한다.

## 다음 작업 순서

1. 전용079의 준비 화면 이전 boot/file_init/mini 종료·소유권을 점검하고 최종 화면까지 실제 플랫폼 이벤트 시험을 연결한다. 실패가 화면 전인지 저장 중인지 구별할 관측방법과 시간상한/예산 밖 범위를 명시한다.
2. 기존 정상044 복원 자료와 묶어 보고서전용P3 적격성을 판단한다. 준비되면 외부실기1회로 화면단계·TXT·정상복원/GBC를 받는다. 원인 사전확정을 요구하는 순환차단은 금지. 아직079 설치패키지는 없다.
3. CF68은 별도P2 외부IO/클록조건과 같은쌍P3 후 실기. 이후P5 정상속도/영상/자원가능성,P6 게임통합 순서 유지.

## 보존·재현·실수 예방

-079 raw: `probes/nes-report-checkpoints079/evidence/`, metadata는 `analysis/report-checkpoint079-verification.json`, 검사기는 `tools/verify_nes_report079.py`. 최종normal-06/변이-06/ARM-03. 초기 준비·타이머 추출/링크·ARM 헤더/긴VERSION·Make 실패 로그 보존. 완료한 finalizer 재실행/044–079 동결편집 금지.
- 빌더는 새079 파일만 사용한다.074빌더SHA `765a808cd9263789f1d98ab3f250e02b59c9b5a1b3e1eeb0f74b6514042d0dde` 불변. VERSION은 기존40자 시스템정보 출력 한도를 고려해 짧게 한다. 함수추출은 호출/선언이 아닌 정의에서 시작하고 ELF출력CRLF를 정규화한다.
- 정상044와HW002 TXT성공 펌웨어 역할을 구분한다. 같은입력·LED·분해·PC USB·부품명 재요청 금지. 사진확인Rev.D/STM32F401RCT6/EP4CE15F17C8N/EBLL-70BLI×2를 사용한다.
- 한국어 PR의 작업 목표/작업 내용/작업 결과, 검증범위·미달성·다음 종료조건을 유지한다. 병합 후 상태 재확인, 큰진전 단위 커밋, 자동병합 금지.

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
