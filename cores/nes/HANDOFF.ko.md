# NES 다음 작업 인계 — 066 이후

현재 **NES-PAIR-PREFLIGHT-066**. [결과](../../analysis/PAIR-PREFLIGHT-RESULT.ko.md), [계약·재현·실기 시험표](../../docs/nes-pair-preflight-contract.md), [준비도](../../docs/development/NES-HARDWARE-READINESS-REVIEW.ko.md). PR19은2026-10-07T04:37:36Z 병합됐고 master40374438ebdd82311e0882c0f59c9d451d8ef703에서 진행했다.044/GBC·동결044–065를 보존한다.

## 완료한 경계

- 오프라인061 FPGA ASM/CPF와065 최종 ARM 쌍을 만들었다. 준비번호066/실행 firmware065/FPGA061을 구별하며 표식은 NES VERIFY 065 80.nh1 및96.nh1이다. 설치 승인은 아니다.
-061과41개 fit 파일 일치,23개 입력/요약·129개 DB 파일 계보 고정. Standard25.1 ASM/CPF 성공. Lite Edition DB 비호환 최초 실패를 보존했다. 새 map/fit/STA·ARM link·Questa는 없다.
- 구형 C 압축기의 EOF 추가FF1바이트를 전체 비교로 검출했다. 수정 전209944바이트 압축이510857바이트로 복원되는 assertion 실패를 보존한다.066 encoder209943바이트는510856바이트 원본과 정확히 일치하며 실제 C 프로그래머 host 모형에서 모든 byte를 비교했다. 긴 run/특수 token 경계66309바이트도 일치한다. C DONE·pin·FIL·tick은 모형이다.
-18개 사전 점검/백업/복원 계획 검사 통과. 독립 digest·변조/혼합/원본변경/경로탈출/기존 백업 보호를 확인했다. backup/rollback-plan은 SD를 수정하지 않는다. 대상6개와 base/menu 의존 파일의 제한 백업이며 카드 전체/GBC·세이브 백업은 별도다. 모형에서 원본1개 복원/신규5개 제거 계획이다.
-065 메뉴 복귀93/4인과 대조·최종 ARM/063과 같은 두 전체 SPI trace의 근거는 그대로다.061 fit2386LE/186LAB/44M9K/135핀/PLL1·내부 최소0.131ns와06350,464,224응답 비트는 재사용 경계다. 전체 코어059959LAB/4여유·마지막8프레임은 별도다. GBC152/originalNES334 보존.

## 하드웨어 식별 완료와 외부 타이밍 검토 재개

사용자 HWINFO002 TXT의 CRC가 정상이며 보드 스트랩0xC4/Rev.D, MCU DEV_ID0x423/Flash256KiB를 관측했다. [공통 하드웨어 가이드](../../docs/development/FXPAK-HARDWARE-REFERENCE.ko.md)에 사용자 기판 사진으로 확인한 U501/U502의 IS66WVE4M16EBLL-70BLI ×2, FPGA EP4CE15F17C8N, SRAM IS62WV5128EBLL-45HLI를 기록했다. PSRAM은 실제 EBLL 공식 문서와 대응해 70ns/총16MiB/전원·IO 2.7–3.6V 규격을 확인했다. 탑재 코드/속도 식별은 해결됐으며 외부 타이밍 승인은 남는다. 후속 확대 사진으로 MCU STM32F401RCT6도 확인했다. 사용자 재개 요청에 따라 [외부 타이밍 검토](../../docs/development/NES-PSRAM-TIMING-REVIEW.ko.md)를 시작했다. 기존061 RTL의 주소/CE에 가정한2ns 지연 차이를 넣는 Questa3대조에서 주소-late 경우만 쓰기1/읽기1 위반을 검출했다. 물리 지연 측정/실기 고장이 아니며 다음 진단 전용 준비·샘플 후 유지 구간의 검증 기준이다. PR20은 master ffb920513a33746d8e76d3eb2c4f0854a320ad94로 병합 확인했다. 기존066 설치 gate는 그대로다. 실기는 외부에서 펌웨어 실행→SD TXT 전달 방식으로 진행한다.

## 다음 순서와 완료 조건

1. 현재 사용자 SD의 원본 firmware/base/m3nu.bin 및 GBC·세이브를 독립 백업하고 readback한다. 정확한 smc_id/sgb_id 분류와 base 호환성,설치/복원 실행·전원손실 경계를 검증한다. backup의 RLE/크기 예비 검사로 승인하지 않는다.044 package나041 기준 과거 installer를 현재 SD 원본 대신 쓰지 않는다.
2. 사진으로 확인한 IS66WVE4M16EBLL-70BLI ×2와 EBLL Rev.D3 타이밍을 기준으로 배선·FPGA/PCB 지연·외부 IO 예산을 검토한다. 제품명과 PSRAM 부품/속도를 반복 질문하지 않는다. 부품 사양 식별 완료를 전압 실측·외부 타이밍 승인으로 확대하지 않는다.
3. 같은 쌍으로80/96KiB 적재/전체 비교/FINISH/STOP/base·메뉴 복귀,SD·CRC·busy·RESET·전원·재진입·GBC 회귀를 기기에서 관측한다. LED/UART·카드 쓰기 방지·실제 시간도 기록한다.68.3/82.0s는 기존 wire 추정이지 측정이 아니다. CPU/PPU RUN과 전체 SNES 소비자 완성을 선행 조건으로 추가하지 않는다.

현재 완료5/부분6/미완료1. H11은 오프라인 쌍까지,H12는 모형 백업/계획까지 진전했다. 실제 SD/menu/복원·외부 IO가 남아 있으며 installable=false다. 새 SD 복사를 요청하거나 실기 준비 완료라고 선언하지 않는다. PREPARED SD 기록과 RAM/UART RETURN_READY_RESET_RELEASED는 실제 화면 복귀 관측과 구별한다.

## 근거와 운영

동결066 manifest와 파일 수는 [기계 판독 결과](../../analysis/pair-preflight-verification.json)에 고정된다. Standard/Lite ASM 실패·성공,구형 압축 실패와 corrected all-byte 통과,18개 로컬 모형을 보존한다. finalize_nes066.py 및 이전 finalizer를 다시 실행하거나 동결 파일을 변경하지 않는다. raw/ROM/DB/ELF/STM/license는 공개하지 않는다.

주요 검증 진전마다 commit·push·한국어 PR을 만든다. 본문은 작업 목표→작업 내용→작업 결과,달성 범위·부족한 점·다음 목표를 명시한다. 사용자 병합 보고 후 GitHub를 새로 확인한다. 실제 Questa는 기존 Starter FLOAT wrapper를 순차 사용하고 license smoke/inherited 실패 경로/새 유료 entitlement 추정을 반복하지 않는다.
