# NES 현재 인계 — 클록 관측 trial091 / 첫 게임 SMB3

091는090의 실제 STM32 설정 함수·매크로를 레지스터 모델에 연결해 구성/관측/mini 복귀94검사와 전환 누락 대조3개를 통과했다. 생산 펌웨어는090 그대로이며 정상044 복원본을 포함한 클록 관측 trial/source ZIP을 완성했다. 다음은 사용자 HW090 TXT/화면 회수다. SMB3(J), mapper4·PRG256KiB/CHR128KiB를 첫 게임 목표로 등록했다.

[091 결과](../../analysis/CLOCK-TRIAL091-RESULT.ko.md), [실행 안내](../../docs/CLOCKREPORT090-RUN.ko.md), [게임 계획](../../docs/development/NES-GAME-COMPATIBILITY.ko.md)을 먼저 읽는다. PR41 merged2026-10-08T04:56:52Z/master `3f83e0f104160d0347810a0226264bd0527f3a9b`에서 시작했고 현재 `codex/nes-clock-transition-091`. 사용자만 병합한다.

## 다음 행동

1. 클록 관측 trial은 `probes/nes-clock-transition091/package-01/FXPAK-CLOCKREPORT090-TRIAL.zip`, 소스는 같은 폴더의SOURCE.zip이다. 시험196248/SHA `00f757fcd1ca0da08ce0e5564358e06b482071e6119d8827e6c81748fcfddebe`와 정상044169056/SHA `1c3b40a3459d24114cb4d91ee9d861d1a08025a670ef25317ef489092203693b`. 파일/화면 번호090을 유지했다. 내용 변경 없이 재빌드/재배포하지 않는다. 사용자가 새HW090 TXT와 영상/마지막화면을 주면 실제 파일명·길이·raw/decoded·최종저장화면을 분석한다. 파일미생성/빈화면도 별도기록하고 관측 전 클록있음으로 확정하지 않는다.
2. 세팅은test/sd2snes/firmware.stm만 복사, 자동진단,90초 종료 기준, 전원OFF후restore 정상044. 정상084 저장/복원/menu/GBC는 과거PASS이므로 반복 시험 질문을 하지 않는다. 새문제가있으면 그 변화만 받는다. 부품/LED/분해/PCUSB/없는백업파일 재요청 금지.
3. 이후 CF86 외부/async/commoncause/최신MCU/전체SPI를 별도 진행한다. 현재 넓은준비도4/7/1, **report_trial_ready=true / nes_installable=false**. 새 실기 클록 근거가 필요한 단계는 TXT회수 전 완료로 바꾸지 않는다.
4. 사용자 첫 게임은 **Super Mario Bros 3 (J).nes**, mapper4,PRG256KiB/CHR128KiB/전체393232, SHA `dbb1cb5e18b091ca9101b1c2f5a5d6bdbeaa4a30ae1a504251310f6765cabb49`다. 로컬원본은Downloads/test에 있고 Git/ZIP에 넣지 않는다. `first-game-target.json`과게임계획을 확인한다. 제목→월드맵→1-1플레이를 첫 실기 구간으로 계획하고 전체호환완료와 구분한다. 현재80/96KiB제한은384KiB지원이 아니다. 이후 mapper확장 시 SMB3/GBC회귀 유지.

## 검증·보존

pins04 actual GPIOhelpers/macros +registermodel94, causal02 AF/SPI복원/DATA0입력누락3검출.6543555상승/하강각 pernormal session, 기존090호출예산과TXT값 동일. 원본SPIbits/CMSISpos와speedH2를 고정했다. 모델은MMIO/BSRR/status/time/card/SRAM이며 SRAM SPItransaction끝CSHIGH는모델계약; 전기파형/bit-levelSRAM새재생 아님. 초기include순서compile실패와pins02/03 speed3상수모델,최종04speed2교정/01및02대조를 보존한다. 기존11hostsame/13native입력/firmware바이트 보존, 새ARM/RTLfit/ASM/Questa없음.

동결717파일 manifest `1ef0c061a1a38dbbec210ad5ee8b4e1f54a7c7ed936b22f53ccaf5f131913040`. verifier091사용. 완료finalizer재실행/044–091archive변경금지. userROM원본변경없음;NESdev direct403/searchprimary참조,헤더값만으로dump리비전/battery하드웨어확정금지.

---

## 이전090 기록

# NES 현재 인계 — 클록 TXT 통합090

090는 단일 제품 함수의 CF87 구성·클록 관측·mini 복귀·실제 SD 초기화/FatFS·TXT 저장/재읽기·최종 화면을 연결했다. 통합94검사·인과 대조4개, TXT16파일 대조와4변조 거부, 전체 ARM196248바이트 링크/호출 검증을 통과했다. 실제 SPI 핀 전환 점검과044 복원 포함 패키지 검증은 남아 있어 실기 배포 전이다.

[090 결과](../../analysis/CLOCK-REPORT090-RESULT.ko.md), [090 계약](../../docs/nes-clock-report090-contract.ko.md)을 먼저 읽는다. PR40은2026-10-08T04:34:51Z 병합, master `6077d65b26ac53b6fc5f029aa1e7fb332d519b9d`에서 시작했다. 현재 `codex/nes-clock-report-090`. 사용자만 병합한다.

## 바로 다음 작업과 완료 기준

1. 090의 전체 세션94·ARM 링크는 완료했다. 반복 구현/라이선스 smoke/기존 저장 실기 재질문을 하지 않는다. 현재 GPIO 응답 모델이 실제 MODER/CR1 핀 전환을 전부 검증하지 않으므로 CF87 관측 종료→mini 재구성의 실제 매크로·CS/SPI idle·RESET 연속성을 점검하고 필요한 fault 대조만 추가한다.
2. firmware196248/SHA `00f757fcd1ca0da08ce0e5564358e06b482071e6119d8827e6c81748fcfddebe`, 기존089 RLE59700/SHA `e772ead5e070c71767df2318d91f5d83d629e8ffedd275b19e81c842133cb4a2`와084 exact mini/정상044 복원 파일로 새로운 report-only trial/source 패키지와 manifest를 검증한다. old044–090 동결 파일은 바꾸지 않는다. 부팅 화면·관측 중 RESET·SD 단계·실패시 복원과 TXT 수거 절차를 구체화한다. 아직 설치 패키지를 전달하지 않았다.
3. 새 실기에서 TXT/화면을 받아 RESET-held reference availability를 판정한다. ACTIVE는 측정 주파수 승인이 아니다. 부품·LED·분해·PCUSB·084저장/복원/menu/GBC는 이미 확정/답변됐으므로 반복 요구하지 않는다. CF86 외부PSRAM/async/common-cause 및 최신MCU/전체SPI80·96KiB는 다음 별도 범위다.

## 근거와 제한

host02 94검사/4인과, text01 16파일/4변조/initial미획득, ARM01 build02 성공/호출순서 통과. host01 93은 이전 snapshot이다. 실제 하드웨어 핀/카드/시간/SRAM/CRC assembly는 모델이며 new RTL/Questa/fit/ASM/ARM실행은 없다. writer 전739341–955390회/기존100만, writer60/10000, 시간11.32/12.82초는 모델 값이다. frozen SysTick 반례089를 유지하고 저장을 보장하지 않는다.

ARM checker 최초 menu whole-file equality 실패는 미사용 메뉴복사 제외 때문이었다.11개 전체소스 hash+정확한 runtime prefix+13개 원본ARM입력을 확인했다. Make 최초 cdcuser.o dependency 실패/retry도 보존한다. 동결 `probes/nes-clock-report090/evidence/` 2063파일 manifest `5ecbc6fe3f5580943d0a9d991d880595caa1d30db37cb78815114bc2c42f0512`. verifier090를 사용하고 완료 finalizer를 재실행하지 않는다. 준비도4/7/1, installable=false.

---

## 이전089 기록

# NES 현재 인계 — CF87 구성089와 호출 예산

089는 고정 CF87 fit의 ASM/압축과 오류 시 중단하는 MCU 구성 경로를 완성했다. 실제 구성·088 reader·084 mini/runtime의 호스트 합산은 정상/부재729572회, 진행 정지921626회로 기존100만 회 제한을 통과했다.304검사·실패 대조4개와 같은 C의 ARM 오브젝트를 확인했다. 제품 main/단일 SD·TXT·화면 세션과 최종 펌웨어 링크·실기 패키지는 아직 미완료다.

[089 결과](../../analysis/CLOCK-CONFIG089-RESULT.ko.md), [구성 계약](../../docs/nes-clock-config089-contract.ko.md)을 먼저 읽는다. PR39은2026-10-08T04:09:45Z 병합됐고 master `fef3935525cc621d8235337d15c623605943b895`에서 시작했다. 현재 브랜치 `codex/nes-clock-config-089`. 사용자만 병합한다.

## 다음 작업

1. **제품 플랫폼 함수**를 만든다. 현재 실제 구성·reader·mini의 순서는 host test가 호출하며 main에 연결하지 않았다. 초기 화면 marker→089 구성→088 reader→RAM→mini→실제081 SD init/mount→084 space/writer/readback/terminal을 연결한다. static alphabet을 사람이 읽을 raw snapshot/판정 TXT로 교체한다.
2. 합산 정상/부재729572회, 진행 없음921626회다. 실제 SD init/space 등 추가 호출을 반드시 함께 계측한다. 특히 후자는 남은78374회뿐이다. writer의 기존 별도10초/10000회 허가 구간은 그대로 지키고, observer 실패 뒤 fault clear·retry별 scope restart는 금지한다. SysTick+window 정지 모델은 mini 복귀 중1000001회/74803바이트에서 차단된다. 이때 TXT를 약속하지 않는다.
3. CF87 RBF510856/SHA `c96d4d3e846a9914a3ab34cfeabc9f4c755516b5166793a510f322f6ba774708`, RLE59700/SHA `e772ead5e070c71767df2318d91f5d83d629e8ffedd275b19e81c842133cb4a2`. 이미 same-fit ASM 완료했으므로 이유 없이 재생성하지 않는다. 고정 generated header의 descriptor를 사용한다. CRC32는06a503c4. configuration byte/bit 모델과 실제 전기 타이밍은 구분한다.
4. 최종 ARM 링크/callsite, SPI/재구성/RESET 경계 및 동일 ASM/ARM/044 복원 manifest 후 report-only trial. 현재 ARM은17876바이트 object뿐이다. CF86 외부PSRAM/asyncclear/commoncause 및 전체 core/MCU/80-96KiB는 별도다.084 실기 저장·044복원/menu/GBC PASS를 보존하고 부품/LED/분해/PCUSB/저장 재질문은 하지 않는다.

## 보존·검증

host04는304검사, 최종 인과02는CRC/nSTATUS/sharedguard 제거3개 및byte단위 예산1개다. 후자는 로컬40000한도 실패이며 전체100만 초과 실험으로 부르지 않는다. ARM02가 host04와 같은 구성 C다. 원래087fit 입력은 보존됐고 새 map/fit/STA/Questa/하드웨어는 없다. 기존088 C와087 RTL 해시는 유지된다.

host01/02 시각 초기화 순서 오류, host03 초기301통과, host04 추가304, ARM01 상대경로cc1 실패를 보존한다. `probes/nes-clock-config089/evidence/` 793파일 manifest `9f1a6a39c0b1d39b725d6f85a04653736ab77a06091986e398a85d1102914018`. verifier089 사용. 완료 `finalize_clock089.py` 재실행/044–088 archive 변경 금지. 준비도4/7/1, installable=false.

---

## 이전088 인계 기록

# NES 현재 인계 — CF87 MCU reader088 검증

088은 CF87을 읽는 실제 MCU GPIO reader다. 1966호스트 검사·C보호제거3개와 기준클록 있음/없음의 실제C파형→RTL 응답146912bit·RTL대조1개를 통과했다. 같은 C로 STM32F401 ARM 오브젝트를 컴파일했다. 전체 main/구성/mini/TXT session·링크된 펌웨어·ASM/실기 패키지는 아직 미완료다. CF87 RTL/fit과CF86·084 실기 성공은 보존한다.

[088 결과](../../analysis/CLOCK-READER088-RESULT.ko.md), [reader 계약·통합 조건](../../docs/nes-clock-reader088-contract.ko.md)을우선한다. PR38은2026-10-08T03:32:54Z병합됐고master `72ed581bd6c333b1cd8c37ce776b2bb847dd9895`에서진행했다. 현재 `codex/nes-clock-reader-088`. 사용자만병합한다.

## 바로 다음 작업과 함정

1. **단일수집session으로통합**한다. CF87고정fit 별도사본ASM/압축→boundedconfiguration sink→RESET-held actualreader→report RAM보관→mini복귀→084 nativeSD/space/writer/readback/terminal을연결한다. 현재reader는main에서호출되지않고FPGA를구성하지않는다. CF87파일만071/CF86에섞지않는다.
2. **예산계측이먼저다.** 정상reader공유검사389972회,frame541,3.005436초다. 기존60초/100만IO예산에byte별FPGA구성/초기mini/복귀를단순합산하면초과할수있다. 실제압축해제길이/호출수를계측해중복검사를줄이거나명시적으로분리된bounded phase를설계한다. fault를지우거나retry마다예산리셋금지. 관측부재/NO_PROGRESS는로그가능한결과이나false/공유fault뒤mini/SD/SRAM재사용금지.
3. 새TXT는사람이읽을결과와raw16byte×3,sequence/count/window/divisor/flags,elapsed/attempt/frame,가정CLKIN값을담는다. READY=서비스/valid=완료구간이지clockPASS아니다. ACTIVE는활동이며20-22MHz/외부전기승인이아니다. 성공한정적084저장시험을다시요청하지않는다.
4. sameCF87ASM/압축+최종ARM링크/callsite+SPI IO/구성전환/RESET소유권+044복원manifest까지닫은후report-onlytrial을전달하고사용자TXT/영상회수. CF86외부PSRAM/asyncclear/commoncause/최신코어MCU/전체80-96KiB는별도다. 부품/LED/분해/PCUSB질문반복금지.

## 증거·실패 보존

- host05/absent06 각각1966검사,생산C/헤더=ARM01. C보호제거3개(no-pair-check/no-deadline/no-owner-check)PASS(expectedfailure).450ticks+512query;tickwrap/freeze/오류뒤IO차단/소유권검사. flags변화2bit는정상변화가능하며CRC무결성이라고부르지않는다.
- wave01은host04정상trace. host05추가손상검사후정상trace SHA가동일 `0893f2996ef2b603a0b7c359c572a37c21bc3b0695b1ad46668e12cffcc93e91`. absent-wave01은absent06trace. 각각73456bit/295453events/541frames/3.005436sec. wrong-divider01은C_MISO_MISMATCH로거부. 087생산RTL2개변경없어그fit을해당관측회로범위에서만유지.
- ARM01은21912byte relocatable object SHA `7850f7beba96877876b74a84029c171412074797575d14ffced1fc5a60ef7cfb`. 링크된firmware/maincallsite/새ASM/실기/패키지없음. pinned084headers로컴파일. 실제timer/runtime는기존보호코드이고이host의시간/register/MISO는모형이다.
- host01MinGWprintf64compile실패(ANSIstdio수정),host02/03invalid0+publishedgap1모형오류,host04초기1965PASS/host05추가1966PASS보존. 실행본snapshot과최종publicsource를구분한다. 새동결416files manifest `a4f589d7c30af2b5d76057c85778097a7a8154a793dfb4009d716fc84e0d4b94`;verifier088. finalizer완료재실행/044–087archive수정금지.
- 모든FLOATjob종료/18000listener중지,라이선스오류/approvalreview거절없음.084physical저장/화면/044복원/menu/GBC PASS유지. 준비도4/7/1.

---

## 이전087 인계 기록

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
