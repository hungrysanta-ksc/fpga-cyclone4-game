# NES212 — 유지 슬롯을 실제 SNES 변경 범위 소비에 연결

PR120의 동일 branch `codex/nes-resident-slots-211`에 추가한 후보다. **실제 C 플래너/송신기와 실제 65816 실행의 연결 검증**이며 생산 RUN·SPI/RTL 연결과 실기 패키지는 아직 없다. 기존210 배포는 그대로다.

## 작업 의미

211의 슬롯 유지가 실제 화면 출력까지 이어지도록 했다. 이전 소비자의 WRAM 전수 비교와 작은 변경의 활성 VRAM 수정/큰 변경의 전체 재구성을 제거했다. 새 소비자는 이번 대상 버퍼에 필요한 타일·맵 범위만 쓰고, 그 범위만 VRAM DMA 목록으로 만든다. 이는 60fps를 위한 출력 작업 감소 구현이다.

작은 갱신도 두 번의 VBlank를 반드시 기다리는 구조는 60fps의 해법이 될 수 없다. 따라서 DMA 후 남은 예산이 충분하면 팔레트·OAM·HDMA 설정과 표시 bank 전환을 **같은 VBlank**에서 완료한다. 큰 갱신만 여러 VBlank로 나누고 그동안 이전 화면을 유지한다. 단일 VBlank 완료 가능성을 검증한 것이며 전체 생산 경로가16.67ms 이내라는 뜻은 아니다.

## 소비 계약

- BEGIN payload12: `2121`, 대상bank16, 마지막 표시 serial32, immutable content epoch32. 소비자는 정확한 다음 serial, 기존 표시 base, WRAM/VRAM 대상 일치를 검사한다. 첫 bank는0, 이후 교대한다. 세션 중 epoch 변경은 거절하므로 reload/state-load는 COMMON STOP/drain과 소비자 재설정이 선행되어야 한다.
- BG/OBJ는 기존 op7 descriptor/token/generation/정렬/길이/범위 검증과 실제400800 DMA를 유지한다. 순차 offset 대신 sparse 수신 bitmap으로 중복을 거절하고, 각 대상bank의 초기화된 슬롯을 별도로 기억한다. 지도는64B 정렬 DATA/RLE만 허용한다. 활성 버퍼에서 복사하던 COPY6는 거절한다.
- 비활성 WRAM에 받은 범위와 동일한 비활성 VRAM 범위를 명령 목록에 기록한다. 인접 source/destination을4096B까지 합치며, 전체 payload 비교나 전체 화면 복사를 하지 않는다. raw2048B는 필요한 프레임에 정확히 갱신한다.
- SEAL payload168: 기존24B metadata/version2121과 실제 C 플래너의 참조 BG/OBJ bitmap144B. 소비자는 참조 슬롯이 **이번 목적 bank**에 초기화되어 있는지, map64그룹이 모두 유효한지 검사한다. C는 used가 목적 residency 또는 이번 dirty에 포함되는지 추가 검사한다. 실제 map/OAM의 참조와 used bitmap의 일치는 C 플래너의 책임이며 기존211 참조 대조와 이번 픽셀 대조로 검증했다. SNES가 map/OAM 전체를 다시 파싱하는 방식은 아니다.
- bitmap의 valid는 물리 공간의 초기화 여부다. 같은 물리 주소의 내용/행변환/키 동일성은211의 정확키 및 epoch 계약이 담당한다. 미완료 후보에서 설정된 valid를 가지고 재시도하지 않는다. 오류는 terminal이며 다음 실행 전 공통 재설정한다.
- C 송신기는 실제 ACK의 op/sequence/serial/generation/signature와 표시 성공을 확인한 뒤에만211 commit한다. op7 consume은 운송 완료이며 최종 표시 ACK가 아니다. 구형 begin/seal/pattern API는 후보에서 실패하도록 하여 구형 RUN이 우연히 이 프로토콜을 쓰지 못하게 했다.

## VBlank와 메모리 예산

DMA는 한 VBlank에 payload+명령당96의 합4192까지 쓴다. 최종 palette512+OAM544+두 DMA 설정192+제어 여유320=1568이 남으면 같은 VBlank에서 전환한다. 아니면 serviced bounded wait로 새 VBlank를 기다린다. VRAM/팔레트/OAM 쓰기와 표시 ACK가 VBlank 안에서 발생하는 것을 실제 65816 실행에서 검사했다. 이 정적 비용은 실기 WCET/60Hz 증명으로 사용하지 않는다.

SNES ROM은4KiB 유지, boot96B/본문3552B/본문 여유384B. 구형195 본문3935B·여유1B에서 전수 비교·fallback을 대체해 공간을 확보했다. 새8KiB ROM이나 FPGA FIT가 필요하다는 결론은 내리지 않았다.

SNES 전용 WRAM metadata는 `$1246..$144f`에522B 추가, DMA 목록은 `$7e4000..$7e6607`에9736B다. 목록은 최대1216개의 서로 겹치지 않는 BG1024/OBJ128/map64 단위와 raw1개, 총1217개·stride8이다. 본문 `$7e2000..$7e2ddf`, stack `$1fff` 아래, 기존 source frame bank7F와 분리된다. 이 공간은 **SNES 내부 WRAM**이며 카트리지 저장 SRAM·FPGA M9K·ARM RAM을 소비하지 않는다. 기존 boot/SPC/client 주소와 겹치지 않는 것을 소스에서 점검했다. 생산 복원 경로와 묶은 검사는 다음 통합에 남는다.

ARM은 resident3200B/video15912B 유지, 새 송신기 object2388B/data·BSS0. SEAL 자체 stack280B(210의144B보다136B 증가), packet320B, begin48B, bulk40B. 기존 관찰cache2560B 교체에 따른 상태+640B만 차감한5104B는 **새 호출 체인과 IRQ를 반영한 full RUN 여유가 아니다.** 후보를 global로 중복 할당하지 않는다.

## 검증 범위

선택 `test09/arm03`, 기준 실제186 converter 화면은 `test05/reference-normal`에 보존한다. [검증 JSON](../analysis/dirty212-verification.json).

- 실제210 기반211 planner → 후보 C packet 송신 → held file mailbox → Mesen의 실제65816 → 실제 WRAM/PPU/DMA/ACK. source CHR와 FPGA descriptor/aperture는 fixture다. WRAM·PPU·성공 ACK 주입은 없다. 실제 생산 E8/E9/계획 FIFO/RTL/SPI bus와 함께 구동한 시험은 아니다.
- 정상14프레임,856,576픽셀을 기존 실제186 converter+195 소비자 결과와 정확 대조한다. cold양쪽 bank, warm 재사용, 새 키, 행변환/raw 표시·해제를 포함한다.
- 같은 합성 입력에서 sink packet485→349개, packet bytes82877→45985B(-44.51%). 후보의 직접 tile aperture992B는 별도이며 SPI packet bytes와 혼합하지 않는다. source 계획/ingress/poll/audio 비용을 포함한 전체 버스 절약률이 아니다.
- 정상 후보의 VRAM DMA26848B/45명령. 기준 실행에는 이 새 카운터가 없으므로 VRAM 감소율을 만들어내지 않는다. warm 동일 프레임3이 정확히 한 VBlank에서 완료되어 불필요한 두 번째 VBlank 제한이 없음을 검사한다.
- 표시 전 오류11종: bank/base/epoch 오류, 없는 슬롯, map 누락, 구형 SEAL, 중복tile/map, descriptor token 오류, DMA 중 STOP, 최종 전환 전 STOP. 이전 화면이 그대로 유지된다.
- 추가 pressure3프레임:80개의 불연속 작은 범위와2048B bulk를 포함, 최대83개 실제 DMA 목록을 여러 VBlank에서 소비한다. 각 쓰기는 VBlank 안이며 같은 참조 픽셀을 유지한다. 최대1217 목록의 전수 부하 실측은 아니다.
- 표시 ACK 전송 손상1종: SNES는 두 번째 화면을 실제 표시했지만 C에 전달하는 ACK generation을 손상시킨다. C는 commit을 거절하고 첫 표시 residency만 유지한다. 이 경우 물리 화면이 이미 바뀌었으므로 '기존 화면 유지'라고 주장하지 않는다. 재사용은 중단하고 COMMON reset으로 다시 일치시켜야 한다.

중간 build01/02 label 연결 오류, test01/arm01 sandbox DLL623, test02 C 하네스 경고, test03 Unicode Lua 경로, test04 이전 하네스 전용 조건 실패는 보존했다. test05 첫 정상 연결,06/07 오류/압력,08 두 VBlank 중간판은 선택하지 않는다. 최종09는 소스 스냅샷과 생성 C의 해시를 기록한다. 이전 archive는 수정하지 않는다.

## 바로 다음

1. 생산 RUN에서210의 passive cache를211 resident로 교체하고 loader의 immutable content epoch와 bind한다. fixture의 epoch1을 근거 없이 복사하지 않는다. `nes_sink212_begin` → 실제 planner/200 plan FIFO·193 sparse descriptor → finish/drain → `nes_sink212_seal` → 실제 표시 ACK →200 retire 순서를 연결한다. queued plan 수락을 실제 tile DMA 완료로 혼동하지 않으며, finish 전에 SEAL하지 않는다. 실패 시 resident abort/COMMON STOP/drain을 묶는다.
2. 실제 queue184/SPI/193의 sparse 순서·중복/취소·END 재무장을 연결에서 최소 검증한다. FPGA RTL은 현재 그대로 쓰는 것을 우선하고, 실제로 필요한 변경 없이 FIT를 반복하지 않는다. byte-identical 기존 source proof를 재사용한다.
3. full ARM RUN+IRQ stack/로그4096B 한계와4KiB SNES ROM 교체를 검사한 뒤 paired 실기판을 만든다. ROM-only ASM/CDB 경로를 우선한다. 이전210 패키지를 새 후보로 표기하지 않는다.
4. 사용자 영상으로 첫 레벨 스크롤의 간격·음향·입력·메뉴 복귀를 확인한다. 이후에도 부족하면 남은 geometry ingress/원래 NES 좌표를 이용한 순환 scroll-map과 생산·소비 겹침을16.67ms 전체 예산에서 처리한다. 단일 synthetic 숫자로 SMB3/다양한 mapper60fps를 선언하지 않는다.

사용자의 최종 정정은210의 마지막 약5초가 첫 레벨 내부였다는 것이다. 동일210/044 반복 시험은 요구하지 않는다. 다음 개선판 촬영은 로딩 종료 직전부터 메뉴 복귀까지다. save SRAM/GBC164/기존 배포/원본 ROM은 불변. MMC4/5·CHR-RAM의 fetch 당시 내용·epoch, state load의 invalidation, frameskip의 실제 표시 ACK 기준을 유지한다. 오디오·약60fps 확보 후 긴 플레이/오류·리셋 로그/조작 품질 순서다.
