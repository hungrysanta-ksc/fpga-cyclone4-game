# NES 화면 전송 방식 조사와 다음 구현 결정

2026-10-12. PR106 머지 `a467be7e1e2dc15f2e9fb83dce71330917188d5c` 이후 조사. 사용자 요청에 따라 변경 타일 구현에 앞서 공개 소스를 비교했다. **조사·최소 형식/용량 프로토타입이며 새165 RTL/펌웨어/실기 패키지는 없다.** 현재 실기 기준은 [164 결과](../analysis/GAME164-HARDWARE-RESULT.ko.md)다. 사용자 후속 의견·PDF 및 FCEUX 비교는 [적용 경계와 용량 확인](nes-native-video-feasibility.ko.md)에 반영했다. 우선순위는 PocketNES/NesDS의 실행 중 패턴 재사용, Nested의 SNES 출력 참고, FCEUX의 픽셀 경로 대조 순이다.

## 결정

**화면 좌표별 완성 픽셀의 변경 타일만 보내는 방식을 연속 화면의 주 해결책으로 채택하지 않는다. SNES의 타일·스크롤·스프라이트 기능으로 표시하는 경로를 우선 설계 후보로 선택한다.** 전자는 정지 배경에서 도움이 되지만 SMB3의 스크롤 구간에서는 전송량 감소가 보장되지 않는다. 후자는 원래 CHR 패턴을 재사용하면서 스크롤 레지스터·타일맵·스프라이트 위치만 바꿀 수 있다.

이는 구현 완료나60fps 보장이 아니다. 다음 작업에서 **SMB3에 필요한 최소 그래픽 상태를 현재 FPGA에서 꺼내고 SNES가 소비할 수 있는지**, 실제 메모리·전송 예산으로 확인한다. 가능하면 그 경로를 작은 실기판으로 연결한다. 불가능하면 구체적인 자원/표현 제약을 기록하고 픽셀 경로의 스크롤 재사용·변경 블록 전송을 차선으로 비교한다. 범용 에뮬레이터/모든 매퍼 지원을 새 선행조건으로 만들지 않는다.

CPU·PPU·APU·MMC3의 게임 실행은 기존 FPGA 코어를 유지한다. SNES에 게임 CPU를 다시 에뮬레이션하거나 Project Nested의 JIT를 이식할 필요는 없다. 바꾸려는 경계는 **실행 결과를 SNES 화면에 전달하는 부분**이다.

## 현재 병목과 변경 타일의 한계

현164는256×224의 완성 화면을 SNES Mode3 BG1 8bpp 타일로 변환한다. `tools/build_nes_game164.py`의 전송은57344바이트를5632×10+1024, 총11회 수직 공백에 나눈다. 전송을 끝낸 뒤에야 동결 프레임을 해제하며 다음 캡처 준비 대기도 있다. 검정 구간 제거는 통과했지만 정상 플레이는 끊김으로 실패했다.

| 계산 | 의미와 한계 |
|---|---|
| 32×28=896타일, 타일당64바이트 | 전체57344바이트. 출력 픽셀을 고정 좌표8×8 블록으로 나눈 경우 |
| 5632÷64=88타일, 전체의 약9.82% | 기존 최대 청크 크기 안의 순수 페이로드 상한. 변경 목록·주소 설정·짧은 DMA 반복 비용을 넣으면 실제 여유는 더 작다 |
| 전체 갱신 최소11수직 공백 | 캡처/준비 대기를 제외한 값. 텔레비전이60Hz라고 새 게임 화면도60fps가 되는 것이 아니다 |
| 6비트만 전송하면43008바이트, 같은 청크 기준 최소8회 | 상위 두 비트플레인이0이라는 사실만 활용해도 충분하지 않다. SNES는6bpp 모드가 없어 별도 배치/변환도 필요하다 |

완성 화면의 고정 좌표 비교에서는 배경이 한 픽셀만 이동해도 많은 블록이 달라질 수 있다. 캐릭터 이동은 이전 자리와 새 자리 모두, 팔레트 변경은 넓은 영역에 영향을 준다. 따라서 정지 타이틀에서 얻은 절감률을 달리는 마리오에 그대로 적용하지 않는다. 이번 조사에서는 실제 SMB3의 변경 타일 비율을 측정하지 않았다.

또한 현 경로는 프레임 소유권/동결/해제에 묶여 있다. 전송량만 줄여도 캡처 대기까지 해결됐다고 볼 수 없다. 56/56 M9K·960/963 LAB 사용 상태에서 이전 전체 화면용 FPGA 버퍼를 그냥 추가할 수 없으며,57344바이트 두 장은 SNES64KiB VRAM에도 들어가지 않는다.

## 공개 구현에서 확인한 방식

아래는2026-10-12에 읽은 고정 커밋의 소스다. 저장소 전체의 성능·호환성을 검증한 결과가 아니다.

| 구현 / 기기 | 실제 소스의 방식 | 우리에게 유효한 점 |
|---|---|---|
| [Project Nested / SNES](https://github.com/Myself086/Project-Nested/blob/cc2c892be2e4f105a4780879022777b57f62052f/Assembly/Project/Gfx_Interrupt.asm) | VRAM 큐에 Tile·Attribute·Palette·Sprite·ScrollX/Y·ChrBank 명령을 넣고 SNES VRAM/CGRAM/OAM과 HDMA로 소비한다 | **출력 기기가 같아 최우선 참고.** 완성 화면 전체 전송을 그래픽 상태 갱신으로 바꾸는 방법. 단, 이 소스도 큐 처리 전후 강제 블랭크를 사용하므로 무점멸/60fps의 증거로 쓰지 않는다 |
| [PocketNES / GBA](https://github.com/Dwedit/PocketNES/blob/9c07f3d1d2a26b957769c5cde942060cc9ea6e64/src/ppu.s), [설정](https://github.com/Dwedit/PocketNES/blob/9c07f3d1d2a26b957769c5cde942060cc9ea6e64/src/config.h) | DIRTYTILES·BG 캐시. NES CHR-RAM 쓰기에서 변경 타일/행을 표시하고 나중에 변환한 패턴을 GBA 배경/스프라이트 메모리에 반영한다 | 여기서 변경 타일은 **화면의 최종8×8 픽셀이 아니라 원본 CHR 패턴**이다. 스크롤해도 같은 패턴을 재사용하는 점이 중요하다 |
| [NesDS / Nintendo DS](https://github.com/DS-Homebrew/NesDS/blob/73b881baa7f92efef75c3bdfa8dbea1ce5ffcd9d/arm9/source/RP2C02/RP2C02.s), [소프트웨어 렌더러](https://github.com/DS-Homebrew/NesDS/blob/73b881baa7f92efef75c3bdfa8dbea1ce5ffcd9d/arm9/source/RP2C02/render.s) | 하드웨어 경로에서 CHR·BG·OBJ를 갱신하고 행별 스크롤/화면 제어 버퍼를 DMA로 전달한다. 별도 소프트웨어 렌더링 경로도 있다 | 타일 하드웨어 활용과 호환성용 픽셀 경로를 나누는 사례. 행 중간/행별 상태를 마지막 레지스터 값 하나로 대체하면 안 된다 |
| [retro-go / ESP32 계열](https://github.com/ducalex/retro-go/blob/4ced120669750ca7228fd0414211430c1d923166/components/retro-go/rg_display.c), [NES 루프](https://github.com/ducalex/retro-go/blob/4ced120669750ca7228fd0414211430c1d923166/retro-core/main/main_nes.c) | 부분 갱신 설정 시 변환한 출력 행의 해시를 비교하고 변경된 블록만 LCD에 보낸다. NES 루프는 음성으로 진행 속도를 맞추며 늦으면 영상 프레임을 건너뛴다 | 최종 픽셀 차분도 실제 사용된다. 그러나 LCD 전송 경로이며 SNES VRAM의 수직 공백 제한과 다르다. 스크롤 시 절감/매 프레임 출력 보장 사례가 아니다 |
| [Espressif esp32-nesemu](https://github.com/espressif/esp32-nesemu/blob/693e378643dd4810665e52c0ec02bd9f64559c50/components/nofrendo-esp32/video_audio.c), [LCD 전송](https://github.com/espressif/esp32-nesemu/blob/693e378643dd4810665e52c0ec02bd9f64559c50/components/nofrendo-esp32/spi_lcd.c) | Nofrendo의 픽셀 버퍼를 큐로 다른 실행 코어의 영상 작업에 보내고 SPI LCD로 행별 전송한다. custom_blit에 dirty_rects 인자가 있지만 이 구현은 소비하지 않는다 | 렌더링/전송 분리 사례. API 인자 이름만 보고 변경 영역 최적화가 구현됐다고 오인하지 않는다 |
| [NES_MiSTer / FPGA](https://github.com/MiSTer-devel/NES_MiSTer/blob/49a0a662e244469ca77b2155746a066df704ffae/rtl/video.sv) | 코어의 색상·주사 위치를 영상 신호/색상 출력으로 연결한다 | 우리 CPU/PPU의 출처지만 SNES VRAM에 완성 화면을 복사하는 구조가 아니다. 원본 코어 속도가 FXPAK 출력 속도의 근거가 되지 않는다 |

Project Nested의 [IO 처리](https://github.com/Myself086/Project-Nested/blob/cc2c892be2e4f105a4780879022777b57f62052f/Assembly/Project/IO.asm), [HDMA](https://github.com/Myself086/Project-Nested/blob/cc2c892be2e4f105a4780879022777b57f62052f/Assembly/Project/Hdma.asm), [Mapper4](https://github.com/Myself086/Project-Nested/blob/cc2c892be2e4f105a4780879022777b57f62052f/Assembly/Project/Mappers/Mapper4.asm)도 조사 대상으로 고정했다. MMC3 구현 파일의 존재가 우리 SMB3/모든 래스터 효과의 호환성을 증명하지는 않는다. 외부 코드는 이번 변경에 복사/편입하지 않았고, 나중에 채택할 경우 해당 파일의 라이선스와 출처를 별도로 유지한다.

## 기존 GBC 경로와 비교

로컬 `src/renderer/base/build.py`에는160×144 화면의6비트플레인 타일 페이로드17280바이트를720바이트씩24번 나눠 전송하는 생성 경로와 팔레트/HDMA 메타데이터가 있다. `src/fpga/indexed_sixplane.sv` 등도 참고 대상이다. NES57344바이트보다 작지만 해상도·색 표현·표시 방식이 다르다. 이것을 NES CHR/타일맵 재사용 구현이나 새 NES 경로의 실기 성능 증명으로 취급하지 않는다. 이 base 생성기 자체가 완성 GBC 제품 전체와 동일하다고도 주장하지 않는다.

## 다음 작업의 범위와 완료 기준

1. **최소 설계:** 기존 PPU/매퍼의 실제 CHR 데이터·이름표/속성·OAM·팔레트·스크롤에서 SNES 표시용 상태를 얻는 경계를 정한다. 현재 픽셀 캡처는 최종 색 인덱스만 받으므로, 코어 기능을 바꾸지 않는 관측/전달 연결이 추가로 필요하다. ROM에서 정적 CHR만 읽는 것으로 동적 뱅크/PPU 상태를 대신하지 않는다.
2. **SMB3에 필요한 표현과 예산:** 배경+마리오 스프라이트, MMC3 CHR 뱅크 전환, 상태창 분할과 스크롤을 우선 처리한다. 프레임 끝 상태만 복사하면 중간 전환을 잃는다. NES의 sprite-zero hit·충돌/IRQ 등은 원래 PPU가 계속 계산하게 한다. SNES 모드/2bpp BG와4bpp OBJ 변환, 우선순위/팔레트 매핑, VRAM 배치, RAM/LAB 비용 및 수직 공백 전송 시간을 명시한다. NES CHR16바이트/타일이라는 원본 크기를 SNES 전송량으로 그대로 사용하지 않는다.
3. **최소 변경 검증 후 실기:** 하나의 완결된 그래픽 갱신 묶음이 잘못된 세대와 섞이지 않는지, 큐가 넘치면 검출되는지, 수직 공백을 넘기지 않는지 확인한다. 대기/전송 때문에 게임 실행·음성·입력을 멈추지 않으며 생산/소비 속도 차이도 명시한다. 작은 SMB3 실기판에서 이동·점프·스크롤·사운드·메뉴 복귀를 확인한다. 범용 진단판/모든 매퍼를 먼저 완성하지 않는다.
4. **실패 시 판단:** 네이티브 표시가 자원이나 필요한 표현에 맞지 않으면 그 원인과 수치를 남긴다. 기존 픽셀 경로의 스크롤 재사용/차분을 제한된 대안으로 비교하며, 타이틀의 높은 압축률이나 단순 프레임 스킵으로 정상 플레이 달성을 선언하지 않는다.

163 SPC/162 오디오·현재 오류 정지/메뉴 복귀를 보존하고 이전 실기 결과/동결 근거는 재작성하지 않는다. 같은164·044/GBC·사운드 전용·무변경 전체 적재를 재시험하지 않는다. 화면/소리가 실제로 조작 가능한 수준이 되면 기존 우선순위대로 **60초 제한 해제와 오류/본체 리셋 시 안전 로그 → 장시간 입력 유지**로 간다. 현재60초 제한·DOWN 유지 미확인 상태는 그대로다.

## 다른 코어에도 적용할 기준

화면 전송 최적화는 원본 기기의 최종 픽셀뿐 아니라 패턴·맵·스크롤·스프라이트의 재사용 가능성과 목적 기기의 표시 하드웨어를 함께 비교한다. 직접 LCD/HDMI 출력 성능을 SNES VRAM 전송에 대입하지 않는다. 먼저 목표 ROM의 실제 플레이 병목을 고르고, 변경 경계만 검사한 뒤 실기로 확인한다. 디버그 체계를 확장하는 일로 게임 실행을 다시 미루지 않는다.
