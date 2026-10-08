# NES 현재 인계 — 실제 SD·구성 통합096

최종094 ARM과 같은 C를 실제 FatFS·native SD·FPGA 구성 데이터의 압축 해제·READY 대기와 연결했다. 호스트 통합154경우와 보호 제거 대조4개가 통과했다. 정상80/96KiB 전체 비교·STOP·기본 FPGA 구성 복귀, 첫 오류 뒤 추가 IO 차단을 확인했다.

PR45 병합 `7d669b1d6d9167c180b9bf5a432c459f4da09a99`, 작업 브랜치 `codex/nes-native-session-096`. [096 결과](../../analysis/NATIVE096-RESULT.ko.md)와 [검증 계약](../../docs/nes-native096-contract.md)이 현재 기준이다. PR은 사용자가 병합한다. 제목/본문은 한국어, 작업 목표→작업 내용→작업 결과 세 섹션에 달성/미달성/다음 목표를 쓴다.

## 다음 작업과 완료 조건

1. 동일086 fit03의 ASM과 실제 압축 구성 파일을 확보해 크기·해제 바이트를 대조하고, 실제 main의 메뉴 SRAM 재적재·표시·RESET 해제·보고 경계까지 연결한다. 이후 최종 ARM/FPGA/정확한044 복원 쌍과 설치 조건을 확정한다. 진단과 base 두 구성 파일 모두 대상으로 한다.096의1100바이트 시험 데이터를 실제 bitstream으로 오인하지 않는다. 동일 fit에서 ASM만 수행할 때도 fit 입력·출력 해시를 먼저 고정한다.
2. `nes_menu_sd_probe()` 정상 반환 뒤 IRQ는 복구되지만 RESET은 유지된다. 이후 실제 main pending-menu와076 SRAM 재적재/표시/RESET release/보고를 하나의 흐름으로 검증한다.096 SRAM stub은 호출되면 실패한다. 실패 후 SD/SPI/SRAM/기본 구성 재사용 금지, FAILED 유지, 첫 오류 보존, RESET/USB 소유권을 유지한다.60초 IO window는 main 메뉴 작업부터 시작하며114/136초 모델 전송에 소급 적용하지 않는다.
3. 생산 변경이 필요하면 새 ARM 및 관련 파형 증거를 만든다. 변경 없이 같은fit ASM을 만들더라도 외부 IO/공통 클록 고장 정책·관측 단계·정확한044 복원 경로가 정리되기 전에는 실기 설치 파일로 전달하지 않는다. 제품 NES의 RUN/video/input/audio는 이 진단 뒤 별도다.

## 현재 근거와 한계

- 최종154경우=80KiB FAT16/SDHC76 +96KiB FAT32/SDSC76 +교차 정상2. 성공8/고장 주입146이며 SD 고장120은5단계 첫·중간·마지막 샘플이다. 모든 명령의 전수 검사는 아니다. CRC/RLE/READY/FAILED 보호 제거 대조4개가 예상 assertion에서 실패했다.
- 최종 실행은 `suite05`, `fat32-96-02`, `fat32-block80`, `fat16-byte96`, 대조는 `negative-crc02`, `negative-ready02`, `negative-config01`, `negative-latch01`. `verify_nes_native096.py` 통과. 동결 1632파일 manifest `379a523afc4024275606ce56475aca94464bbc2cab16d9c84ee15e0462d95444`. 초기 헤더/상수/COFF 링크 오류, delayedREADY/공유시간/핀 검사를 보강한 중간 실행도 보존했다. 완료 finalizer 재실행/044–096 archive 편집 금지.
- 실제 FatFS/native20함수/checked config/READY/094 세션 C 실행. 카드 준비에서 CMD24, 측정 세션은0writes. preinitialized 카드 seam, CRC assembly primitive/핀/FPGA 응답/시간은 모델. 실제 초기화/main메뉴/실제구성바이트/하드웨어 미검증. 새 ARM/RTL/fit/STA/ASM/패키지 없음.
- 핵심 C9개는094 최종 ARM과 같다.094 ARM180928 SHA `70aa72fa1a70a90d501bac386ff4d159f46a12a48e15f0880c95f6fd78d208da`. [094 결과](../../analysis/SESSION094-RESULT.ko.md), [095 결과](../../analysis/REPLAY095-RESULT.ko.md) 참조.095 정상 전체901152프레임/50464224비트는34비트 guard 반복 전제의 조건부 분리 결과다.096 native 시간과 같지 않으며 C/RTL co-simulation이 아니다.
- [086 결과](../../analysis/CLOCK086-RESULT.ko.md)의 fit03는2446LE/191LAB/44M9K/min0.158ns.093 SDF는 구조적 최대23.699ns 근거이며 게이트 시뮬레이션/실기가 아니다. 두 클록 정지+lock HIGH의 CE9µs 반례와 외부 IO/공통원인 조건을 숨기지 않는다.

## 유지할 실기 정보와 제품 목표

084 저장/재읽기/화면 및 정상044 복원·메뉴·GBC PASS,092 클록 활동/TXT/복원 PASS를 유지한다.092로 절대 주파수를 확정하지 않는다. 저장/복원·부품·LED·분해·PC USB 질문을 반복하지 않는다. 실기는 외부에 있으며 검증된 패키지를 사용자가 실행하고 로그를 전달하는 방식이다. 알려진 FXPAK Pro/Mk.III Rev.D 및 부품 정보는 기존 공통 가이드를 따른다.

준비도4완료/7부분/1미완료, 설치 승인 false. SMB3(J) mapper4·PRG256KiB+CHR128KiB,393232바이트 SHA `dbb1cb5e18b091ca9101b1c2f5a5d6bdbeaa4a30ae1a504251310f6765cabb49`가 첫 게임이다. ROM은 Git에 넣지 않는다.80/96KiB 진단을 게임 지원으로 표현하지 않는다. 전체 코어4LAB 여유·DMC·IRQ/영상/입력/음향 미완료는 [개발 계획](../../docs/nes-development-plan.json)에 유지한다. 과거 상세 이력은 단계별 결과와 Git history에서 읽는다.
