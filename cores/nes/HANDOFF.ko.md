# NES 현재 인계 — 083 첫 화면·저장 관측 패키지

083은 SD 접근 전에 mini와1A초기화/1Bmount 표식을 표시한다. 실제 전체경로679·1초타이머5·인과대조4·최종ARM 순서 검증을 통과했고, 첫 관측 ZIP/정상044복원/대응소스를 준비했다. 실기 가독성·새TXT·복원 후 메뉴/GBC는 사용자 관측 대기다. CF68/NES 설치 승인이 아니며 준비도4완료7부분1미완료를 유지한다.

[083 결과](../../analysis/REPORT-OBSERVATION083-RESULT.ko.md), [실행/복원 안내](../../docs/SDREPORT083-RUN.ko.md)를 먼저 읽는다. PR33은 master `413c4fd11a395e661a6d894fed1c283d4fdc2ecb`에 병합됐고 원래 head 도달을 확인했다. 현재 `codex/nes-report-observation-083`이며 새 PR은 master 대상이다. 자동 병합하지 않는다.

## 완료와 보존

- 실제083 순서는 내장mini/boot→STEP1A(1초)→081초기화→STEP1B(1초)→첫native mount→writer 단계2–8(각0.5초)→terminal이다. 새 표식은 write permission/예산을 재시작하지 않는다. 표식 후 RESET 재유지, 첫fault 이후 추가IO 금지, USB 제외를 보존한다.
- actual native/FatFS/전체 writer679검사, 실제1초 timer5, 비교·RESET·최초표식 제거4대조 통과. 소스 SRAM문구/렌더링 기회는 TV 픽셀/가독성 증거가 아니다. 새ARM 실제 호출 순서와 기존15입력SHA 불변을 확인했다. main power/clock/CIC startup은 시험 범위 밖이다.
- SDREPORT083132552바이트 SHA `60d5ffcf283bdd1a69a62d8baac3f4f1dfad06c2562888c55e0491968663d91b`. TRIAL ZIP은 test와restore 각각firmware.stm, 안내/manifest/LICENSE만 포함. SOURCE ZIP은 대응 준비소스와 생성헤더/빌드 도구를 포함한다. 기본 FPGA/메뉴/게임/세이브는 교체하지 않는다.
- 정상044 복원169056바이트 SHA `1c3b40a3459d24114cb4d91ee9d861d1a08025a670ef25317ef489092203693b`는 사용자가 준 마지막 정상파일이다. HW002성공125260바이트 파일은 별도이며 복원에 쓰지 않는다. 없는firmware.before-sdinfo072.stm을 요구하지 않는다. 전체SD백업은 사용자 수행 항목이다.
- 최종normal03/negative4종03/ARM01/package02,2119파일 manifest `4b60051cd38f38cb9ef48ed20cbe918aed1c8e265bda58df1c6ebca58e0723df`. 초기 no-early-marker02의 더 이른 GPIO assertion/수집기 기대 불일치, package01 Make .ARG_VERSION 차이, Make 최초 의존성 실패/재시도를 보존했다. 완료 freeze/update 재실행과044–083archive편집 금지. 기존082 verifier 통과.

## 다음 입력과 작업

1. 사용자083 실행을 기다린다. 전원 직전부터TV영상, 새HW083nnn.TXT(0바이트 포함) 또는 없음, 정상044복원 후 메뉴/GBC 결과가 입력이다. LED/분해/PCUSB/기존파일/확인한 부품 질문을 반복하지 않는다. 사용자 현장 실행 대신 로컬 성공을 실기로 기록하지 않는다.
2. `tools/check_sdreport083.py <TXT>`는 기대3072바이트 전부와 비교한다. 파일 일치만으로 최종close/terminal/복원 성공을 주장하지 않는다. 마지막표식은 다음작업의 예고다. 코드7은 healthy IO의 내용 불일치일 수 있으며 shared fault와 구분한다.
3. 표식 없음은 적용/startup/mini/표시 범위,1A만 관측은 초기화 범위,1B는 초기화 성공 후mount/후속 범위다. 표시 뒤RESET held로 화면이 꺼질 수 있어 전체영상을 본다.1초/0.5초 실제가독성은 아직 미확인이다.90초는 사용자의 관측 종료 기준이지 startup watchdog 보장이 아니다.
4. 보고서전용 오프라인P3준비만 끝났다. 실제복원과P1실기관측은 대기. CF68 P2/동일쌍P3,전체NES4LAB/P5/P6는 별도다. 결과가 오면 해당실패경계만 수정/검증하고 큰 진전에서 한국어3구역PR을 만든다.

## 재현

`nes_report083_prepare.py --evidence081 <고정입력> --out <새source>` → 기존build_nes_report079_arm.ps1 → check_nes_report083_arm.py. obj-report079 출력명은 재사용이며 VERSION은083이다. test_nes_report_observation083.py는 normal/4negative를 각각 새폴더에서 실행한다. verify_nes_report083.py는동결증거/ZIP전체를검사한다. 개인고정입력 없이공개clone만으로재현된다고 주장하지 않는다.

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
