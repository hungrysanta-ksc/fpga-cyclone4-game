# NES 현재 인계 —141 실행·메뉴 통과, 화면 관찰 대기

**최신 실기 판정:** ROM 오류0/RUN·STOP·자동 메뉴 복귀·TXT 성공. 사용자는 진단 화면을 관찰하지 못했다. [실기 결과](../../analysis/SCREEN141-HARDWARE-RESULT.ko.md)를 아래 제작 시점의 실기 대기 문구보다 우선한다.

같은141을 화면 관찰 목적으로 한 번만 재실행한다. 약8분30초부터 대기하고 진단 그림의 정상/검정/깨짐과 메뉴 복귀를 확인한다. 사진/짧은 영상 권장. 새 펌웨어·무변경 빌드·044/GBC 복원 반복은 필요 없다. 정상 화면 확인 뒤 패드·SMB3 mapper4/384KiB·오디오로 진행한다.

[결과](../../analysis/SCREEN141-RESULT.ko.md) · [실행 안내](../../docs/nes-screen141-instructions.ko.md) · [검증 메타](../../analysis/screen141-verification.json)

141을 한 번 실행해 두 TXT, 진단 화면, 자동 메뉴 복귀를 확인한다. 같은044/GBC 복원 시험은 반복하지 않는다. 실패하면 최초 context와 실패 경계를 비교하고, 성공하면 패드 입력과 SMB3 mapper4/384KiB 연결로 진행한다.

## 메뉴 복귀 변경

마지막 TXT 저장에 설정한 1,000tick/10,000poll 대기 예산이 저장을 마친 뒤에도 남아 있었다.141은 진입 전 메뉴 예산의 활성 여부·남은 poll·시작 시각을 보관하고 저장 종료 때 그대로 복원한다. 시작 시각을 갱신하거나 오류를 지우지 않는다. 실제 MCU 소스와 추출한 main을 사용한21개 호스트 사례가 통과했다. 마지막 저장 뒤 추가20,000poll을 수행하는 사례20은 기존140의 nes_menu_return.c만 되돌리면 실패한다. 이 비교는 코드 결함을 입증하지만 실기 검은 화면의 유일한 원인이라는 뜻은 아니다.

## ROM 경로 변경

- 선택한 매퍼 어댑터는 cart_ce(div10)에서 ROM 데이터를 소비하지 않는다. 검사 시점을 마지막 open-bus 입력 캡처(div11)와 실제 CPU/DMA 소비(div12)로 맞췄다. 실제 CPU·PPU 클록은 바꾸지 않았다. cart_ce에서 ROM을 쓰는 미래 매퍼에는 이 예외를 그대로 적용하면 안 된다.
- RUN 완료 ACK를 HOLD에서 데이터 캡처 에지로 옮겼다. READ16/168MHz의95.232ns, 캡처 뒤 한 메모리 클록의 CE/OE 유지,2단 동기화와 CHECK 완료 위치는 그대로다.
- CPU8바이트 직접 매핑 캐시와 PPU2바이트 캐시로 반복되는 ROM 접근을 재사용한다. 검증된 응답만 저장하며 주소 태그·리셋 무효화·태그 충돌·범위 밖 접근을 검사한다. 현재 불변 PRG64KiB/CHR32KiB 범위다. SMB3의384KiB 확장과 CHR-RAM 쓰기에 대한 캐시 정책은 아직 구현하지 않았다.

## 확인한 결과와 한계

캐시74검사, 경계12위상, 실제 코어3위상에서각각67.161ms 및 실제 CPU 읽기/최종 버스 캡처각99,641회를 확인했다.3개 완전 프레임은각61,440픽셀이고 기존 정상 모델의 프레임과 바이트 단위로 같았다. 실제 SPI START/STOP 및 STOP 후 버스 격리도 통과했다.80KiB 적재를 다시 실행한 시험은 아니며 기존 적재 근거를 재사용했다.

전체 코어의 요청5ns/ACK12ns는 배치의 해당 첫 동기화 입력 data-minus-skew 최대3.729/4.359ns보다 큰 디지털 지연 조건이다. **ACK16ns 확장 스트레스에서는 여전히 PPU deadline 오류가 발생한다**(55.822ms,샘플165488). 이 실패는 보존했다.12ns 통과를 모든 지연·메타안정성·실기 성공으로 일반화하지 않는다. CPU 검사 시점만 변경한 후보, ACK까지 바꾼 후보, PPU 캐시만 추가한 후보의 실패도 남겼다.

reader16위상에서8,400읽기/208취소와 주소·데이터 CDC 및 setup/hold를 검사했고,110ns 메모리와 sample HOLD 제거 반례는 거부했다. ARM186,468바이트, 강한 NMI 벡터/15store/3DSB/2ISB 및 호스트와 실제 MCU 소스 일치를 확인했다.

선택fit05는13,790LE/924LAB/5,359레지스터/50M9K/PLL1/실제122핀이다. 같은 클록 setup+0.087ns/hold+0.146ns,419개 held-data 쌍과17동기화 체인을 확인했다. PSRAM 읽기 여유+2.639ns는70ns 부품·setup등2ns·PCB왕복2ns 가정의 조건부 계산이다. 보드 실측이나 전체 IO 승인,MTBF 계산을 의미하지 않는다. E1/E2·8µs·양클록정지 CE9µs·source-lock4·124격리를 유지한다.

## 다음 실기와 작업 의미

[실행 안내](../docs/nes-screen141-instructions.ko.md)의 NES SCREEN 141.nh1을 한 번 실행한다. 적재·대조약9분,이후약10초 진단 표시와 자동 메뉴 복귀가 목표다. 두 TXT와 화면·메뉴 관찰을 받는다. MENU_PREPARED는 마지막 SD 기록일 뿐 실제 RESET 해제·메뉴 표시의 증거는 아니다. 동일044/GBC 복원 시험은 사용자 요청에 따라 반복하지 않는다.

이번 변경은 실제 코어의 ROM 공급 경로와 MCU 메뉴 복귀를 수정한 작업이다. 일반 디버그 프레임워크 확장이 아니다. 첫 게임 SMB3(J),mapper4/PRG256KiB+CHR128KiB 목표는 유지한다. 정상 화면 확인 뒤 패드·실제 게임 연결·오디오 순으로 진행한다.


## 재개 시 필수 확인

선택 fit05/arm01/armcheck02/host04/core06/reader01/inventory05/sta05/io05/asm05/release01. 동결 evidence 내부는 역할명 fit/arm/armcheck/host/core/reader/inventory/sta/io/asm/release로 저장했다. 원본 시도 번호는 메타 selected에 있다. core06의140 대조 로그는 core03에서 재사용했으며 생산 소스 차이는 cache service뿐이고 LEGACY=1/CAPTURE=0으로 나머지 두 변경을 끈 대조다.16ns 실패를 없애거나12ns 통과를 전체 타이밍 승인으로 쓰지 않는다. 공개 core driver는 같은 시험의 휴대 가능한 재생 도구이며 이미 완료한 전체 시험을 이유 없이 반복하지 않는다.

141 이번 실기에서 사용자 자동 메뉴 복귀를 확인했다. 정상 영상은 미관찰이므로 별도로 판정한다. PREPARED 이후 UART 전용 보고를 TXT 누락 실패로 혼동하지 않는다. 변하지 않은044 복원은 요청하지 않는다. 실기와PC 연결은 어렵다. SD 패키지→사용자 실기→TXT 회수 방식, 영상은선택이다.

SMB3(J) SHA dbb1cb5e18b091ca9101b1c2f5a5d6bdbeaa4a30ae1a504251310f6765cabb49. GBC152/원래NES334 및 모든 과거 public pin 보존. 부품은 사용자 사진의 FXPAK Pro Mk.III Rev.D/2022-05-02,STM32F401RCT6,EP4CE15F17C8N,PSRAM IS66WVE4M16EBLL-70BLI 두 개를 기준으로 한다. 다시 제품명/속도를 묻지 않는다.

Questa는 기존 FLOAT wrapper와1seat를 재사용한다. uncounted Terminal Services 실패경로/새 유료 라이선스 요구를 반복하지 않는다. 한 번에 한 작업. Git에는 ROM/펌웨어/FPGA 바이너리/미디어/라이선스/개인경로를 넣지 않는다. PR은 한국어 제목과 작업 목표·작업 내용·작업 결과·작업 의미4절, 사용자가머지한다.
