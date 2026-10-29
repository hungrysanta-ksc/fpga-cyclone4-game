# NES480: 실제 게임 source·타일 ROM·65816 표시 연결

**실기 후속 판정: 표시 시작 실패.** 정확한 ROM 적재·검증·START와 STOP·메뉴 복귀는 정상이었으나 SNES client boot timeout으로 비용 측정 전 종료했다. 이 전달본의 재시험은 권고하지 않는다. 아래는 당시 기능 시험의 범위이며 실물 부팅 성공을 뜻하지 않는다. [실기480 분석·481 보류](nes-mmc481-startup.ko.md).

**479의 전용 ID79와 엄격 SMB3 로더를 유지하고 live 입력→tile plan/query→실제 ROM→staging→65816 DMA/독립 검사→최종ACK/EA→STOP 경로를 한 실행에 연결했다.** 기능·독립 픽셀 관문을 통과해 제한된 실기 비교본을 준비했다. 실기 게임 FPS/60fps·전 게임 호환성은 아직 미확인이다. [검증 JSON](../analysis/mmc480-verification.json) · [설치·원복](nes-mmc480-trial.ko.md).

## 실제로 확인한 경계

- 기존 host2232 encoder를 입력으로 쓰지 않고 같은 MMC3/core/source RTL이 만드는 packet을 실제 SPI로 받았다. 현재 ARM479 C의 receiver·planner·serializer·4credit·plan 공급·진행 응답 검사를 host에서 실행했다. FPGA가 실제 타일 ROM을 읽으며 NES CPU/PPU ROM 요청과 같은 중재 경로를 사용했다.
- SNES는 실제65816 프로그램을 Mesen에서 실행했다. queue/descriptor·staging 소비·token/receipt·독립 CRC/coverage·SEAL·VBlank·최종ACK/EA를 유지했다. 같은 run136가 START·표시·STOP·retained observer를 확인했고 STOP 뒤 lease·SPI·sink·ROM fault와 버스 해제 조건을 검사했다.
- 65816 실행 이미지와 FPGA boot ROM의 코드0..4031B, mapped 마지막64B header/vector가 byte 동일하다. 단순히 같은 프로그램 이름이라고 가정하지 않았다.
- ROM과 loaded/verified 상태는 seed, native startup GPIO/console setup·service/ticks는 모델이다. 실제 전체384KiB loader/물리 base/menu 재실행은 반복하지 않았다. 변경 없는479의 실제 C/FatFS/programmer/run13620건 근거를 유지한다.

| 결과 | 값 |
|---|---:|
| 표시 commit / ACK | 1 / 34 |
| 실제 staging consume | 2 |
| VRAM DMA bytes / 명령 | 4416 / 3 |
| 최대 단일 DMA | 256B |
| live source 입력 | 15packet / 3206payloadB / generation12 |
| 실제 NES PPU → 실제 SNES 화면 | **57344픽셀 동일, 차이0** |
| 해당 live 입력의 linked480 M4 | 수신288231·계획330833명령,40B tile plan18개 |

부팅 중 도입부 한 캡처다. 월드맵·1-1·큰 sprite/CHR bank/IRQ 부하나 연속 입력·capture 무손실을 증명하지 않는다. transaction RPC는 공통 실시간 스케줄러가 아니며 host C를 실제 M4 cycles/IRQ 비용으로 보지 않는다.235.17ms 모델 종료 시각에는 부팅 대기가 포함되므로 게임 FPS·steady 처리 시간으로 환산하지 않는다.

## 독립 픽셀 검사와 첫 실패의 원인

테스트 전용 관찰기가 변환 전 실제 NES PPU의 최종6bit color를 기록했다. ARM 출력 map/plan으로 golden을 만들지 않았다. SNES screenshot의 RGB8 상위5bit를 `native_palette165`의RGB15와 비교했다. 전체224×256픽셀과 위7/아래8줄 검정 여백을 검사했다.

처음에는239줄 screenshot의0행을224줄 화면의0행으로 잘못 비교해18115픽셀 차이가 났다. [Mesen SnesPpu::ApplyHiResMode/SendFrame](https://github.com/SourMesen/Mesen2/blob/master/Core/SNES/SnesPpu.cpp#L1319)는224줄을239줄 버퍼 중앙에 배치하고 위7/아래8줄을 비운다. 이 고정 좌표 계약을 적용한 pixels02는57344개 전부 동일하다. 진단용 offset 탐색 자료를 보존했으며 최종 비교 기준은 Mesen 구현의 고정 여백으로 정했다. 허용오차를 두거나 NES 일부 픽셀을 제외하지 않았다. 비교 규칙만 고쳤으며 RTL/ARM 좌표·색 변환은 바꾸지 않았다. pixels01과 진단 offset 자료는 보존했다.

생성 Python 어댑터의 두 구문 오류도 RTL 실행 전 실패로 보존했다. prepare-only 검사를 추가하고 실제 float03 연결 시험을 통과했다. 기존 Starter FLOAT1좌석을 순차 사용했으며 추가 라이선스는 필요하지 않았다.

## 전달본과 비용

480은479의 menu/checkpoint 문자열·경로만 바꿨다.75object의 SHF_ALLOC 영역이 동일하고 변경2개는 해당 label이다. 실제 live SPI에서 추출·CRC 검사한15packet을 새 linked480 M4에 재생해 기존476과 전체 상태·40B plan이 같음을 확인했다.

| 항목 | 선택값 |
|---|---|
| ARM | text202313/data10040/BSS18552, firmware212356B·Flash 산술 후미636B |
| RUN workspace | 31848B 그대로, full nested/IRQ stack proof 없음 |
| FPGA | 같은479 FIT15260LE/14069comb/8387FF/256608bits,148LE 잔여 |
| 관련 timing | implementation setup+0.235/hold+0.154ns; nominal+0.404/+0.154ns |
| 미완료 timing | raw setup−6.482/recovery−8.794ns·전체 reset/CDC/IO |
| 조립 | 같은 fitted DB의 ASM/CPF·RBF↔BI3 roundtrip, 새 MAP/FIT 없음 |

공개 Git에는 도구/해시/집계만 넣는다. ROM·PPU/RGB·raw trace·펌웨어/bitstream/ZIP는 로컬 비공개 시험 자료다. upstream 공개 소스/라이선스 hold와 제품 공개 승인은 그대로 남는다. 실기 대상으로 승인한 현재 보드에서만 비교하며 공개 제품 릴리스를 만들지 않는다.

다음은 [MMC480 실기 설치](nes-mmc480-trial.ko.md) 후 새3TXT·메뉴 복귀·게임 장면을 받아 수신/계획/표시 비용과 FPS를 분석하는 것이다. NROM476 실기 평균23.84fps는 보존하며 다른 게임과 개선율로 섞지 않는다. 이후 실제 병목을 기준으로 최적화 순서를 정한다.
