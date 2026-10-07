# NES 현재 인계 — 076 제한적 SRTC 메뉴 복귀

**075에서 확인한 carttype55 거부를 active 복귀 경로에서 수정했다.** 받은64KiB 메뉴의 전체CRC/헤더를 확인하는 새 분류기와 실제 복사 중 재CRC·전체PSRAM readback을 연결했다. 일반/GBC 분류기는 그대로다. [076 결과](../../analysis/MENU076-RESULT.ko.md)·[검증 메타](../../analysis/menu076-verification.json)를 먼저 읽는다.

## 현재 검증과 제한

- 호스트853검사(분류256지점×3오류=768 포함), CRC 제거2인과대조 통과. FatFS/SRAM은 모델, 전체load_rom 호스트 실행은 아니며 실제active 구간을 추출했다.
- ARM 전체 링크와 실제 새 분류/승인/복사/CRC 호출, 기존3marker/공유run/READY/CF68 검사 통과. 180108바이트 SHA1af4cc50de3a3c71e57d328007c301f3cc5da3fded16e989955414d640296762, ID NES-MENU076-CF68. **compile-only, 설치 금지**. 기존071 쌍/069표식에 새076 MCU를 혼합하지 않는다. 새 실기패키지 없음.
- 고정069 275입력 중memory.c/nes_menu_return.c/Makefile만 변경,272동일. 새helper2/VERSION 별도. SDnative/FatFS/SPI/타이머/main/기존smc/sgb/GBC는 그대로다. 새RTL/Questa/Quartus/ASM 없음.
- 프로필은 정확히 받은65536바이트/CRC c014b571/SRTC/map31/8KiB SRAM/resetff02뿐이다. 범용메뉴 지원/CRC 보안인증이 아니다. 분류와복사 각각유한IO·오류차단,공유fault후close도금지한다.

## 다음 작업

1. **SD 0바이트 원인은 미확정**이다. 메뉴를 호출하지 않는073/074와076 메뉴수정을 혼동하지 않는다. 다음은 실제 SD DATA/CRC 응답 샘플·busy와보고서/할당예산 인과대조다. 075의CMD24 시작간격2클록은단순8클록누락을원인으로확정할근거가아니다.
2. 원인과가시적출력이확보된뒤새실기패키지를설계한다. 074 반복/LED 영상/분해/PC USB/같은파일재요청금지. 무제한legacy fallback·오류검사완화·불확실쓰기재시도금지. nativefault RESET/USB·추가SD/SPI/base 차단유지.
3. 실제TXT,원본044복원,메뉴/GBC재진입,base FPGA호환성/외부IO가남는다.071설치보류와준비도5완료6부분1미완료유지.

## 입력·보존·게시

정상044 firmware.stm과TXT성공HWINFO002 firmware.stm.bak-hwTest는별도역할이다. 두파일과m3nu.bin/base를이미보존했고before-sdinfo072사본은없다. [075 결과](../../analysis/OFFLINE075-RESULT.ko.md)의전체해시/관측을따른다. 알려진Rev.D/STM32F401RCT6/EP4CE15F17C8N/EBLL-70BLI×2는재질문하지않는다.

076증거 probes/nes-menu076/evidence/:1467파일,manifest `648144bf654b167b7316f77673eceb5b0f097ec566e5f382d030d6ef897aec0c`. verifier076사용,finalizer재실행/동결044–076편집금지. 최초Windows열거형충돌·mini자기복사·Makefile검사누락실패와ARM로그보존. 호스트최종소스는ARM입력과동일해시다. 이번시작시PR27open/미병합,같은PR업데이트;다음차례상태재확인. 주요검증진전마다한국어PR3절과미달성/다음완료조건을유지한다.

---

아래는074 당시 역사적 기록이며 위076과075 결과가 우선한다.

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
