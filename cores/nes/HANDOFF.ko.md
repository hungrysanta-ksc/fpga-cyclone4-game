# NES 다음 작업 인계 — 065 이후

현재 **NES-MENU-RETURN-065**. [결과](../../analysis/MENU-RETURN-RESULT.ko.md), [계약·재현](../../docs/nes-menu-return-contract.md), [준비도 가이드](../../docs/development/NES-HARDWARE-READINESS-REVIEW.ko.md). PR18은2026-10-07T03:54:55Z 병합됐고 master 28e58e240d999c7c53b1e3da9c439a8c1d4367ea에서 진행했다.044/GBC 실기 기준과 동결044–064를 보존한다. 신규 설치 쌍/물리 STM32·SD 결과는 없다.

## 완료한 경계

- 메뉴 버퍼 적재/전 byte readback·active SPI/TIM2 대기 종료·실제 FatFS 캐시/할당 한도·PREPARED 단일 블록 SD 쓰기/CRC/busy 오류를 연결했다. 진단부터 RESET 해제 후100ms 안정화·CIC/SRAM 검사까지 USB/active 소유권을 유지한다. 후속 오류는 RESET을 다시 잡고 BLOCKED로 들어간다. 외부 전원/RESET 대기이며 패드 취소가 아니다.
-93 helper/복귀 검사(복사20/대기12/로그24/SD16/FatFS7/실제 main 구간14),4개 지정 mutation 실패,상위41/18입력/16메뉴/native 오류2를 확인했다. 주변 핀/카드/CPU/FAT는 모델이다. 일반 load_rom 분류/설정 전체는 소스/ARM 근거이며 전체 host 실행이 아니다.
- 최종 ARM link의세 marker·한 shared call·같은 목적지의 두 narrow/wide 분기,메뉴 copy와 FatFS guard 두 호출을 확인했다. compile-only, 설치하지 않는다.
-80/96KiB180224바이트/901152프레임의 전체 C SPI trace는063과 동일.063 보드50,464,224응답 비트와061 fit2386LE/186LAB/44M9K/135핀/PLL1·내부 최소0.131ns를 동일 trace/RTL 경계에만 재사용한다. 신규 Questa/Quartus는 없다. 전체 코어059959LAB/4여유·마지막8프레임은 별도다.
- 보호된 메뉴 준비에서만SD PREPARED 로그를 쓰며 RETURN_READY_RESET_RELEASED는 RAM/UART-only다. 해당 기록은 실제 화면 성공이 아니다. 진단 복귀의 최근/즐겨찾기 수는0이고cfg_save를 생략한다. 일반 inactive 경로는 기존 동작이다.

## 다음 순서와 완료 조건

1. 정확한 PSRAM 부품/speed grade/보드 대응과tOE/tWP/tDS/tDH/tHZ min/max·외부 IO를 확보한다. FXPAK Pro/Mk.III STM32+EP4CE15F17C8은 알려진 대상이다. 제품명을 다시 묻지 않는다. Rev.D 문서와 실제 관측을 구별하고 총16MiB/16bit/70ns를 완전한 사양 증명으로 쓰지 않는다.
2. 최종 FPGA ASM/압축 roundtrip·ARM 쌍 manifest·SD 원본 백업/rollback을 같은 후보로 준비한다. 메뉴 실제 파일 형상·최대시간 정책·card/write protect·LED/UART 가독성 시험표를 포함한다. CF61/protocol59만으로 설치 파일 동일성을 판단하지 않는다.
3. 제한된 적재/전체 비교/STOP/base·메뉴 복귀/오류/전원·RESET/재진입/GBC 회귀를 기기에서 관측한다. 전체 SNES 소비자 완성을 선행 조건으로 추가하지 않는다.
현재 완료5/부분6/미완료1. H08/H09는 물리 종료/가시성/복귀가 남아 부분 완료,H06 외부 IO는 미완료다. SD 복사를 요청하거나 실기 준비 완료를 선언할 단계가 아니다.

## 근거와 운영

probes/nes-menu-return-065의3249파일 manifest SHA256:00588f074cdc63f1736267a735df8fd4b1b25b5721d42f77d78708ac207923c2. 초기 준비/include/host/ELF/FatFS/longjmp 실패를 보존했다. 동결 후 verifier 로그 경로 오기는 공개 checker에서만 수정했으며 archive는 그대로다. finalize_nes065.py 및 이전 finalizer를 다시 실행하거나 동결 파일을 변경하지 않는다. raw/ROM/ELF/STM/license는 공개하지 않는다.
큰 검증 진전마다 정리·commit·push·한국어 PR을 만든다. 제목 한국어,본문 작업 목표→작업 내용→작업 결과로 달성 여부·부족한 점·다음 목표를 명시한다. 병합/제품 배포는 별도다. 실제 Questa는 기존 Starter FLOAT wrapper를 순차 재사용하고 license smoke/inherited 실패 경로/새 유료 entitlement 추정을 반복하지 않는다.
