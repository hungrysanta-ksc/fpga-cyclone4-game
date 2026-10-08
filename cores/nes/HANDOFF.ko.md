# NES 현재 인계 — CF87 메모리 비활성 클록 관측

087은 메모리 접근 없이 RESET-held 기준 클록을 관측할 별도 CF87 회로다. 20MHz 기본800만 주기1경우와3주파수 축소 구간·고장 대조3개, 새 fit/내부STA/배선 감사를 통과했다. 10제어핀 비활성·32데이터핀 출력 차단을 배선 결과에서도 확인했다. 실제 MCU GPIO/TXT 통합·ARM/ASM·실기 패키지는 다음 작업이며 CF86 자체와084 성공 결과는 유지한다.

[087 결과](../../analysis/CLOCK-OBSERVATION087-RESULT.ko.md)와 [응답 계약·다음 완료 조건](../../docs/nes-clock-observation087-contract.ko.md)을 먼저 읽는다. PR37은2026-10-08T02:56:06Z 병합됐고 master `4017a50d716474df76e43e2698feb685fbb6f8c1`에서 시작했다. 현재 `codex/nes-clock-observation-087`. 사용자만 병합한다.

## 바로 다음 작업

1. **실제 bounded MCU GPIO reader와 수집 session**을 만든다. CF87/C0 snapshot 원시16byte의ID/window/divisor/예약/flags/sequence 진행을 검증하고 MCU 자체시간·전체poll예산을 둔다. READY=1은 서비스표식, valid=1은 구간완료일 뿐이다. live0·마지막gap1·진행없음·부분응답을 성공으로 처리하지 않는다. 응답CRC는 아직 없으므로 actualC↔RTL을 연결해 검증한다. 구형 코어MCU가CF87을 승인하게 바꾸지 않는다.
2. RESET-held 관측→RAM 보관→검증된mini 복귀→084 기반TXT/화면까지 ONE session. CF87은 화면/메모리가 없으므로 값을 확정한 후mini로 바꾼다. 최초fault 뒤 불확실SD/SRAM IO금지,RESET/USB 소유권 보존. 기존 정상 저장시험만 다시 요청하지 않는다.
3. freshCF87fit의ASM/압축 + 해당ARM +044복원 쌍/manifest를 만든다. SPI IO/구성 전환/RESET 소유권 확인 후 외부실기용report-only trial을 전달한다. 사용자TXT/영상으로 기준 클록 가용성을 판별한다. LED/분해/PCUSB/기존파일/부품 재질문 금지.
4. CF87은 관측전용이다. CF86 reset/guard·외부PSRAM/비동기clear/공통고장·최신코어MCU/전체80-96KiB는 별도 미완료다. 관측기의 상시메모리비활성을 CF86의activewrite차단 승인으로 대체하지 않는다.

## 고정 근거와 실패 기록

- fit01 동일생산RTL2개:337LE/27LAB/247regs/메모리0/PLL0/135핀.18내부summary 최소0.187ns,예외1개/실제inter-clock6행. mapped10제어HIGH/fitted32데이터disabled. 외부SPI3입력4경로/1출력2경로미제약. 새ARM/ASM/실기/패키지없음.
- normal02 **20MHz 기본800만 주기 case0만PASS**1250000회. 다음22MHzcase1은1ps stimulus 양자화 기대 오류1375017vs1375000으로 실패했다. 전체run성공아님. short04의80000주기3경우12500/13750/13424 + 부재완료/재개구간PASS; short03은추가구간검사전PASS. production동일,TB parameter override만 다름.
- 3대조same-clock02/live-snapshot01/memory-enable01 PASS(expectedfailure). same-clock01은 부재검사가 예상했던주파수검사보다일찍 올바르게 실패한 수집기기대오류,normal01compile문법/timeout경고도 보존. Questa 라이선스오류없고모든job/18000listener종료.
- base90files 중88은18bytefixture,2는actual수신/075사본. source-binary동일성미확인. 재질문대신자체관측경로선택. FE명령을CF87에가정하지않는다.
- 동결458files manifest `2b13e7bf14b1ed1e0d5c4230f6ee9ed8600fb73f1ed82aa96b73a748ba604d76`. verifier087 사용; finalize_clock087.py 완료재실행금지/044–086archive수정금지.084실기저장/화면/044restore/menu/GBC PASS; 준비도4/7/1.

---

## 이전086 인계 기록

# NES 현재 인계 — CF86 reset 경계·새 배치 검증

086은 실제 CF85 배치에서 발견한 raw 감시 신호의 영역 간 직접 연결을 수정했다. CF86 동일 생산 입력16개로 새 fit/STA·CDC 감사와4 GPIO/128정지/130360응답 비트·보호 제거4개를 통과했다. 제약된 내부39 summary 최소0.158ns, 새 PSRAM3168경로의 가정상 최소64.565ns다. 외부 IO·비동기 clear 지연·실제 기준 클록/공통 고장·최신 MCU 쌍/전체 세션·실기는 미완료이며 설치 파일은 없다. 084 저장/화면/정상044복원·메뉴/GBC 성공은 유지한다.

[086 결과](../../analysis/CLOCK086-RESULT.ko.md), [086 계약](../../docs/nes-clock086-contract.ko.md), [메타데이터](../../analysis/clock086-verification.json)를 우선한다. PR36은2026-10-08T02:26:05Z 병합됐다. master `2995577f37280dbe23398ba39d5238b867f20366`에서 시작한 `codex/nes-clock-timing-086`이며 자동 병합하지 않는다.

## 다음 작업 순서와 완료 조건

1. 보유한 base의 FE 지원·측정창과 binary-source provenance부터 확인한다. 보존 MK3 source는8MHz×12=96MHz,96000000계수+1publish주기, 최초FFFFFFFF다. 사용자 binary 대응 및 RESET-held 가용성은 아직 입증하지 못했다. 대응 불가면 PSRAM 접근을 시작하지 않는 자체 READY/클록 관측 경로를 검토한다. 성공한084 저장·복원 시험이나 부품/LED/분해/PCUSB 수집은 반복하지 않는다.
2. CF86의 실제 비동기 clear→Q/핀/PCB/전압·부하 상한과 기준 클록 연속성·공통 원인 고장 정책을 닫는다. 이번39 summary는3개 CDC 예외가 적용된 내부 수치다. 외부 input54/744·output49/1391은 미제약이고64.565ns는 미측정 PCB 가정이다. 양클록 정지9µs 반례/MTBF 미확인을 숨기지 않는다.
3. 이후 최신 MCU의 ID86/READY/최종 로그·전체80/96KiB 실제 C/SD/SPI/STOP/복구를 같은 후보로 검증한다. 그 뒤 같은 fit의 ASM/압축/ARM/base/menu/정상044 복원 쌍(P3)과 외부 TXT/영상(P4)이다. CF68/071 쌍에 CF86만 섞지 않는다. 전체NES 자원4LAB/P5/P6는 별도다.

## 재현·보존

- finalfit03과wave01의 생산 입력16개 동일. 39내부summary 최소0.158ns, 실제CDC36행/예외3개,128정지/130360응답 비트/인과4개 통과. CHECK96KiB 준비는 TB 핀 쓰기이고 C CHECK는256byte다. 전체 C 적재라고 확대하지 않는다.
- 원래 CF85 fit01−5.354ns/일반 제어 FF crossing은 실제 배선 반례다. 수정 후 예외 없는fit02−2.561ns와 최종fit03, 첫 감사 API 오류/한글 경로 helper 오류를 보존한다. 정상/음성 로그의CLOCK085 marker는 기존 시험 task 재사용이며 실제 query86을 검사한다.
- evidence 1793파일 manifest `f210693b8ecb48392adc4ae535282c9e5252f9b3e833a4d3b24839192a388d54`. `finalize_clock086.py` 완료 재실행 금지/044–085 archive 수정 금지. verifier086은 public source와 private 동결 입력을 함께 요구한다. 모든 FLOAT job 종료/18000 listener 없음 확인; 새 license smoke 불필요.
- 내부 fit 통과를 외부/실기 승인으로 확대하지 않는다. 새ARM/ASM/전체길이SPI/하드웨어/설치 없음. 084 physical 및044복원/menu/GBC PASS 유지. 현재 준비도4/7/1.

---

## 이전085 인계 기록

# NES 현재 인계 — CF85 단일 클록 정지 차단

085는 별도 입력 클록을 이용한 단일 클록 정지 차단을 실제 진단 핀 셸에 연결했다. 디지털 GPIO4경우/정지128경우/인과 대조3개를 통과했으며 검출 최대4.374µs, CE LOW 최대3.350µs다. 두 클록 동시 정지 반례는 남는다. 새 fit/STA·실제 기준 클록 가용성·최신 MCU 쌍/전체 세션·실기는 미완료이며 설치 파일은 없다. 084 저장/화면/정상044복원·메뉴/GBC 성공은 유지한다.

[085 결과](../../analysis/CLOCK-GUARD085-RESULT.ko.md)와 [구현·재현·다음 승인 조건](../../docs/nes-clock-guard085-contract.ko.md)을 먼저 읽는다. PR35는 2026-10-08T01:54:37Z 병합됐고 master `bf29565e94fd9d63a57b013764dc4f612c710986`가 기존084 head를 포함한다. 현재 브랜치는 `codex/nes-clock-guard-085`다. 자동 병합하지 않는다.

## 보존할 근거

- 정상044/menu/GBC와084 사용자 TXT3072바이트 전체 일치·최종 성공 화면·수동044복원 성공은 완료다. 같은 파일/LED/부품/분해/PCUSB 질문을 반복하지 않는다.
- 실험RTL CF85 / 과거 승인 범위의RTL CF68 / 전체 디지털 세션070(069 C) / 파일 쌍071(069 MCU) / 최신 코어MCU077 / 보고서 전용084를 구별한다. 084를 NES 펌웨어로 교체하거나071에 CF85를 섞지 않는다. CF85 새 ID85는 구형 MCU의 승인 대상이 아니다.
- normal02 4 GPIO 실행·128정지·130360응답 비트/negative3. reference20/약21.477/22MHz, CLKIN8MHz. 두 클록 동시 정지 반례와 아날로그/CDC/배선 미검증을 보존한다. 모형 abort 뒤 데이터는 무효이며 SRAM·RUN 차단을 유지한다.
- 새 evidence 471파일 manifest `aec4aabee2f45eeaf1bec3cb353d8501c629369513482e471477a4ccf6f320d0`. normal01/02와 대조 로그·실행 snapshot 보존. `finalize_clock085.py` 완료 재실행 금지,044–084 archive 수정 금지. 최종 결과는 [메타데이터](../../analysis/clock-guard085-verification.json)와 verifier를 사용한다.

## 다음 작업

1. 기존 `get_snes_sysclk()` 명령FE·96000000주기 측정창이 실제 base에서 지원되는지, RESET-held에도 SNES_SYSCLK가 유지되는지 먼저 대조한다. 이번에는 실기 측정하지 않았다. 공통 HSE 기반 MCU/PLL 카운터로 독립성을 대신하지 않는다.
2. CF85의 새 fit/STA/CDC·A9 클록 라우팅·비동기 assert/reset release·외부 IO를 검사한다. 과거068 slack/PSRAM3168경로를 새 top에 재사용하지 않는다. 양쪽 클록 동시 정지의 처리 또는 제한 근거가 없으면 P2 설치 보류.
3. 최신 MCU 승인/READY·최종 로그·전체80/96KiB 실제 C↔RTL·STOP/복구를 같은 후보에 연결하고, 해당 fit의 ASM/압축/ARM/base/menu/정상044 복원 쌍(P3)을 만든다. 이어 외부 실기 TXT/영상 회수(P4). 전체NES 자원4LAB/P5/P6는 별도다.

---

## 이전084 인계 기록

# NES 현재 인계 — 084 실기 저장·재읽기 통과

084 실기 저장·재읽기·화면 관측을 통과했다. 사용자 HW084001.TXT3072바이트가 기대값과 전체 일치하고, 영상의 같은 파일명·TXT SAVED + READBACK OK·Save code:0을 확인했다. 검토 화면에서 글자 잘림도 없다. 사용자가 정상044복원 후 메뉴·GBC도 모두 정상이라고 확인했다. 083 실제 원인 확정·반복 내구성·NES/CF68 전체 검증으로 확대하지 않는다. 준비도4완료7부분1미완료를 유지한다.

[084 실기 결과](../../analysis/REPORT084-HARDWARE-RESULT.ko.md), [실행/복원](../../docs/SDREPORT084-RUN.ko.md), [메타데이터](../../analysis/report-space084-verification.json)를 먼저 읽는다. [PR34](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/34)는 작업 중 병합됐고 master `5ad37abe1de6935f16200028d5f59c95b7831b79`에서 기존084 head 도달을 확인했다. 현재 `codex/nes-report084-hardware-result`에서 문서만 바꾼 후속 실기 기록을 별도 PR로 게시한다. 자동 병합하지 않는다.

## 완료·보존

- 사용자083은1A/1B/2/3까지표시했지만STEP3고정/TXT0바이트/좌우잘림이다.0바이트는사용자보고이며원본TXT수신없음. 영상8초STEP2,10/40/49초STEP3샘플확인. 이번084시험후정상044복원/메뉴/GBC는사용자정상확인.
- 083실제코드+조밀한FAT모형에서stage3/fault16/1directorywrite/0bytes를재현했다. 사용자실제원인확정아님. 084는1C읽기전용공간탐색후RAM할당힌트만설정한다.60초/100만poll과writer10초/10000poll보존. 연속공간eligibility이며root확장은별도:fullroot+조밀FAT는stage2/write0제한실패를명시적으로검증했다.
- 화면공통최대26문자/좌우3공백/33번째NUL;복원안내단축.809통합/실제timer5/causal5/ARM01통과. native/ff/timer등13입력동일,수정5소스host/ARM동일. 이번보고서저장·재읽기·화면은실기통과이며전체NES실기성공으로확대하지않는다.
- ARM132880 SHA `b2895696ab5c665b2b9a0a4acf3997f0ca13442b40e6f1ebf4abc3513036db1e`. TRIAL+정상044+SOURCE를별도로컬ZIP으로전달한다. 정상044169056 SHA `1c3b40a3459d24114cb4d91ee9d861d1a08025a670ef25317ef489092203693b`. HW002용firmware와구분한다. SD에자동복사하지않았다.
- 동결2537파일 manifest `1a43873e74e8a5cc888d099874d9ff17caa6959b4b12ffdd53a9d0987100a3d5`. finalnormal05/negative05/ARM01/package01. normal02의mount이전힌트기대오류,negative03의row기대메시지오류,Make초기dependency실패/재시도,video60초범위오류보존. freeze_feedback084.py/update_feedback084_docs.py완료재실행금지;044–084archive수정금지. occupied-repro/result.json은역사083복사본이므로별도provenance084.json을따른다.

## 다음 작업과 완료 조건

1. 사용자HW084001.TXT3072바이트전체일치와영상최종성공/같은파일명/코드0확인을완료했다. 이번정상044복원·메뉴/GBC도사용자정상확인을받았다. 저장성공판정을다시보류하거나같은입력을반복요구하지않는다.
2. 향후다른실패가발생할때만:1C면읽기오류/예산/연속빈공간여부,2면directory/name/확장,3면첫payload할당/쓰기경계를조사한다. 모형재현을실제카드원인으로단정하거나writer예산을무작정늘리지않는다. 공유fault뒤IO금지와불확실쓰기재시도금지를지킨다.
3. 현장firmware→영상/TXT회수방식유지. LED·분해·PCUSB·기존파일·부품질문반복금지. 이번보고서저장/복원은완료됐으므로별도CF68외부조건P2/동일쌍P3/적재검증P4진입조건을점검한다. 전체NES4LAB/P5/P6는미완료다.

재현:084prepare→기존build079wrapper→084ARM검사. obj-report079는역사출력명이다. verify084와이전083verifier를사용한다. 공개clone에없는고정개인입력필요성을명시한다.

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
