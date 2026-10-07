# NES 현재 인계 — 075 오프라인 조사

이번075는 받은 파일을 실제 C에 실행한 조사다. **메뉴 carttype55/SRTC가 기존 메뉴 복귀의 carttype>2 조건에 거부됨을 재현했다. 제품 펌웨어 수정과 0바이트 TXT 해결은 아직 아니다.** [075 결과](../../analysis/OFFLINE075-RESULT.ko.md)와 [검증 메타](../../analysis/offline075-verification.json)를 먼저 읽는다. PR27은 이번 시작 시open/미병합이며 같은 PR을 갱신한다.

## 확보한 입력과 재요청 금지

- firmware.stm은 사용자 마지막 정상044, 169056바이트/SHA1c3b40a3459d24114cb4d91ee9d861d1a08025a670ef25317ef489092203693b. 기존 manifest 일치/STM3 CRC 통과. 현재074 파일로 해석하지 않는다.
- firmware.stm.bak-hwTest는 HW002 TXT 쓰기 성공 진단,125260바이트/SHA6599441e92cfe5cdffe07e0bb9240452bf76b672b1203504a02f849ba3219da6. 로컬HWINFO002-C44 빌드 전체바이트 일치. 일반 메뉴 복원 기준과 구분한다.
- 실제 m3nu.bin/fpga_base.bi3도 받았다. 전체 SHA/역할/결과는075 표를 따른다. firmware.before-sdinfo072.stm은 없다. 추가 펌웨어를 다시 요구하거나 현재 진단을 원본으로 이름만 바꾸지 않는다.
- 074는0바이트·검은 화면이고 LED가 밖에서 보이지 않는다. 재시험·LED 영상·분해·PC USB 요청 금지. 확인된 보드/부품도 다시 묻지 않는다. 새 물리 패키지는 이번에 만들지 않았다.

## 이번에 새로 확인한 범위

실제 메뉴 분류/현재 거부 식3검사, 호스트 전용 방어 실험15, 실제 C command→DATA 첫 시작 GPIO 에지32조합, 고정069 C 베이스 복원214981바이트/오류13대조를 통과했다. CMD24 응답 끝→시작2클록이며 여유8 추가 시10클록이다. 단순8클록 누락을 저장 실패의 확정 원인으로 삼지 않는다. DATA 본문/CRC 응답/busy/전압/시간은 이 에지 시험 범위 밖이다. 메뉴 거부는 메뉴를 호출하지 않는073/074 TXT 문제와 별개다.

비공개 증거 `probes/nes-offline-075/evidence/`: 91파일, manifest `b1f089f563727faca3b2327e0fd3c85f4d70126c3eeced18f6761bb54ff17708`. `tools/verify_nes_offline075.py`로 검사한다. 최초 fallthrough -Werror 실패와 수정 후 원본 경고를 보존했다. finalizer 재실행/동결 증거 편집 금지. 공개 도구만으로 사용자 입력을 재생성할 수 있다고 주장하지 않는다. 기존044–074도 보존한다.

## 다음 작업 순서

1. 확인된 SRTC 메뉴의 제한적 승인 정책과 실제 분류 읽기 오류를 신규 변경으로 구현·검증한다. carttype 제한 단순 삭제 금지. 현재 호스트 guarded 변형은 실험일 뿐 제품에 적용되지 않았다.
2. SD DATA CRC 상태 샘플·busy와 보고서/할당 예산을 실제 하위 코드로 비교하고 인과 대조를 만든다. HW002 legacy CMD25 성공은 bounded 보호 제거의 근거가 아니다. native 공유 오류 뒤 RESET/USB 유지·추가SD/SPI/base 금지·불확실 쓰기 재시도 금지를 유지한다.
3. 실제 보이는 결과와 로컬 근거가 생긴 뒤 새 실기 패키지로 비어 있지 않은 TXT·원본 복원·메뉴/GBC를 확인한다. 아직 요청할 재시험은 없다. 071 쌍 설치 불가, H06/물리 가시성/독립 복원/외부 조건과 준비도5완료6부분1미완료 유지.

제품 RTL/ARM/FPGA 쌍은 그대로다. 새 ARM/Questa/Quartus는 실행하지 않았다. 고정071/069/068,044/GBC 실기 기준은 아래 역사적 기록을 참고한다. 과거 '파일 미수신'·'LED 영상 요청'은 현재 지시가 아니다.

---

아래는074 전달 당시의 역사적 기록이며 위075가 우선한다.

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
