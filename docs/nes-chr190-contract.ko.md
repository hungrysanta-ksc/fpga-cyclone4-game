# NES190 CHR 타일 묶음 전송 후보

2026-10-16. PR117 `codex/nes-bulk-aperture-188`의 후속 구현. [189 연결](nes-source189-contract.ko.md)에서 확인한 CHR 1바이트당6바이트 전송을 줄인다. [검증 JSON](../analysis/chr190-verification.json). **배포186 유지. 새 실기 패키지는 없다.**

## 작업 의미와 결정

새 `nes_source_bulk190`는 배포 exporter/fill의 레코드를 기존 mailbox로 받고, host 도메인에서 CHR 16바이트를 타일 하나로 묶는다. 한 타일96B가22B로 줄어 CHR 부분의 전송량이77.08% 감소한다. MCU가 새 버퍼를 SPI로 채우는 방식은 쓰지 않는다. 기존188/189 소스는 비교 기준으로 그대로 두고190 후보를 별도로 둔다.

현재 생산 변환기 `nes_native_video185_build`는 단순한 NES/SNES plane 순서 변환만 하지 않는다. BG 행별 low/high plane mapping, cross-tile 예외, 슬롯 할당, OBJ 마스크·평가 순서·팔레트 epoch, raw 행, OAM·HDMA를 함께 처리한다. 따라서 **이 변환기 전체를65816에 이식하지 않는 방향**으로 진행한다. 이번에는 native NES plane 배열을 유지한 무손실 타일 묶음을 구현했다. 최종 SNES-ready 타일이나 VRAM 목적지까지 계산한 결과가 아니다.

다음 구조 후보는 MCU가 geometry에서 작은 슬롯/행 매핑 계획을 만들고 FPGA가 그 계획에 따라 CHR을 materialize해 직접 읽기창으로 공급하는 형태다. 현재 metadata 경로와 복잡한 검증을 유지하면서 대량 CHR 왕복을 제거할 수 있는지 확인한다. **아직 구현·성능 승인된 구조는 아니다.** 계획 크기/포트/원본 수명/CHR 재사용·메모리 비용이 성립하지 않으면 이 후보를 채택하지 않는다.

## 1901 형식과 수명

BEGIN의 payload version만1813→1901로 바뀐다. 기존1813 입력만 수락하며 다른 BEGIN version은 fault다. kind6 이외의 압축 geometry/raw/control 레코드는 byte 순서가 그대로다. CHR_END/END의 레코드·바이트 합계도 기존 **논리 레코드 기준**을 유지한다.

| kind6 타일 묶음 오프셋 | 내용 |
|---|---|
| 0..1 | 기존 kind6 +13bit tile tag, big endian |
| 2..3 | 원본16bit generation, big endian |
| 4 | kind1=BG,2=OBJ,3=공유. 그 외 비트0 |
| 5 | layout0 고정: NES plane0의8행, plane1의8행 |
| 6..21 | lane0..15의16바이트 |

lane0부터15까지 같은 tag/generation/kind이며 reserved bits가0인 경우만 완성 묶음을 쓴다. 16바이트 scratch는 초기화하지 않지만 모두 채우기 전에는 노출하지 않는다. 잘못된 첫 lane/순서/tag/generation/kind/예약 비트나 중간 CHR_END는 sticky fault로 멈춘다. 새 board controller는 이 fault에서 STOP과 미완성 프레임 폐기를 수행해야 하며, 그 controller는 아직 연결하지 않았다.

부분 타일 도중 같은 generation의 source ABORT가 도착하면 scratch만 버리고 ABORT를 전달한다. 이미 공개한 다른 묶음이 있더라도 전체 세대는 미완성이므로 소비자는 화면에 확정하면 안 된다. STOP/reset/active loss는 mailbox·scratch 소유권·읽기창을 함께 취소한다. 부분 타일 후 STOP/restart에서 새 token과 새 데이터만 나타나는 경계를 시험했다. 모든 비동기 위상의 물리 CDC 승인을 뜻하지 않는다.

완성된22B 레코드는2048B 묶음 경계에서 쪼개지지 않는다. 기존 token consume/PREPARED/COMMIT/displayACK 수명 구분은 유지한다. token wrap fault와 새session seed 요구도189와 같다. 새 production1901 decoder는 아직 없으며1813 소비기에 섞어 보내면 안 된다.

## 검증

SELECT `probes/nes-chr190/test02` + `evidence01`. test01은 호스트 GCC의 `%zu` 형식 오류로 C 컴파일에 실패했고 원본을 보존했다. `%u`와 명시적 cast로 수정한 test02에서 모든 시험을 완료했다. 승인된 Starter FLOAT 래퍼를 사용했고 임시 서버는 종료했다.

| 합성 사례 | 189 바이트 | 190 바이트 | 감소 | 묶음 수 |
|---|---:|---:|---:|---:|
| patch0, CHR3타일 | 763 | 541 | 29.10% | 2→2 |
| maxgroups/7raw, CHR3타일 | 3,132 | 2,910 | 7.09% | 3→3 |
| raw query fault | 924 | 702 | 24.03% | 1→1 |
| CHR512타일, 소비 지연 | 49,627 | 11,739 | 76.35% | 26→7 |

- 배포 exporter181/fill165/mailbox165 + 후보190/188을 실제 RTL로 연결했다. query와 PSRAM 응답은 고정 fixture, 소비자는 raw bus 시험기다. live PPU/실제 게임/65816 DMA/board mux/실기 측정은 아니다.
- 네 사례 모두 exporter의96bit 레코드 배열은189와 같고, 읽은 모든 바이트는 독립 타일 인코딩 결과와 같다. CHR512는 두 슬롯 full 대기261,311 host클록 후 손실 없이 완료했다. source-fault 사례는 ABORT1/COMMIT0이다.
- 정상 두 사례는 새 타일 묶음을 host 검사기에서 기존 레코드로 복원해 **배포186의 변경 없는 C 수신기**에 넣었다. 이전 형식으로 실행한 수신기 전체18,072B가 byte 동일했다. 이는 호스트 ABI 크기이며 ARM 메모리 승인 수치가 아니다. PREPARED 상태는 검사기가 COMPLETE 후 주입했으므로 실제 제어 ACK 경로 검증은 아니다.
- 부정/경계10사례: 틀린 첫 lane, lane 누락, tag 변경, generation 변경, kind 변경, reserved bit, 중간 CHR_END, 이전 BEGIN version, 부분 타일 ABORT, 부분 타일 STOP/restart 후 새kind3 타일을 확인했다.
- C 검사기의 타일당16번 재확장 호출은 동등성 확인용이며 제안 runtime이 아니다. 1901을 production에서 받는 MCU/65816 decoder를 구현했다고 주장하지 않는다.
- 기존186 배포2799파일·실기11파일·187 회고8파일·188 후보142파일·189 후보328파일의 해시를 확인했다. GBC164/세이브 SRAM/배포 파일은 변경하지 않았다.

## 남은 비용과 다음 작업

187에서 쓰던 바이트당8 master cycle 모델에서11,739B의 카트리지→WRAM 순수 payload 하한은 약4.37ms다. **측정값이나 완성 프레임 시간은 아니다.** 수집·PSRAM fill·레코드당 mailbox handshake·변환/슬롯 할당·제어와 DMA 시작·WRAM→VRAM/VBlank·음성/입력·최종 ACK를 제외한 값이다. 특히 이번 host 측 묶음은 upstream의 CHR바이트별96bit mailbox 인계 횟수를 줄이지 않았다.

raw 위주 사례는7.09%만 줄었다. 모든 장면의 속도가76% 좋아지거나60fps에 도달했다고 해석하면 안 된다. 실제 첫 레벨 연속 스크롤의 같은generation source/변환 결과는 여전히 미확보다. 현재 C 변환 시간에는 staging callback 비용도 포함되므로 그 시간을 모두 순수 CPU 연산으로 간주하지 않는다.

추가 payload는 타일 하나16B scratch뿐이다. 188의4096B 읽기 RAM을 재사용하며 전체512타일 복사본/세이브 SRAM을 만들지 않는다. scratch가128bit라는 사실과 serializer/metadata 레지스터 증가를 자원표에 반영해야 한다. 현 잔여24LAB/14M9K에 들어간다는 합성·FIT 보장은 없다. 새 전체 ARM/FPGA FIT/STA/ASM/ZIP은 실행하지 않았다.

다음은 합성 버퍼 시험을 더 늘리는 것이 아니라 **실제 변환기의 슬롯·row mapping 계획을 분리하고, FPGA의 작은 tile materializer와 결합해 기존 BG/OBJ 출력 bytes가 같은지 확인하는 것**이다. cross-tile/OBJ row mask/raw 경계를 보존하고, tile source의 bank/내용 generation·fetch 시점 의미를 유지한다. 작은 조각으로 기존 source 수명을 유지할 수 있는지, snapshot/cache 비용과 총16.67ms 예산이 성립하는지 먼저 판정한다. 이후 최종section descriptor/실제SNES bulk 읽기/표시 ACK와 board 연결, 최소 FIT/IO 후 실기로 간다. 같은바이트를MCU가SPI로재공급하는경로는왕복제거로채택하지않는다.

실제 스크롤 절차는 월드맵 숫자1 타일+A → 레벨 상태 확인 → **RIGHT+B 유지, A press/release 반복**이다. 이번에는 실행하지 않았다. MMC4/5·CHR-RAM·강제save/load/cache invalidate·mute·frameskip 요구와 GBC164/저장 영역을 보존한다. 약60fps·사운드 확인 → 장기플레이/오류·reset로그 → 입력 품질 순서를 유지한다.
