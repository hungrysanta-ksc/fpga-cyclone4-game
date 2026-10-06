# NES H1 037: 복구 가능한 첫 실기 묶음 준비

035 MCU와 SPI 수정036 FPGA를 고정한 **NES-H1-BRINGUP-037.zip**을 만들었다.
실기 첫 실행·화면·RESET/재진입·GBC 복귀를 확인할 단계다. NES 게임 코어는 포함하지 않는다.
[시험 안내](../docs/nes-h1-bringup-test.ko.md), [검토 계약](../docs/nes-h1-bringup-contract.md),
ZIP (로컬 비공개 자료: `local-h1-bringup-037/NES-H1-BRINGUP-037.zip`), [기계 검증](h1-bringup-verification.json).

- 실제 Questa: 2타이밍×12위상, 각6조건 통과. ROM12,288/payload196,608바이트 exact.
  입력 수신 허용/Z 해제, 마지막 쓰기 데이터, STOP/정지 클록 PLL loss를 포함한다.
- SD 설치/복원: 합성 SD의 실제 파일시스템12시험 통과. 중단 복구, 기존 파일 보존,
  손상·외부 변경 거부를 포함한다. 실제 SD 카드에는 쓰지 않았다.
- 기존 Mk.III HDL의 OE/DIR/IRQ 극성 확인. 036과 동일 FPGA 바이트,035와 동일 MCU 바이트다.
- 036 full fit/내부STA/ASM/실제MCU decoder 및034 Mesen 참고 이미지는 재사용했다.
  이번에 다시 빌드·Mesen 실행·실기 검증했다고 주장하지 않는다.

ZIP SHA-256: 72fd83a8b300a79762dfb0c7fba53ce0b10201795ded9eea83d27bb107b2c719

설치 도구는 기존 C44 firmware/GBC를 확인하고 변경될 세 파일을 SD 밖에 백업한 뒤 쓴다.
원본 base/GBC 이미지·메뉴·게임·세이브는 교체하지 않는다. 실제 화면 제목은 **NES H1 034**다.
복원은 원본 파일 해시를 검증하고 새로 추가했던 H1 파일만 제거한다.

38입력/11출력 미제약, 실물 부품 지연·CPU/DMA 최소 setup/hold·turnaround는 여전히 미확인이다.
임의 SDC나 false-path로 이를 지우지 않았다. 패키지 준비 완료는 전기적 signoff가 아니다.
기존 정상 대상에서 짧은 복구 가능한 시험을 하고, 실패 단계/영상으로 다음 수정 구간을 정한다.
현재 H1 hardware_executed=false. H0의 제한된 육안 통과만 기존대로 유지한다.

기록된 최초 실패는 추가 시험대 신호 선언 순서 오류다. 첫 driver/컴파일 로그를 보존했다.
반복시험 로그의 full_64KiB CASE 이름은 원본에서 물려받은 이름이며 실제 반복은512바이트다.
036에서 이미 검사한 전체64KiB 결과와 혼동하지 않는다.

GBC C44 소스152개와 기존034/035/036 구현·검증 기록은 보존한다. 계획의 오래된 H1=031 항목도
현재037로 맞췄다. NES 실제 게임/외부 메모리/오디오·DMC 문제와032 자원 여유40LAB는 별도다.

완료 검사 중 Windows Git의 safe.directory 역슬래시 표기와 .gitignore CRLF 저장 문제를
발견해 명령별 경로를 slash로 정규화하고 .gitignore를 기존 LF로 복원했다.
오류 원문은 보존했고 최종 diff --check와 보호 경로/원본201항목 검사는 통과했다.
