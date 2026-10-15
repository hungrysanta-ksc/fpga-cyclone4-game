# NES181 — 60fps와 MMC4·MMC5 확장 예산

2026-10-15 설계 검토. 현재1813 구현에 적용할 다음 설계 조건이며, 새로운 매퍼 구현·합성·실기 통과 기록이 아니다. 기존 완료된 검증 기록은 변경하지 않는다.

## 공통 출력과 매퍼 호환성을 구분한다

화소/타일의 무손실 묶음, 전송 CRC·세대, SNES 비표시 bank 준비와 최종 공개/ACK는 공통으로 재사용할 수 있다. 그러나 같은 NES 화면 크기라는 이유로 수집기까지 자동 호환된다고 판단하면 안 된다.

| 대상 | 확인할 차이 | 현재 구현에 요구하는 경계 |
|---|---|---|
| MMC3 / mapper4 | 현재 SMB3 실행 대상 | 기존 실제 ROM의 화면·음성·입력 동작을 유지하며 출력 속도 개선 |
| MMC4 / mapper10 | 특정 PPU pattern read가 CHR bank latch를 바꿈 | 실제 읽기 순서와 그 읽기에 적용된 bank 보존. 나중의 bank 값으로 과거 tile을 재해석하지 않음 |
| MMC5 / mapper5 | BG/OBJ bank 구분, 확장 속성·split·nametable 공급 차이 | 실제 fetch에 적용된 CHR/속성/scroll을 수집. MMC3식 bank/attribute 재구성 금지 |

MMC4 동작 근거는 [NESdev MMC4](https://www.nesdev.org/wiki/MMC4), MMC5 기능·최대 CHR 1MiB/PRG RAM 128KiB는 [NESdev MMC5](https://www.nesdev.org/wiki/MMC5)를 참고했다. 이는 매퍼의 범위이며 모든 게임이 최대 용량을 사용하는 것은 아니다. 웹 직접 열기는403이었고 검색 색인의 해당 본문으로 대조했다. 실제 구현 비교에는 [Mesen2 MMC5 소스](https://github.com/SourMesen/Mesen2/blob/master/Core/NES/Mappers/Nintendo/MMC5.h)의 BG/OBJ bank 선택, mapper RAM/nametable, IRQ와 audio 경계를 참고했다. 소스를 이식하거나 정확성 전체를 인증한 것은 아니다. 이후 구현 시 원본 revision과 라이선스를 별도로 고정한다.

MMC5의 ExRAM 1KiB는 영상 scratch와 구별해 소유권을 배정해야 한다. 확장 음원·IRQ·PRG RAM/세이브도 별도 호환성 항목이다. 화면만 정상이라고 mapper5 지원 완료로 표시하지 않는다. MMC5 전체 사양을 SMB3 개선의 선행 구현으로 만들지는 않는다.

## 현재 소스에서 확인한 실제 제한

분석 기준은 `analysis/replyjoin181-verification.json`에 해시가 고정된 보드 소스다. 로컬 `probes/nes-replyjoin181/evidence/map02`의 다음 파일을 대조했다.

- `nes_probe.sv`: `.mapper_flags(64'd4)`로 고정. 현재 실행 코어가 MMC4/5를 선택한다고 주장할 수 없다.
- `nes_native_fetch165.sv`: PPU 실제 fetch의 `physical_address`를 받는 것은 재사용할 좋은 경계다. 그러나 `physical_address[21:17]==5'h10`, tile `[16:4]`, query13bit, `required_tiles[0:8191]`로 **128KiB CHR 영역**에 제한한다. BG/OBJ를 구분하는2bit 표의 payload는2KiB다.
- `nes_native_fill165.sv`: tile/query도13bit다. fetch 한 곳의 mask만 바꾸면 나머지 경로에서 alias가 발생할 수 있다.
- 공개 `src/nes/firmware/nes_native181.h`: `required[2048]`를 CHR 검증 완료 뒤 raw scratch로 재사용하며, `tiles[512]`만 수용한다. 전체 ROM의 주소 범위와 한 장면의 사용량은 서로 다른 제한이다.
- `src/nes/firmware/nes_native_video181.h`: BG key 영역은 raw staging과 union이다. 다음 frame 차분용 영구 cache라고 가정하지 않는다.

1MiB CHR는16B tile 기준65,536개이므로 같은2bit bitmap을 그대로 확대하면16KiB가 필요하다. 현재보다 **14KiB 증가**다. ARM receiver에 그대로 추가하는 방식은 현재 여유로 불가능하다. 이 계산은 bitmap payload만의 산술이며 FPGA M9K 배치/포트 수나 전체 MMC5 필요량 측정이 아니다.

다음 설계에서 물리 CHR 식별 범위는 최소1MiB를 표현할 수 있게 고려하되, 저장량은 실제 사용 tile의 bounded working set으로 분리한다. sparse set/압축 page table/스트림 중복 제거 중 포트·지연·충돌 검사가 가능한 방식을 선택하며 아직 특정 구현을 채택하지 않는다. 512tile 한도도 NES 사양으로 고정하지 않고 지원 profile과 실제 장면에서 재평가한다.

캐시 동일성은 현재 bank 번호가 아니라 **실제 해석된 source 주소와 source 종류, 변경 가능한 CHR의 데이터 세대**를 기준으로 한다. 같은 pattern을 다른 palette/속성으로 쓰는 것은 배치/변환 key에서 구분한다. mapper가 실제 read를 관측해 바뀌는 부작용과, 화면 출력용 CHR 재조회는 분리해야 한다. reset/ROM 교체/STOP/기준 bank 상실 시 이전 key·delta를 무효화한다. 새 필드가 필요하면 wire version을 변경하며1813의13bit index를 조용히 재해석하지 않는다.

최대7raw행은 현재 후보의 제한이지 모든 NES 화면을 표현하는 보편 사양이 아니다. 지속적인 확장 속성을 전부 raw fallback으로 보내는 방식은 기능과60fps 모두 별도 검토가 필요하다. 한도 초과를 조용한 alias/오래된 화면의 무기한 유지로 숨기지 않는다.

## 자원 목표를 상향한다

아래는 **설계용 잠정 목표**이며 MMC5 합성에서 측정한 필요량이나 달성된 결과가 아니다. 실제 active-mapper profile의 통합 보고로 보정한다. 물리 칩의 용량을 늘리는 것이 아니라 공통부가 소비하는 자원을 줄여 여유를 확보한다.

| 자원 | 현재 확인 범위 | 앞으로의 목표 |
|---|---|---|
| FPGA 논리/배선 | 마지막 전체 분석 후보963/963LAB, setup−1.408ns로 미채택. packed1813 전체FIT 미실행 | 공통부+활성 매퍼 통합 뒤 LAB 약10% 이상(97개, 사용≤866) 여유를 장기 확장 목표로 관리. 숫자 충족과 별도로 실제 setup/hold·혼잡 검사 |
| FPGA RAM | 같은 후보38/56M9K, 산술18개 여유 | 화면 overlap/metadata와 활성 매퍼 RAM을 모두 포함한 뒤 최소8M9K 미할당 목표. MMC5 ExRAM1KiB는 별도 항목으로 견적. 포트/폭에 따른 실제 block 수 확인 |
| ARM RAM/stack | 기존 paired build 여유1,032B; 새 packed의 국소 호출 stack+40B, 전체 재승인 안 됨 | 최악 foreground+IRQ+library 포함 최소4KiB 여유 목표. 이전16KiB plan 복제 금지; mapper RAM을 ARM frame workspace에 떠넘기지 않음 |
| SPI/처리시간 | 2.625MHz에서60Hz당 순수 bit 한도5,468.75B. 현재 한 방향7행도11.097ms 모델 | 양방향 명령·상태·ACK 포함 전송 점유를 정상 플레이에서 frame 시간의80% 이하로 설계(약13.33ms). 남는 시간에 MCU 처리·service·변동 여유를 산정; 단순 byte 목표만으로 승인 금지 |
| 외부 메모리/저장 | 기존 배포·저장 영역 보존 | ROM/mapper PRG RAM/CHR RAM/영상 workspace 주소표를 분리. 최대128KiB PRG RAM은 향후 profile 견적 대상이며 지금 예약·구현한 것이 아님. 기존 카트리지 세이브SRAM을 scratch로 사용하지 않음 |

LAB10%/8M9K/ARM4KiB/전송80%는 서로 대체할 수 없다. RAM이 남아도 배선·포트·논리 또는 대역폭이 모자라면 실패다. 반대로 최대 CHR ROM을 모두 FPGA RAM에 둘 필요도 없다. 1KiB ExRAM 확보만으로 MMC5가 들어간다는 뜻이 아니다.

매퍼별 bitstream 선택도 후보로 남긴다. 모든 매퍼를 한 FPGA 이미지에 동시에 넣는 것을 기본 전제로 하지 않는다. 필요하면 공통 출력 ABI와 저장 분리를 유지하고 활성 매퍼만 합성한다. 다만 MMC3를 제거하고 MMC5를 넣을 때의 전체 자원·타이밍은 새로 측정해야 하며, 이 방식 자체가 MMC5 수용을 보장하지 않는다.

## 구현 순서와 승인 기준

1. 현재 다음 작업인 **MCU→SNES section/CHR 묶음·bank 기준 차분·raw steady 갱신·capture/export 겹침**을 진행한다. 변경하는 buffer마다 크기/위치/포트/수명/세대/해제 조건과 위 자원 목표 대비 잔여를 기재한다. 새 최적화에 SMB3 13bit 식별자나 화면 전체 정적 속성 가정을 추가하지 않는다. 기존 제한은 profile로 명시하고 실제 확장 시 필요한 wire/bitmap 변경 경계를 남긴다.
2. 바뀐 endpoint의 최소 검증, packed 포함 전체 ARM/FIT/IO를 거쳐 SMB3 숫자1타일→A 실기로 간다. 확장 여유 목표 달성만 기다리며 불필요한 FIT를 반복하지 않는다. 안전·타이밍 조건을 만족한 MMC3 중간 시험은 가능하지만, 여유가 부족하면 **확장 준비 미완료**를 명시한다.
3. 60fps 승인은 실제 source frame과 SNES 표시 완료의 연속 간격·누락/반복·입력/음성을 함께 본다. 정상 플레이 목표는 NTSC/SNES 실제 주기에 맞춘 약60fps(설계 환산 약16.7ms). pipeline의 일정한 frame 지연과 낮은 갱신률을 구분한다. 평균 ACK 수로 대체하지 않는다. 큰 keyframe/scene 전환의 유한 복구도 따로 기록하며 반복적인 수-frame 갱신을 정상60fps로 승인하지 않는다.
4. 공통 경로가 실기에서 안정되면 MMC4, 다음 MMC5의 구체적인 게임/기능 profile을 추가한다. latch 순서, 같은 PPU 주소의 다른 BG/OBJ source, tile별 속성·split, CHR 변경, capacity/세대 복구 등 바뀐 경계만 최소 검사하고 실기 ROM으로 확인한다. 전체 매퍼의 진단 체계를 먼저 만드는 공정은 추가하지 않는다.

우선순위는 영상 약60fps+음성 → 장기 플레이/오류·리셋 로그 → 입력 유지 품질이다. 현재1813 데이터 압축·안전정지·정답 fixture는 재사용한다. 새 firmware/FIT/ZIP/실기 결과는 이번 계획 갱신에 포함하지 않는다.

[현재 압축 구현](nes-packed181-contract.ko.md) · [종단 성능 예산](nes-cadence181-contract.ko.md) · [인계](../cores/nes/HANDOFF.ko.md)
