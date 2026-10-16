# NES209 이후 60fps 가능성 회고와 수정 계획

2026-10-17. 사용자 요청에 따라 **스크롤 구현을 더 하기 전에 회고**했다. PR117 머지 `ef75c54f1be951268f15fdf0f550401e4c40daa1` 기준이다. 새 펌웨어·FPGA·실기판을 만들지 않았다. [계산과 소스 근거](../analysis/nes-60fps-retrospective209.json), [209 실기 결과](nes-game209-hardware01.ko.md).

## 판단과 작업 의미

**SMB3/MMC3의 지속 스크롤을 약60fps로 표시하는 목표는 조건부로 계속 추구할 가치가 있다. 그러나 아직 실현 가능성이 입증된 것은 아니며, 현재209의 매 화면 재구성과 직렬 전송을 조금씩 빠르게 하는 것만으로 달성한다고 볼 근거도 없다.** 모든 NES 게임/MMC4/MMC5/CHR-RAM의 모든 장면을 무손실60fps로 보장하는 것은 별도이며 현재 자료로 약속할 수 없다.

처음 조사에서 가능하다고 본 근거는 NES의 CHR 패턴을 계속 재사용하고, SNES에는 변경 패턴·타일맵 가장자리·스크롤·OAM 위주로 보낸다는 조건이었다. [초기 타당성 문서](nes-native-video-feasibility.ko.md)도 캐시 히트 스크롤과 큰 뱅크 변경을 구분했다. 단순히 FPGA에서 NES가 실행되고 타일 DMA가 가능하면60fps라는 뜻이 아니었다. **그 성능 전제의 생산 구현과 실제 스크롤 검증을 뒤로 미룬 것이 이번 회고에서 수정할 핵심이다.**

188–209의 직접 aperture/DMA·immutable lease·epoch·취소·표시ACK 작업은 버릴 작업이 아니다. 실제209에서 소리·조작을 유지하며205회 표시 완료를 확인했다. 다만 전송 경로의 기능 완성과60fps 구조의 완성은 다르다. 향후 작업은 또 다른 범용 진단 체계보다 실제 스크롤에서 재사용과 단계별 처리량이 성립하는지에 집중한다.

## 현재까지 된 것과 미완료인 것

| 항목 | 현재 상태 | 다음 판단에 주는 의미 |
|---|---|---|
| NES 실행·사운드·조작 |209 사용자 정상 보고 | 우선 화면 소비 경로에 집중. 매퍼 기능을 무작정 다시 작성하지 않음 |
| 픽셀의 MCU 왕복 제거 |203 metadata ingress +209 직접 타일 DMA 실기 동작 | 유지할 기반 |
| 변경량 절감 |map COPY/RLE, SNES WRAM 비교, 묶음 SPI, 짧은 계획 형식 구현됨 | 최적화가 전혀 없는 것은 아님 |
| 프레임 간 패턴·출력 슬롯 재사용 |미구현.191 planner가 매번 BG/OBJ 슬롯 재배정 | 원본 타일이 같아도 계획/생성/전송 및 맵 번호 변경 발생 가능 |
| 원본 CHR 캐시 |192의16B 한 타일 캐시 | 전체 working set/VRAM 패턴 캐시와 다름 |
| 수집과 출력 중첩 |201은 이전 표시 lease 동안 다음 캡처 가능 | C의 receive→plan→finish→seal→retire는 직렬. 전체 파이프라인 완료가 아님 |
| SNES 비용 절감 |동일 블록 비교 가속 및 차분 DMA 있음 | 그래도 매 후보를 SNES에서 다시 비교하며 큰 변경은 여러 VBlank에 걸침 |
| 실제 지속 스크롤 측정 |209 체감·전체 누적 로그 있음 | scene별 ingress/plan/map/cache miss/차분 CPU/은행 재구축 빈도는 없음 |
| 확장 여유 |207 여유148LE/1LAB/9M9K, ARM9260B | 대규모 캐시·계측·매퍼 추가를 무료로 계산할 수 없음 |

209의205표시/60.06초는 전체 평균3.41회/초, 완료 간격 약293ms다. 약16.67ms 목표와는 평균 기준17.6배 차이가 있다. 이는 스크롤 순간 FPS나 CPU만의 속도 차이가 아니다. 받는 시간을 완전히 없앤다고 가정하고 나머지 작업을 고정해도 약4.30완료/초에 불과하다. 특정 한 단계의10~20% 개선을 계속하는 방식으로 해결될 규모가 아니다.

## 놓치거나 충분히 해결하지 못한 제한

### 1. 같은 SPI에 남아 있는 모든 일을 합산해야 한다

현재2.625MHz SPI는 약60Hz 한 구간에 이상적으로5,468.75 clocked bytes만 보낼 수 있다. TX와RX를 이중 합산한 값이 아니며, 실제 상태조회·헤더·CS간격·MCU 처리 여유는 여기서 더 빠진다. geometry 수신, tile plan 송신, map/palette/OAM/HDMA 송신, 상태/ACK가 같은 예산을 쓴다. 직접 aperture의 픽셀 전송은 별도지만 나머지는 SPI에 남아 있다.

- 조건 예시: 일반BG512개와 END의 짧은 계획3,587B만10.93ms다.
- 조건 예시: map4,096B를 문자 그대로 보내면12.48ms다. 위 계획과 합치면23.41ms로 이미 한 구간을 넘는다. COPY/RLE가 효과적인 장면에는 이 예시를 적용하지 않는다.
- ingress도 프레임 간 delta가 아니다. 29group×33cell이 모두 반복 압축되지 않는 경우 map record만5,742B/17.50ms다. raster/object/프로토콜 비용은 별도다. **출력 타일 캐시만 추가해도 이 입력 병목이 남을 수 있다.** 이는 최악 조건 계산이며 실제209 스크롤의 바이트 수를 측정한 결과는 아니다.

따라서 geometry의 변화량/행 재사용, 안정된 패턴 참조와 맵 갱신량을 함께 줄여야 한다. 그것으로도 입력 예산이 안 맞으면 compact geometry/delta 또는 parallel ingress를 별도 후보로 비교한다. 더 빠른 SPI/CRC 제거/확인 없는 전송을 최초 해법으로 삼지 않는다.

### 2. 물리 CHR 읽기에도 독립적인 공급 한계가 있다

선택된207 RTL의 `native_fill_slot`은 `div_cpu==3`, NES scanline242..259, CPU 읽기·DMC/정지 등 안전 조건에서만 허용된다. 기존192 계산의 낙관적 상한은 `(260-242)*341*4/12 = 2046` byte reads/frame이며 실제 코어 경쟁은 더 줄인다. 읽기창 밖으로 무조건 넓히면 과거 ROM 응답·게임 정지 문제를 되돌릴 수 있다.

512개 서로 다른 원본타일8,192B를 cold 상태에서 다시 읽는다면 이 예산으로 최소5개 읽기창이 필요하다. 한 타일 캐시는 동일 타일 반복에 유리하지만 연속된 많은 고유 패턴을 프레임 간 보존하지 않는다. **같은 완성 타일의 재생성 자체를 생략하는 재사용은 SPI·PSRAM·SNES 세 구간을 동시에 줄일 수 있다.** 실제 cache miss 수와 출력 슬롯 churn을 먼저 측정한다. 초기 장면 적재 비용과 지속 스크롤 비용은 분리한다.

### 3. SNES의 비교 CPU 비용과 최종 VRAM 비용은 별개다

`nes_bulk195`는 기존 `nes_rawsteady181`/`nes_client181`을 유지한다. 타일을 직접DMA로 WRAM에 받더라도 `nes_native_local165`는 두 후보의 BG/OBJ/map 등을 다시 비교한다. 동일64B 블록 가속은 이미 있지만 여전히 데이터 전체를 읽고 비교한다. **전송 전에 이미 안 바뀐 것을 아는 정보를 최종 SNES 소비자까지 전달하지 못하는 비용**이 남아 있다. 변경 목록을 상류에서 생성해 이중 작업을 줄이는 후보가 필요하다. 단순 CRC 동일 판정만으로 다른 내용을 같다고 처리하지 않고 실제 content/base 소유권을 검증해야 한다.

현재 차분은 최대32개 DMA 명령, charged budget5,000B이며 명령당96B 상당 설정 비용을 계산한다. 작은 변경이 여러 곳으로 흩어져도 명령 수/설정 비용으로 fallback할 수 있다. raw 행 개수 전환·큰 변화·명령 초과 때는 비활성 VRAM 은행을4KiB 청크 단위로 여러 fresh VBlank에 채우고 마지막에 전환한다. **무점멸 화면 유지에는 유효하지만 이 fallback이 매 스크롤 프레임 발생하면60fps가 될 수 없다.** 실제 빈도는209 로그로 확정하지 못한다.

[SNESdev Timing](https://snes.nesdev.org/wiki/Timing)은 NTSC224줄에서 VBlank37줄, DMA8 master clocks/byte 및 refresh를 고려한 이론적 상한6,123B를 제시한다. 설정·실행 비용은 별도다. 현재5,000B를 근거 없이6,123B로 늘리지 않는다. [DMA 문서](https://snes.nesdev.org/wiki/DMA_registers)에서 카트리지→WRAM과 WRAM→PPU는 서로 다른 전송임도 확인할 수 있다. WRAM에 빨리 도착했다고 표시 완료인 것은 아니다.

예를 들어BG8,192B+map4,096B+palette512B+OAM544B를 모두 새로 쓰면13,344B라 이론적 상한으로도 최소3 VBlank다. 현재 청크/영역 분할은 더 늘릴 수 있다. 반대로 원본 패턴이 유지되고 스크롤 레지스터·새 가장자리·스프라이트 변화만 반영하면 훨씬 작은 양으로 표현할 가능성이 있다. 이 가능성을 목표 게임에서 입증해야 한다.

과거164의256×224×8bpp57,344B 경로로 돌아가면 순수DMA만21.36ms이며 실제 VRAM 갱신 가능시간은 더 짧다. 화면 전체 픽셀 복사의 원복은60fps 해법이 아니다.

### 4. 큰 메모리가 조금 생겼다는 이유로 캐시를 그냥 추가할 수 없다

ARM 여유9,260B에1024개64bit BG키8,192B만 추가하면1,068B가 남는다. 기존 최소1,024B 기준 위 여유는44B뿐이다. OBJ키·퇴거/참조표·추가stack은 계산하지 않은 상태다. 현재 bg_keys는 OBJ 검사/raw scratch로 덮어쓰므로 memset만 없애면 되는 것도 아니다. 캐시의 크기·키 압축·수명/메모리 재배치를 구체적으로 정해야 한다.

FPGA도9M9K가 남았지만148LE/1LAB뿐이며 logic/포트/배치 여유와 RAM 수는 다르다. SNES client4KiB 본문도1B만 남았다. 따라서 새dirty API를 기존 전수 비교 경로의 대체로 줄일지, 코드 배치를 바꿀지 함께 검토해야 한다. 별도 세이브 SRAM을 빌리지 않는다.

## EverDrive64에서 참고할 수 있는 것

[공식 제품 페이지](https://krikzz.com/our-products/cartridges/ed64x7.html)는 NES 지원을 명시한다. 더 중요한 [공식 변경 이력](https://krikzz.com/pub/support/everdrive-64/x-series/OS/changelist.txt)의3.07 항목은 이전 Neon 에뮬레이터를 FPGA 기반 NES 코어로 교체했다고 설명한다. 따라서 현재 X7 NES 지원을 단순 Neon64 소프트웨어 에뮬레이션으로 설명하면 잘못이다.

이번 조사에서 확인한 [NES64 배포 폴더](https://krikzz.com/pub/support/var/rc/nes64/)에는 nes.v64/readme가 있고, [Krikzz 공개 ED64 저장소](https://github.com/krikzz/ed64-x-pub)는 SD/USB 등 하드웨어 접근 예제를 설명한다. **이 범위와 공개 검색에서는 후속 NES64 코어의 이식 가능한 RTL/화면 전달 소스를 찾지 못했다.** 모든 공개 장소에 없다고 단정하지 않으며, 해당 바이너리를 역공학하거나 출처 불명 코드를 가져오지는 않았다. 공식 제품 설명만으로 사용 FPGA 자원·표시 방식·게임별60fps를 추정하지 않는다.

공개 [Neon64v2 개발 문서](https://github.com/hcs64/neon64v2/blob/master/README.md)는 이전 소프트웨어 구현이다. CPU/RSP 작업 분담,8행 묶음 전달, RDP 완료 후 VI 표시, framebuffer/FIFO 구조를 설명한다. N64의 RSP/RDP/RDRAM을 활용한 구조이므로 SNES의 VBlank VRAM 예산과 동일하지 않다. 단계별 소유권·비동기 완료·프레임 예산에 맞춘 프로파일링은 참고할 수 있지만, 그 처리량을 우리 보드에 적용할 수 없다. 문서 자체도 FIFO/팔레트 등 미완료 제한을 밝히므로 이상적인 무제약60fps 구현으로 취급하지 않는다. 후속 Krikzz 코어가 내부적으로 이 소프트웨어와 같은 표시 경로를 쓴다고 주장하지 않는다.

**N64의 성공은 카트리지 FPGA와 본체를 조합할 수 있다는 참고 사례다. FXPAK/SNES에서60fps가 보장된다는 증거는 아니다.** N64용 CPU/RSP 코드를 그대로 가져와도 현재 SPI·SNES 비교/VRAM 병목은 해결되지 않는다.

## 더 직접적인 공개 참고 자료

| 자료 | 실제 참고할 부분 | 적용 한계 |
|---|---|---|
| [PocketNES ppu.s](https://github.com/Dwedit/PocketNES/blob/main/src/ppu.s) | `dirty_tiles/dirty_rows`, `nes_chr_update/store_recent_tiles`, BG 캐시 및 생산/소비 cursor | GBA의메모리·DMA속도를 SNES에 대입하지 않음 |
| [Project Nested Gfx_Interrupt](https://github.com/Myself086/Project-Nested/blob/master/Assembly/Project/Gfx_Interrupt.asm) | Tile/Attribute/Palette/Sprite/Scroll/ChrBank 큐. 목적 기기가 SNES라 변경 명령 소비 설계에 가장 직접적 | PC 이미지 준비와 실행 중 JIT/그래픽 처리가 함께 있음. CPU JIT 이식 불필요; 범용·무손실60fps 증거 아님 |
| [NesDS](https://github.com/DS-Homebrew/NesDS), 기존 고정소스 조사 | 행별 스크롤·뱅크 변화와 하드웨어 렌더링/호환성 fallback 구분 | GBA/DS의 표시 능력 차이, 중간 행 상태를 마지막 상태 하나로 대체하면 안 됨 |
| [기존 FCEUX 대조](nes-native-video-feasibility.ko.md) | 정확성/매퍼/PPU 동작 대조 | framebuffer 출력 환경이 달라 SNES VRAM 처리량 근거가 아님 |

외부 코드는 생산 구현에 편입하지 않았다. 다음 설계의 원리는 안정된 source identity와 변경 정보 보존이며, 게임별로 미리 정한 타일 목록이나 SMB3 전용 화면 위치를 박아 넣는 해법은 아니다.

## 수정된 진행 순서와 중단 기준

1. **실제 스크롤 한 구간으로 가능성 판정:** 숫자1+A→첫 레벨→RIGHT+B 유지/A 반복으로 카메라가 계속 이동하는 구간을 대상으로 한다. 현재/후보에 같은 자료를 넣어 비교한다. scene boundary, ingest/plan/map/control clocked bytes, physical misses, 출력 slot 교체, SNES 비교 작업·fallback/VBlank 횟수, 실제 표시 간격을 필요한 최소 범위로 얻는다. 기존 보존자료에 충분한 구간이 없으면 다음판에 작은 카운터/샘플을 함께 넣는다. 플레이 중 SD 쓰기는 하지 않는다.209 로그에는 이 구분이 없으므로 기존209 반복을 요청하지 않는다.
2. **성능 전제를 먼저 작은 계산/재생으로 검증:** 현209 vs 안정된 physical-pattern slot+스크롤을 고려한 맵 재사용+상류dirty목록을 비교한다. BG/OBJ 변환·row/alt/mask·palette 의미와 화면 픽셀 동등성은 유지한다. geometry ingress가 이미 예산을 넘으면 출력캐시만 구현해 낙관하지 않는다. 대규모RTL/FIT 전에 SPI·qualified source·ARM·SNESCPU·VBlank·RAM/포트/LAB을 모두 계산한다.
3. **지속 재사용 구현:** 같은 physical CHR/content epoch와 변환key에 같은 slot을 유지하고 신규·변경 패턴만 준비한다. 맵은 동일 screen offset 비교만이 아니라 원래 좌표/스크롤·행별 mapping을 보존해 반복 전체 전송을 줄인다. 최종 SNES까지dirty목록을 전달하여 같은 자료를 전수 비교하는 작업을 줄인다. 현재 연속 bg_next/obj_next API를 그대로 두고 계획을 생략하면 안 된다. skip/reuse·길이/slot·display base/bank의 새 계약이 필요하다.
4. **처리 단계 겹침:**201의 다음 캡처를 활용하되 계획/출력 소유권은 구분한다. capture→ingress→준비→업로드→표시를 전부 직렬로 더하지 않도록 개선한다. 최종표시ACK는 유지하고 내부 credit/descriptor를 묶어 전달한다. 한 장의 지연이16.67ms를 넘더라도 파이프라인 처리량은60/s일 수 있지만, 같은 SPI/PSRAM 자원의 합산 점유는 넘길 수 없다. 충분한 frame buffer가 생겼다고 가정하지 않는다.
5. **최소 변경 경계 검사 후 실기:** 이전 화면 참조 slot 덮어쓰기/중간세대 공개/STOP·epoch 무효화만 필요한 범위로 확인한다. 실제 지속 스크롤에서 표시 간격 분포·마감 누락/반복·음성·입력을 판정한다. 평균60회라는 숫자만으로 주기적인 긴 멈춤을 합격시키지 않는다. 최초적재/장면전환과 정상스크롤은 분리하되 둘 다 기록한다.

**진행 조건:** 공유 버스 점유와 실제 핵심 작업이 약16.67ms 처리량에 들어가고, SNES VBlank 예산과 메모리/논리 여유를 함께 만족하는 설계가 나와야 다음 큰 구현으로 간다. 최소 전송량/읽기량만으로 초과하면 그 직렬 경로를 더 FIT하지 않고 데이터 재사용/형식/경로를 바꾼다. 재사용 후에도 게임 장면 작업집합이 맞지 않으면 지원 범위 또는30fps/명시적 frameskip 같은 대안을 사용자와 결정한다. 지금 목표를 임의로 낮추지는 않는다.

MMC4 latch/MMC5의 CHR·ExRAM·분할/확장속성·CHR-RAM 쓰기는 fetch시점 source identity/content를 유지해야 한다. 새로운 cache는 논리 타일 번호 하나를 key로 쓰지 않는다. 실제 game timing/IRQ는 기존코어가 유지하며 렌더러 빠른 경로가 처리하지 못하는 효과는 명시적fallback이다. 매퍼 계열별bitstream도 자원 후보이며 아직 지원 구현은 아니다. state load/reset에서base와cache를 무효화하고 sound mute/frameskip은 게임 진행과 분리한다.

유지:209 동작 기준과186/GBC164 복구 자료,세이브SRAM 비점유,최종표시ACK,사운드/입력/메뉴복구. 생략:반복044복원·pad-only·변경없는FIT·독립codec/loader검사·새wholegamecosim 체계. 회고를 스크롤 수정 뒤로 미루지 않고 **이번 판단을 스크롤 구현의 설계 조건으로 삼는다.**
