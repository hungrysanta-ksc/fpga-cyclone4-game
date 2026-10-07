# NES 현재 인계 — 078 보고서 전체 저장 세션

계획P1의 실제074 보고서→전체077 FatFS/native CMD17/CMD24/CRC/busy GPIO 모형 연결을 완료했다. [078 결과](../../analysis/REPORT-SESSION078-RESULT.ko.md)와 [관측 계약 초안](../../docs/nes-report-observation078-contract.ko.md)을 먼저 읽는다. **P1은 부분 달성: 관측 구현·부팅/총시간·최종ARM/패키지는 남는다.** 사용자0바이트의 실기 원인은 미확정이다.

## 이번 근거

-116검사: FAT16/FAT32 보고서2879바이트, 각각20명령(읽기10/쓰기10), 모든 R1/쓰기end/읽기CRC 위치, cold remount 전체비교,6길이/SDSC·SDHC/이름충돌/불연속할당/시간·poll한도. end검사/내용비교 제거2대조는 정확한 assertion 실패.
-생산077 MCU·068 RTL 불변.074 보고서와077 lower 경로를 결합한 호스트 구성이며 새ARM/Questa/Quartus/실기/설치쌍 없음. 카드/GPIO/tick/ARM CRC primitive는 모형이다. 읽기 응답-데이터 중첩 전체 위상과 부팅은 미검증.
-078 frozen267파일,manifest `9532cd2e82acae40baacee35053bd29bd94e6a73f2a7de324d82729c4bc9dac6`. run-01 정의추출/헤더 실패,run-02 미사용메뉴 링크실패,중간82/108검사 보존. 최종run-05/대조-02. verifier078을 사용하고 finalizer078/기존044–077을 재실행·편집하지 않는다.

## 다음 작업

1. P1 잔여: 보고서 전용 후보에서 실행 전 단계 화면→RESET 유지 SD 작업→정상 때 다음 표식 순서를 구현하기 전에 mini 실제 화면 갱신/RESET 재시작과 SPI/SD 소유권을 확인한다. 오류 이후 guard 해제·화면/SD 재시도는 금지한다. 화면 방식은 설계 초안이며 가시성이 증명되지 않았다.
2. 기존1000tick/10000poll 보고서 예산에 표시 대기를 몰래 더하지 않는다. 표시/SD/전체 예산, 부팅/file_init의 예산 밖 경계, timeout 초과 마지막 호출을 구분한다. 실제 플랫폼 이벤트·실패 주입·최종ARM 호출을 연결한 뒤 패키지를 판단한다.
3. [P1–P6 계획](../../docs/development/NES-077-PROCESS-REVIEW.ko.md)을 따른다. 보고서 전용은 기존 경로/관측/복원 조건 충족 시CF68 P2를 기다리지 않는다. CF68 메모리 실기는P2/같은 쌍P3 필요. 준비도4완료/7부분/1미완료 유지.
4. 반복074/LED영상/분해/PC USB/같은입력 재요청 금지. 정상044와HW002 TXT성공 펌웨어 역할을 구분한다.071 조립은 완료됐지만 설치보류,077은compile-only이며 임의 혼합 금지. 현재PR27open 조회, 같은PR에 계획검토+078 반영 후 다음 차례 상태를 재확인한다.

## 입력과 보존

정상044와TXT성공HWINFO002는별도역할이며파일4개는이미보존했다.없는before-sdinfo072를현재진단으로대체하지않는다. 확인된Rev.D/STM32F401RCT6/EP4CE15F17C8N/EBLL-70BLI×2 재질문금지. [075 결과](../../analysis/OFFLINE075-RESULT.ko.md)·[076 결과](../../analysis/MENU076-RESULT.ko.md)를참조한다.

077 증거 probes/nes-sd-response077/evidence/:1424파일,manifest `8b4b5a9385dd7ced9a46b725d9e3a71f6877734b07febe3f0ec560f30842720c`. verifier077로검사하고finalizer재실행/동결044–077편집금지. 최초DWORD중복과ELF checker의direct-call가정실패를보존했다(후자는stderr전사임). 이번시작PR27open/미병합,같은PR갱신;다음차례재확인.한국어PR3절/큰진전커밋규칙유지.

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
