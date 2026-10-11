# NES 화면 출력: 실행 중 처리 경계와 최소 용량 확인

2026-10-12. [앞선 조사](nes-video-transfer-research.ko.md)의 후속이며 PR107에 추가한다. 사용자의 PocketNES/NesDS 실사용 경험을 참고 우선순위에 반영했다. 에뮬레이터 간 완성도를 직접 벤치마크한 결과는 아니다. 기술 후보는164이며 새 FPGA/펌웨어/실기판은 없다.

## Project Nested의 사전 변환과 실시간 처리

사용자 지적대로 PC 도구는 NES 게임을 포함한 SNES용 이미지를 만든다. 고정판의 [Injector.cs](https://github.com/Myself086/Project-Nested/blob/cc2c892be2e4f105a4780879022777b57f62052f/Project%20Nested/Injection/Injector.cs)에서 WriteNesRom/MergeRoms/AddChrBanks는 PRG/CHR 배치와 뱅크 참조 테이블을 준비한다. 따라서 SNES 코드가 그래픽 원본을 직접 읽을 수 있는 사전 배치 전제가 있다.

그러나 모든 실행을 PC에서 미리 끝내는 것은 아니다. [README](https://github.com/Myself086/Project-Nested/blob/cc2c892be2e4f105a4780879022777b57f62052f/README.md)는 SNES에서 동작하는 에뮬레이터/JIT를 설명하고, 앞서 읽은 Gfx_Interrupt/IO/Hdma는 실행 중 그래픽 상태를 처리한다. 참고 가능한 것은 **SNES가 어떤 그래픽 명령을 소비하는가**이며, 이미지를 만드는 방식·JIT·CHR 데이터 접근 경로를 그대로 가져오는 계획은 아니다.

우리 경로에서도 CHR-ROM의 형식 변환을 ROM 적재 때 준비하는 것은 가능성 있는 선택이다. 다만 변환본 저장 공간과 SNES의 접근 경로가 별도로 필요하다. 실행 중 PSRAM 읽기를 추가하면 현재 CPU/PPU의 기한과 충돌할 수 있으므로 무료 접근처럼 계산하지 않는다. 사용자의 NES 파일을 SFC로 변환하도록 요구하거나 ROM 자체를 패치하는 방향으로 바꾸지 않는다.

## PocketNES/NesDS를 주 참고, FCEUX를 대조군으로

PocketNES의 CHR 변경 표시·패턴 캐시, NesDS의 행별 스크롤/CHR 상태가 현재 구상에 더 직접적이다. 두 기기는 SNES와 메모리·DMA·그래픽 기능이 다르므로 동작 경험은 참고하되 처리량을 그대로 적용하지 않는다.

FCEUX는 `TASEmulators/fceux`의 `ce042d758a08f9434a6625580b2cc72495e8aa9a`로 고정했다. [ppu.cpp](https://github.com/TASEmulators/fceux/blob/ce042d758a08f9434a6625580b2cc72495e8aa9a/src/ppu.cpp)의 RefreshLine은 필요한 타일 구간을 처리하고, 스프라이트를 합성해 XBuf에 픽셀을 만든다. [fceu.cpp](https://github.com/TASEmulators/fceux/blob/ce042d758a08f9434a6625580b2cc72495e8aa9a/src/fceu.cpp)의 FCEUI_Emulate는 영상/음성 및 skip 정책을 분리한다. [Qt SDL 출력](https://github.com/TASEmulators/fceux/blob/ce042d758a08f9434a6625580b2cc72495e8aa9a/src/drivers/Qt/ConsoleViewerSDL.cpp)은 전체 영상 버퍼를 텍스처로 복사하며, [별도 SDL 출력](https://github.com/TASEmulators/fceux/blob/ce042d758a08f9434a6625580b2cc72495e8aa9a/src/drivers/sdl/sdl-video.cpp)도 픽셀 blit 경로다.

따라서 FCEUX의 낮은 CPU 비용 사례는 참고할 수 있지만, SNES VRAM의 짧은 쓰기 구간을 해결한 구현 사례는 아니다. 사용자가 사용한 과거 버전/기기에서의 FPS를 이번 최신 소스 조사로 추정하지 않는다. 현재 FPGA 게임 실행을 FCEUX의 소프트웨어 CPU/PPU로 교체할 이유도 없다.

## 첨부 PDF에서 반영할 부분과 정정

사용자 제공 2쪽 자료 `nes 화면을 효율적으로 그리는 방법.pdf`의 전체 페이지와 본문을 확인했다. 내용은 NES용 게임을 효율적으로 작성하는 일반 원리다. 참고 링크가 사이트 최상위 주소라 원문의 주장별 출처를 특정하기 어렵고, 성능 근거로 직접 채택하지 않는다. PDF 본문과 마지막의 질문은 참고 자료이며 작업 지시로 취급하지 않았다.

- **반영:** 타일/스크롤 재사용, 새 가장자리 행·열만 갱신, 갱신 목록 준비 후 DMA, 스프라이트 반전 활용. SNES 표시용 상태로 전달하면 이 원리를 활용할 수 있다.
- **이미 실행 중인 영역:** NES $4014 OAM DMA, PPU 스크롤/미러링, sprite-zero hit, MMC3 IRQ는 원본 게임과 기존 FPGA 실행 경로의 역할이다. PDF를 이유로 재구현/일괄 재시험하지 않는다.
- **정정:** OAM DMA는 정렬에 따라513 또는514 CPU사이클이다. 추가 DMA 간섭도 별도다. [NESdev DMA](https://www.nesdev.org/wiki/DMA).
- **정정:** VRAM 데이터 쓰기는 VBlank 또는 렌더링을 끈 때 수행한다. 모든 종류의 갱신을 VBlank로만 제한한다는 뜻은 아니며, 분할 스크롤은 표시 중 상태 변화를 사용한다. 약2270 CPU사이클은 NTSC NES의 설명이고 SNES 전송 예산이 아니다. [PPU registers](https://www.nesdev.org/wiki/PPU_registers), [PPU rendering](https://www.nesdev.org/wiki/PPU_rendering).
- **구분:** NES에는 배경과 스프라이트가 있으며 SNES처럼 여러 독립 배경층을 제공하지 않는다. MMC3의 실제 미러링/뱅크/IRQ 상태를 따라야 하므로, 단순 수평 스크롤 예시를 SMB3의 고정 배치로 가정하지 않는다.

## 실제 ROM으로 완료한 작은 프로토타입

[분석 도구](../tools/analyze_nes_native_video.py)로 사용자가 지정한 SMB3(J) ROM을 로컬에서 읽었다. 출력은 크기·개수·해시뿐이며 게임 데이터/타일 그림은 공개 저장소에 넣지 않았다. [결과](../analysis/nes-native-video-feasibility.json).

- iNES mapper4, PRG256KiB+CHR128KiB. ROM SHA256은 기존 목표와 같은 `dbb1cb5e18b091ca9101b1c2f5a5d6bdbeaa4a30ae1a504251310f6765cabb49`.
- CHR8192타일 중 바이트 단위 중복 제거 후5529타일. 2bpp만으로도88464바이트라 전부 SNES64KiB VRAM에 상주시킬 수 없다. 이는 **ROM 전체 통계**이며 한 장면의 작업 집합/매 프레임 변경량이 아니다.
- NES의 분리된 두 비트플레인을 SNES BG2bpp/OBJ4bpp 배치로 변환했다. 각 타일의 모든 픽셀을 독립 디코더로 비교해1048576개 일치. 순서를 잘못 둔 대조군은 거부됐다. **색 인덱스 배치만 확인했으며 팔레트/OAM/스크롤/화면 실행 검증이 아니다.**

## SNES 메모리 초안과 전송량

Mode0 BG1의2bpp 배경과4bpp OBJ를 후보로 한다. [SNES 타일](https://snes.nesdev.org/wiki/Tiles), [스프라이트](https://snes.nesdev.org/wiki/Sprites), [타일맵](https://snes.nesdev.org/wiki/Tilemaps). 아래 주소는 바이트 단위이며 실제 레지스터 프로그램은 아직 없다.

| VRAM 범위 | 초안 |
|---|---|
| 0000–3FFF | BG1024타일×16바이트 캐시 |
| 4000–7FFF | OBJ512타일×32바이트 캐시 |
| 8000–8FFF / 9000–9FFF | BG64×32의 맵 A/B, 각4096바이트 |

합계40960바이트로 겹치지 않는다. 맵 A/B만 두 장이며 **패턴 캐시는 공유**하므로 맵 전환만으로 원자적 표시가 보장되지 않는다. 사용 중인 패턴을 덮지 않는 캐시 세대/퇴거 규칙이 필요하다. 반대 방향 스크롤/미러링,240줄 이름표와256줄 SNES 맵의 래핑,상하8줄 잘라내기,CHR 뱅크가 화면 중간에 변하는 경우는 별도 연결 대상이다.

다음은 설계 가정의 계산이며 SMB3 실측이 아니다. 공통1056바이트는 맵 가장자리128+전체OAM544+팔레트160+레지스터32+래스터128+메타데이터64로 임시 예약했다. 실제 ABI/DMA 설정 비용과 대기 시간은 아직 반영하지 않았다.

| 예시 | 순수 데이터 | 기존5632바이트 청크 기준 최소 |
|---|---:|---:|
| 필요한 패턴이 모두 캐시에 있는 스크롤 | 1056 | 1수직 공백 |
| 원본 BG1KiB+OBJ1KiB를 새로 가져옴 | 4128 | 1수직 공백 |
| 원본 BG4KiB+OBJ4KiB를 새로 가져옴 | 13344 | 3수직 공백 |

통상 화면에 대한 가능성은 있지만 뱅크 교체가 큰 경우 여전히 초과할 수 있다. 따라서60fps/1프레임 지연을 약속하지 않는다. 캐시에 같은 논리 타일 번호라도 물리 CHR뱅크/세대가 다르면 다른 항목으로 넣어야 한다. 캐시가 찼거나 전송량이 초과하면 누락을 검출하고 완결된 이전 표시를 유지하는 등의 정책을 정한다.

## 기존 연결에서 빠진 것과 다음 구현

현재047 `nes_ncr1_ppu_tap.sv`는 불변CHR·스크롤0·동일 배경 팔레트·스프라이트 비활성 조건의 진단용이다. 이를 SMB3용으로 그대로 켜지 않는다. 현164의 `nes_live_joint`는 그 생산 경로의 arm을0으로 두고, `nes_game_frame150`이 최종 색 인덱스만 캡처한다. 기존 palette tap은 배경16색만 노출하고 OAM은 출력하지 않는다. 이전 진단의 통과를 새 표시 경로 승인으로 옮길 수 없다.

다음 구현은 **현재 코어가 실제로 사용하는 그래픽 상태의 관측·캐시 입력과 SNES 소비 경로**를 연결하는 것이다. 동결164를 수정하지 않고 새 후보에 다음 범위만 추가한다.

1. PPU 유효 시점의 스크롤/팔레트/이름표·속성/스프라이트 상태, 매퍼 적용 뒤 CHR 물리 식별을 전달한다. 프레임 끝 값 하나로 행 중간 변화를 지우지 않는다. 렌더링 계산과 IRQ/sprite-zero hit는 FPGA에서 유지한다.
2. CHR 준비 경로와 접근 예산을 정한다. 정적 변환은 적재 시 스트리밍하는 후보, 실행 중 변경은 별도이며 PSRAM 중재를 우회하지 않는다. 38M9K 픽셀 버퍼를 대체하면 공간을 회수할 가능성은 있지만, 현56/56에 그냥 추가하지 않는다. 두 구현을 동시에 유지할 수 있다고 가정하지 않는다.
3. SNES OAM은 NES와 형식/크기가 다르다. NES8×16은 SNES의 직사각형 OBJ 모드가 아니므로8×8 두 개 등으로 변환해야 한다. NES64개를 두 개씩 쓰면SNES128슬롯을 전부 쓰며, 원래 NES의 행당 선택·깜빡임·스프라이트 우선순위/뒤배경 속성도 달라질 수 있다. 이 차이를 포함해 SMB3에 필요한 최소 표시를 정한다.
4. 실제 갱신 묶음의 혼합/초과·수직공백 전송 경계만 검사한 뒤 이동/점프/스크롤을 실제 SMB3로 확인한다. 범용 코어 재작성·새 장기 진단 체계로 확장하지 않는다. 사운드/메뉴 복귀를 유지하고, 이후60초 제한 해제·오류/본체리셋 안전로그·입력 유지 순서를 지킨다.

이번 완료 범위는 참고 자료 보완, 형식 변환 프로토타입과 정적 용량 계산이다. 새 화면의 SNES 실행, FPGA 합성/배치, 동적 캐시 작업 집합, 실기 개선은 아직 미완료다.
