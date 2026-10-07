# NES 다음 작업 인계 — 072 이후

현재 전달 도구는 **SDINFO072-BASE069 원본 SD 수집기**다. NES 진단 쌍은 **NES-CF68-PAIR-071 / MCU069 / FPGA068 CF68**를 그대로 유지한다. PR26 병합 `dbb4a3b171651363ed913ffeb3c0e5ab3265eb66`에서 `codex/nes-sd-inspection-072`로 진행했다. [072 결과](../../analysis/SD-INSPECTION-RESULT.ko.md), [수집 계약](../../docs/nes-sd-inspection-contract.md), [실행 안내](../../docs/SDINFO072-RUN.ko.md), [기계 요약](../../analysis/sd-inspection-verification.json)을 먼저 읽는다. 이 인계는 과거 문서의 당시 현재/다음보다 우선하며, 모델/담당 변경으로 검증 수준을 낮추지 않는다.

## 완료 범위와 동결

collector52/writer23/platform6/report29·인과 오류 대조2·ARM 실제 main/collector/writer/최종 보호 호출을 확인했다. 입력4개는 읽기 전용이며 TXT만 새로 생성·sync/close/readback한다. format_ok/finished/TXT SAVED는 실제 입력·메뉴 승인이나 복원 성공이 아니다. 기존 file_init/mini startup은 예산 밖 legacy 코드다. 전용 main은 메뉴 이전에 noreturn 수집기로 들어가지만 ELF의 기존 함수 제거를 주장하지 않는다.

ARM132768바이트 SHA `8215d81dd84a07f3dfffe5163163c07ef1166fcbfab25b95cbc4942dbc42f724`, identity SDINFO072-BASE069. 내장mini SHA `9ae79c3028391063338d42ae16b19acf48d0d80858939b015ef6481f55cbefe9`. 전달 zip은 firmware 하나이며 공개 제품 릴리스가 아니다. 외부 사용자가 교체 전 원본을 독립 백업하고 SD에 firmware.before-sdinfo072.stm 사본을 만든다. 실행한 뒤 전원을 끄고 새 HW003nnn.TXT를 반환하며 원본 firmware를 복원·readback하고 메뉴/GBC를 관측한다.

동결0721411파일 manifest `c10bb9f31911addb4dd87f9258bc84a3074dca7574db3a2b1003aeca921f3c39`;069의275개 입력과072 전체 입력1333개를 구분한다.04 ARM/호스트 최종과 실행 소스·초기 VERSION/기대값 오류를 보존했다. VERSION 재현의 마지막 CRLF/LF 최초 실패는 동결 밖 reproduction-review 전사이며 새 준비 도구는 원본CRLF와 동일하다. finish_nes072.py 및044–072 finalizer를 다시 실행하거나 동결 archive를 바꾸지 않는다. public verifier는 private evidence를 필요로 한다.

## 다음 작업 순서와 완료 조건

1. 사용자에게 제공한 수집 패키지의 **새 HW003nnn.TXT**, 화면 이름/코드/시간과 원본 복원·메뉴/GBC 관측을 먼저 확인한다. 과거 HW002000과 호스트 SYNTHETIC-NOT-HARDWARE.TXT를 이번 실물 결과로 혼동하지 않는다. check_nes_sd_inventory.py로 framing/CRC/shape를 검사하되 실행 출처·원본 사본/현재 펌웨어 구분은 별도로 확인한다. 공유 오류/예산이면 수집은 멈추며 기존 실패 로그를 해석하고 불확실한 자동 retry를 넣지 않는다.
2. TXT 헤더/reset byte로 **실제 menu 분류 C**의 입력을 재구성한다. 기존 smc_id/sgb_id를 먼저 읽고 unsafe shift/짧은 read/초기화 없는 reset_inst를 bounded adapter에서 다룬다. 변환한 adapter를 원본 전체 동작이라고 과장하지 않는다. plain mapper0/1·carttype0–2·offset/payload≤4MiB·특수 FPGA/SGB/EGBC 없음 조건을 명시하고, 현재SD가 그 조건을 충족하는지 확인한다. parseableRLE/작은 크기만으로 승인하지 않는다. 기기 CRC만으로 SHA/독립 backup을 확보했다고 쓰지 않는다.
3. 독립 전체SD/게임/GBC/세이브 백업과6개변경파일/base/menu 제한 rollback을 구분한다. 실제 복원 전후 byte/SHA 확인 및 메뉴/GBC 실행 결과를 따로 기록한다. preflight는 읽기 전용 plan이며 실제 설치/복원기가 아니다.
4. 전압/PCB/비동기SPI/SNES·reset해제 전 안정과 lockedHIGH CE>8µs 반례를 검토한다. 200µs startup은 voltage sensor가 아니며 같은 입력 PLL은 독립 차단이 아니다. 임의 delay/blanketfalsepath로 승인하지 않는다. 조건과 회복 경로가 정리되면 제한된 CF68 load/CHECK/STOP/base/menu/reentry/GBC 실기 패키지를 별도로 준비한다. 수집072는 CF68 적재 시험이 아니다.

## 고정071/069/068 기준

071 RBF510856 SHA `45dcb3f3908b427b66f3fe52f14e56c80efae58d422af95b322580bd57f0a572`, packed212523,069 ARM179336 SHA `268bc38df477516cbcee19f17b192151b79c6e011dc801756d1ad02fc0262499`. fpga_nl8.bi3,표식 NES VERIFY 069 80.nh1/96.nh1,로그 `/sd2snes/nes-verify-last-069.txt`를 같은 쌍으로 유지한다.065/066/072 firmware와 섞거나 timestamp header를 정규화하지 않는다. 071manifest `a70297c41f163eacdf9423e9c93ba8abb5a828aa9bf05e3112eadde7d5848cbd`,374파일 audit 재통과. [071 결과](../../analysis/CF68-PAIR-RESULT.ko.md)/[계약](../../docs/nes-cf68-pair-contract.md)에 원본db114/관측incremental17 제외·ASM/CPF·C복원510856+66309·오류13·로컬preflight23가 있다.

070180224bytes/901152frames/50464224응답bit/ACK/FINISH/STOP은 디지털 보드 세션이며 actual MCU/SD/화면 proof가 아니다. [070 결과](../../analysis/CF68-SESSION-RESULT.ko.md)를 따른다.068최종 fit03 2400LE/195LAB/1479regs/44M9K/135핀/PLL1/최소hold0.140ns와069 ARM·95helper 회귀를 현재 source 경계에서 유지한다. 전체NES059의959LAB/4여유/마지막8프레임은 별도 근거다. START/불확실DATAACKretry/native 공유오류 뒤SD/base 금지,RESET/USB 보호를 보존한다.

## 알려진 실기·준비도·게시

FXPAK Pro Mk.III Rev.D / STM32F401RCT6 / EP4CE15F17C8N / PSRAM IS66WVE4M16EBLL-70BLI×2 / SRAM IS62WV5128EBLL-45HLI는 실물 확인 완료다. 부품/사진/분해/PC 직접연결을 다시 요청하지 않는다. 외부기기 패키지→사용자실행→TXT/영상으로 진행한다.044 LINK SCREEN1→2→3→1·자동종료 없음·GBC 정상 플레이와 GBC152/originalNES334 해시를 유지한다.

준비도5완료/6부분/1미완료는 작업량 비율이 아니다. H06외부/H08H09실물가시성·시간/H11설치/H12실제복원은 남고071 installable/hardware/clock_halt_safe=false다. 주요 진전마다 명시적stage/commit/한국어PR 세절과 목표달성/미달성/다음완료기준을 남긴다. Questa는 기존 Starter FLOAT wrapper로 실제 필요 job만 실행한다. 이번072는 새 Questa/Quartus를 실행하지 않았다. 실제 모델 변경은 도구로 주장하지 않는다.
