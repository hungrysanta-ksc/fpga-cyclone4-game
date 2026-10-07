# NES 다음 작업 인계 — 073 이후

지금 전달 후보는 **SDINFO073-BASE069 TXT 저장 수정 수집기**다. NES 쌍은071/MCU069/FPGA068 CF68를 유지한다. PR27은073 작업 시작 확인 시open/미병합이며 동일 PR에 재시험 수정을 반영한다. [073 결과](../../analysis/SD-WRITE-RECOVERY-RESULT.ko.md), [재시험 안내](../../docs/SDINFO073-RUN.ko.md), [기계 요약](../../analysis/sd-write-recovery-verification.json)을 먼저 읽는다. 이 인계가 과거 현재/다음보다 우선하며 모델/담당 변경으로 검증 수준을 낮추지 않는다.

## 실제 실패와 수정 경계

사용자072 사진에서버전/Save code4와 TXT 없음이 확인됐다.072의 active 진단에는 report-only write permission이 필요한데 수집기에서 열지 않았다. 실제 FatFS/SD helper로 FAT16/FAT32 모두 code4/전송0/entry 미반영을 재현했다.073 writer만 저장/readback 동안 nes_return_log_allow(true)를 소유하고 모든 종료에서 false로 회수한다. RESET/USB/offload와 sticky shared fault 보호를 우회하지 않는다. gate/runtime/wholeFatFS11개 입력은072/069와 동일하다.40통합검사·window제거mutation1·collector52/writer23/platform6/report29·ARM true/false2호출이 통과했다. SD/CMD24/media/CRC는 host 모형, 실제073성공은 아직 없다.

firmware133184 SHA `cd7eea7ae61cca3be60a8c5f876a09dbd29e0c6669ccba53462c035b654de5e7`,ID SDINFO073-BASE069,새로그HW004000–999. 원본 백업 이름 firmware.before-sdinfo072.stm은 유지한다. 현재072/073 firmware를 원본 사본에 덮어쓰지 않는다. Op/FAT result/Bytes/offset은 첫 실패의 실제 반환정보이며 표시이름은 저장완료 증거가 아니다.073은 메뉴/CF68/core를 실행하지 않고 완료 화면에 머문다. native fault는 화면갱신 없이 RESET/USB 유지 가능하다. collect60초/1Mpoll, report10초/10000poll; legacy file_init/mini startup은 예산 밖이다.

## 동결·실패 보존

073 `probes/nes-sd-write-recovery-073/evidence/`1571파일 manifest `eaa22dcf085ac6598484ed6ab5945bc6b56534996f83c18b0eafa24ce9fcd586`. final07 exact source,mutation,host01,ARM build02/실제호출/사진 관측을 보존했다. 경로/추출/타입/링크/FAT fixture/read-model 최초실패와 Make3.81 최초dependency를 보존한다. 마지막 finalizer keyword syntax실패는 동결 밖 전사이며 데이터 생성 전 수정했다. finish_nes073.py/document_nes073.py나044–073 finalizer를 다시 실행하지 않는다.072 공개코드·1411파일 및verifier는 변경되지 않았다. 새073 자료만 검증한다.

## 다음 완료 조건

1. 사용자에게 새073패키지를 전달하고 **새HW004nnn.TXT** 또는 Op/FAT/Bytes/offset이 보이는 실패 관측을 받는다. 기존 원본 독립 백업과072이전 사본을 유지한 채 firmware만 교체한다. 사용자에게 분해/부품/PC USB 연결을 다시 요구하지 않는다.
2. 새TXT framing/CRC/shape·입력4상태와 교체 전 원본/현재수집기 구분을 검사한다. 실제 원본 복원 뒤 메뉴/GBC 관측과독립backup/readback은 별도 확인한다. code0/TXT/CRC로 이를 승인하지 않는다.
3. actual smc_id/sgb_id의 unsafe shift/짧은read/초기화 없는reset_inst를 bounded adapter에서 다루고 변환 범위를 밝힌다. plain mapper0/1/carttype0–2/offset/payload≤4MiB/no specialFPGA/SGB/EGBC를 실제 원본 자료에 대조한다. parseableRLE/작은menu만으로 승인하지 않는다.
4. 전압/PCB/비동기SPI/SNES/reset안정·lockedHIGH CE>8µs 반례와복원 경로를 정리한 뒤 제한CF68 실기를 준비한다. 같은 입력PLL/200µs startup을독립안전차단/voltage sensor로 주장하지 않는다. 준비도5완료6부분1미완료/071 installable=false 유지.

## 같은 실수의 예방

상위 writer와platform mock이 각각통과해도 native 쓰기권한은 실행되지 않을 수 있다. 새 상태/권한이 여러층을 건너면 실제 호출자/FatFS/native guard/runtime 성공·오류를 하나의 시험으로 연결한다. 종료별permission회수·native fault뒤물리전송0·마지막화면보호를 확인한다.실제 source/ARM callsite와 같은입력임을해시로고정한다. 원시증거와모델범위/실물결과를구분한다.

## 고정071/069/068 기준

071 RBF510856 SHA `45dcb3f3908b427b66f3fe52f14e56c80efae58d422af95b322580bd57f0a572`, packed212523,069 ARM179336 SHA `268bc38df477516cbcee19f17b192151b79c6e011dc801756d1ad02fc0262499`. fpga_nl8.bi3,표식 NES VERIFY 069 80.nh1/96.nh1,로그 `/sd2snes/nes-verify-last-069.txt`를 같은 쌍으로 유지한다.065/066/072 firmware와 섞거나 timestamp header를 정규화하지 않는다. 071manifest `a70297c41f163eacdf9423e9c93ba8abb5a828aa9bf05e3112eadde7d5848cbd`,374파일 audit 재통과. [071 결과](../../analysis/CF68-PAIR-RESULT.ko.md)/[계약](../../docs/nes-cf68-pair-contract.md)에 원본db114/관측incremental17 제외·ASM/CPF·C복원510856+66309·오류13·로컬preflight23가 있다.

070180224bytes/901152frames/50464224응답bit/ACK/FINISH/STOP은 디지털 보드 세션이며 actual MCU/SD/화면 proof가 아니다. [070 결과](../../analysis/CF68-SESSION-RESULT.ko.md)를 따른다.068최종 fit03 2400LE/195LAB/1479regs/44M9K/135핀/PLL1/최소hold0.140ns와069 ARM·95helper 회귀를 현재 source 경계에서 유지한다. 전체NES059의959LAB/4여유/마지막8프레임은 별도 근거다. START/불확실DATAACKretry/native 공유오류 뒤SD/base 금지,RESET/USB 보호를 보존한다.

## 알려진 실기·준비도·게시

FXPAK Pro Mk.III Rev.D / STM32F401RCT6 / EP4CE15F17C8N / PSRAM IS66WVE4M16EBLL-70BLI×2 / SRAM IS62WV5128EBLL-45HLI는 실물 확인 완료다. 부품/사진/분해/PC 직접연결을 다시 요청하지 않는다. 외부기기 패키지→사용자실행→TXT/영상으로 진행한다.044 LINK SCREEN1→2→3→1·자동종료 없음·GBC 정상 플레이와 GBC152/originalNES334 해시를 유지한다.

준비도5완료/6부분/1미완료는 작업량 비율이 아니다. H06외부/H08H09실물가시성·시간/H11설치/H12실제복원은 남고071 installable/hardware/clock_halt_safe=false다. 주요 진전마다 명시적stage/commit/한국어PR 세절과 목표달성/미달성/다음완료기준을 남긴다. Questa는 기존 Starter FLOAT wrapper로 실제 필요 job만 실행한다. 이번072는 새 Questa/Quartus를 실행하지 않았다. 실제 모델 변경은 도구로 주장하지 않는다.
