# NES 137 — 최초 RUN 실기 통과와 실제 화면 소비자 연결

136 사용자 실기에서 **80KiB 적재·전체 대조·CPU 읽기 활동·STOP·메뉴 복귀·복원**을 확인했다. 이어 실제 NES CPU/PPU가 생성한 패킷을 SNES 프로그램으로 표시하는 경로를 구현했다. 새 화면의 실기 패키지는 아직 없다. 이번137은 C의 화면 구현 진전이며 입력·오디오·SMB3 플레이 완료가 아니다.

## 실기136 판정

두 원본 TXT는 새137 증거에 보관했으며, 이전136 동결 자료는 수정하지 않았다.47개512바이트 진행 기록의 연속 번호·단계·시각을 확인했다. loaded/compared=81920, verified/end/stop/base/safe=1, 오류0이다. CPU ROM 읽기 카운터는7002→124484, STOP 뒤132438로 기록됐다. 이는 CPU의 읽기 활동이며 명령·화면·게임 정확성의 증거로 확대하지 않는다.

메뉴 준비까지491600ms(약8분12초)는 펌웨어 시각이다. RUN_NEXT→RUN_STOPPED의50ms에는 SPI·진행 기록 처리가 포함되므로 순수RUN 길이라고 부르지 않는다. 메뉴 화면 복귀와 복원은 사용자 확인을 별도로 반영했다. 이번 GBC 플레이 여부는 따로 보고되지 않았으며, 기존044 GBC 성공 근거는 유지한다.

## 구현과 확인

| 작업 | 결과와 범위 |
|---|---|
| 실제 코어→화면 패킷→물리 SNES 포트 |135 코어·70ns PSRAM 모델·실제 SPI START/STOP·044 전송 경로.3프레임6024바이트를 읽어184320 NES PPU 픽셀과 정확히 대조했다. PRG/CHR와 loaded/verified는 기존122 자료로 초기화했으며 전체 적재를 반복한 시험은 아니다. |
| 캡처 시작 조건 |초기 PPU 설정 완료 및 encoder 여유 조건으로 제한. 두 슬롯을 채운 뒤 세 번째 프레임을 보류하고 소비를40ms 늦춰도 중복 캡처·오류 없이 이어졌다. |
| SNES 소비자 |2008바이트 NCR1을 WRAM으로 받고 헤더/길이/읽기 수를 검사한다. commit 뒤 vblank에서 tile map·오른쪽 한 열·palette·fine-X를 갱신한다. 고정16KiB CHR atlas이며 패드·오디오는 없다. |
| 실제65816/PPU/DMA 실행 |새 RTL이 생성한3패킷을 Mesen의 명시적 MMIO 모델로 공급했다.3장의256×239 표시,183552픽셀 모두 일치했다. 이는 순차 비교이며 RTL과 에뮬레이터를 동시에 연결한 co-simulation은 아니다. |
| 표시 기한·오류 |vblank 여유32060/11622/11644 SNES master clocks. 첫 화면은SETINI 적용 전225행 vblank, 다음부터240행이다. 잘못된 길이/헤더는 화면 DMA와commit 전에 차단했다. |
| 소비자 ROM 결선 |24KiB compact ROM을 통해 LoROM 전체65536바이트(코드·atlas·vector·빈 영역)를 실제 RTL에서 대조했다. reset/STOP과 raw read release의 출력 차단도 통과했다. |
| 새 물리 배치 |13592LE,924/963LAB,5122registers,50/56M9K,PLL1,122실핀/0가상핀. 같은 클록 setup 최소+0.060ns,hold+0.176ns. raw setup−6.600ns 및 새 CDC/reset/외부 I/O는 별도 미완료다. |

첫 배치fit01에서 load_valid→loaded_bytes 경로가−0.157ns로 실패했다. 바이트 수 clear/advance 조건을 상태·오류 전이와 분리하고fit03에서 해결했다. 동작 지연·write pulse 변경은 없다. 기존135 대비26112개 상태/명령/길이/오류/카운터 조합이 일치하고 잘못된 증가량 대조군은 실패했다. 전체 코어 영상 시험test01과fit03은 이 counter 변경만 다르며 다른 컴파일 입력은 같다. 새로운 최종 배치를 통째로 다시 기능 검증한 것으로 표현하지 않는다.

## 남은 작업과 다음 산출물

다음은 **이 화면 경로를 실행하는 제한 실기 패키지**다.136의 owner094는 SNES RESET 유지가 필수이므로 단순히 reset만 풀면 보호 경로가 실패한다. 표시 상태 전용 소유권을 만들고 진입·종료·고장 후 reset 재유지 및 기존CSS/NMI/shared-fault 차단을 유지해야 한다. RUN 중 SD 쓰기는 추가하지 않는다. 정상 종료는 STOP→base→menu→044 복원으로 연결한다.

현재137 셸은59/D4를 그대로 유지한 내부 구현 시험본이며 ARM/ASM/압축/SD 패키지를 만들지 않았다.136 firmware와 섞어 설치하지 않는다. 다음 실기 쌍에는 화면용 식별을 명시하고 단일 식별만 허용한다. SNES 활성 입력/출력·PSRAM 경로의 새 배치 지연과 필요한 CDC/reset 영향만 확인한다. 전면적인 디버그 체계 확장을 선행 조건으로 삼지 않는다.

첫 화면은 제한된 fine-X 진단과239행 표시 정책이다. 패드 입력,240행 제품 정책,일반 PPU 모드,오디오,SMB3의384KiB 적재·mapper4·플레이는 남아 있다. 기존 코어 내부의 제한 MMC3 진단을 SMB3 제품 지원으로 해석하지 않는다. E1/E2·MTBF·8µs/양클록 정지 CE9µs 반례,source-lock 보류4건,124 자료 격리도 유지한다.

## 재현과 보존

`nes_screen137.py --baseline <private probes> --out <fresh ASCII> --quartus-bin <Quartus>`가 고정135/122 자료를 확인하고 새 후보를 만든다. `test_nes_screen137.py`, `test_nes_screen137_counter.py`, `test_nes_screen137_bus.py`는 기존 FLOAT wrapper의RunOnly 실제 job으로 실행한다. 소비자는 `test_nes_screen137_client.py`의normal/bad_length/bad_header로 검사한다. 개인Mesen portable 복사본과 해당.NET runtime을 사용하며 Lua 파일 접근은 저장하지 않는 실행 옵션으로만 켠다.

완료 자료는 `verify_nes_screen137.py --evidence <frozen137>`로 읽기 전용 검사한다. [검증 메타](screen137-verification.json) · [현재 인계](../cores/nes/HANDOFF.ko.md). 이전 동결044–136과 실패fit01/준비assert/client 환경·검증기 실패는 보존했다. GBC 및 원래NES 소스에는 변경이 없다.
