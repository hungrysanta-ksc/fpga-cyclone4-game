# NES 다음 작업 인계 — 064 이후

현재 **NES-DIAG-RECOVERY-064**. [결과](../../analysis/DIAG-RECOVERY-RESULT.ko.md), [계약·재현](../../docs/nes-diag-recovery-contract.md), [준비도 가이드](../../docs/development/NES-HARDWARE-READINESS-REVIEW.ko.md). PR17은2026-10-07T03:02:30Z 병합됐고 master `76bfe89dddbae7aa57fdf6eafff9167fbe19237b`에서 진행했다. 044/GBC 실기 기준과 과거 동결 근거를 보존한다. 새 설치 쌍과 물리 STM32/SD 결과는 아직 없다.

## 완료한 경계

- active 진단에서 실제 SD busy·응답·data 시작·CRC 오류를 반환한다. CMD17 버퍼 읽기와 R1/CRC7/네 DAT lane CRC16,sticky 오류·쓰기/오프로딩/자동 init 방어를 연결했다. 실패한 SD로 base/메뉴를 다시 읽지 않고 GPIO를 복원한 뒤 RESET/USB 보호를 유지한다.
- checked FPGA 설정은 독립 FIL/256바이트·검사한 RLE·핀/파일/출력/tick/poll 상한으로 실패를 반환한다. legacy044/056와 원래 programmer는 그대로 남는다. SD가 정상인 설정 실패에만 base 복구를 시도한다.
- 실제 helper FPGA22/SD24/LED16/UART5/FatFS6,상위41회귀/18입력/16메뉴/native 오류 보호2와2개 causal mutation을 통과했다. 실제 핀/카드/CPU는 host 모형이다. FatFS는 실제 읽기 함수를 추출했고 FAT chain/card는 모형이다.
- 최종 ARM 전체 link에서 세 marker·한 shared run call·그 call로 합쳐지는 두 분기,checked 설정 두 호출·runtime/SD fault 호출을 확인했다. compile-only이며 설치하지 않는다.
- 새064 C의80/96KiB 전체 SPI trace가063과 SHA256 동일하다.180224바이트/901152프레임/마지막 ACK/FINISH/STOP,START 없음.063의50,464,224응답 비트 보드 핀 재생과061 fit2386LE/186LAB/1458regs/44M9K/135핀/PLL1·내부 최소0.131ns를 동일 기록/생산 RTL에 한정해 재사용한다. 새Questa/fit은 수행하지 않았다. UART/SD/CPU 지연·물리 클록 위상 증명으로 확대하지 않는다.
- LED는 VALIDATE/CHECK read 점멸,CONFIG/LOAD write 점멸,RECOVER 둘 켜짐,BLOCKED write 켜짐+ready 점멸이다. 안전한 종료에서 원래 모드/논리 상태를 복원한다. UART phase/error/25% 관측과 active 송신 상한을 구현했지만 실제 가시성/물리 시간은 미검증이다.

## 다음 순서와 완료 조건

1. **메뉴 재적재 offload·늦은 SD 로그·active 밖 UART 및 기존 TIM2 SPI delay를 점검**한다. 메뉴 준비/로그까지 실제 하위 대기 종료와 오류 전달을 연결하고 실패·재진입·RESET/USB/SD 보호를 검증한다. 현재 H08/H09는 부분 완료다. 보호 루프는 외부 전원/RESET 개입을 기다리는 의도적인 fail-closed 상태이며 패드 취소가 아니다.
2. FXPAK Pro/Mk.III STM32+EP4CE15F17C8은 알려진 대상이다. 제품명을 다시 질문하지 않는다. 과거 Rev.D와 실제 보드 관측을 구별한다. PSRAM 정확한 부품·speed grade/BOM 대응과tOE/tWP/tDS/tDH/tHZ min/max·외부 IO 제약은 부족하다. 기존 총16MiB/16비트/70ns 표기를 전체 사양 증명으로 쓰지 않는다.
3. 최종 FPGA ASM/압축 roundtrip·ARM 쌍 manifest·SD 백업/rollback을 준비하고,같은 후보로 필요한 영향 검사를 닫는다. CF61/protocol59만으로 파일 동일성을 판정하지 않는다.
4. 제한된 적재/전체 비교/STOP/base·메뉴 복귀/재진입/전원·RESET/GBC 복귀를 실제 기기에서 관측한다. 일반 NES 소비자 완성을 선행 조건으로 추가하지 않는다. 전체 코어959LAB/4여유·소비자·CDC·STA와마지막8프레임은 별도이다.

현재 점검표 완료5/부분6/미완료1이며 공수·제품 완성률이 아니다. H06 외부 IO는 미완료다.064 표식/log명은 생성 소스의compile-only 이름이며 사용자에게 SD 복사를 요청할 단계가 아니다.

## 근거와 운영

로컬 `probes/nes-diag-recovery-064/` manifest2733파일·SHA256 `ccd03676bc933b8209916aeba3af3b8d2e068688525c11726e3ba12985f351df`에 실패·수정·최종 실행 소스/로그/ELF를 동결했다. `finalize_nes064.py` 및 과거044–063 finalizer를 다시 실행하거나 manifest를 무효화하지 않는다. raw/ROM/ELF/STM/license는 공개하지 않는다. 초기LED extern 누락,ARM optimizer shared-call 검사,host mock/선언/링크 실패를 성공 로그로 덮지 않았다.

큰 검증 진전마다 정리·commit·push·PR을 만든다. PR 제목은 한국어,본문은 `작업 목표`→`작업 내용`→`작업 결과` 순서로 달성 여부·부족한 점·다음 완료 조건을 명시한다. 병합/제품 배포는 별도이다. 새Questa가 필요하면 기존 Starter FLOAT wrapper를 순차 재사용하며 license smoke/실패한 inherited 경로/새 paid entitlement 추정을 반복하지 않는다.
