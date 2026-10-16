# NES194 직접 타일 수신과 기존 표시 경로 연결

PR117 같은 branch의 미배포 후보다. 배포186/GBC164/세이브 SRAM을 유지한다. 실제 스크롤 부하 감소·실기 FPS는 이번에도 미측정이며 `analysis/scroll193-measurement-plan.json`의 수집 run은 비어 있다.

## 작업 의미

193의 SNES-planar 타일 묶음을 실제65816 코드가 카트리지 읽기창에서 WRAM으로 DMA하고, 기존 section 검증·VRAM 비교/비활성 bank 갱신·최종 표시 ACK로 이어가는 경계를 구현했다. 타일 bytes를 MCU/SPI로 다시 채우는 방식이 아니다. 이번 SNES 시험의 타일 공급은 과거 실제186 C가 생성한 합성 fixture를 읽는 Lua bus다. 실제193 RTL과65816을 동시에 실행하는 결합 시험이나 실제 게임 생산기 연결은 아니다.

## 제어 레지스터와 소유권

`nes_bulk_control194.sv`는193의 host-domain descriptor를 다음 주소에 노출한다. 앞의 `00:`은 SNES bank다. 기존6000/6010 제어부·400000 패킷 창과 겹치지 않는다.

| 주소 | 의미 |
| --- | --- |
| 00:6040 | 현재 chunk ready: 0 또는1 |
| 00:6041 | kind: BG0 / OBJ1 |
| 00:6042..43 | 길이16bit, little endian |
| 00:6044..45 | section 내 byte offset, slot×16 또는×32 |
| 00:6046..47 | generation16 |
| 00:6048..4b | token32 |
| 00:604c..4f | 소비할 token32의 네 byte 쓰기 |
| 00:6050 | A5 쓰기로 consume 요청 |
| 40:0800..0fff | 기존188 immutable payload 읽기창 |

네 token byte가 모두 작성되고 현재 token과 정확히 같아야 consume을 한 번 발행한다. publish 시 mask는 성공/실패 모두 지운다. 부분 token·이전 token·잘못된 token은 소유권을 바꾸지 않는다. raw /WR 끝을 동기화해 처리하며,193과 같은 reset/STOP/active/source fault 취소가 필수다. 독립 reset은 지원하지 않는다. host clock 정지 중 STOP에도 제어부와 payload 출력은 차단된다. 재시작 fresh token 발급은 상위 controller 책임이다.

## SNES 명령과 표시 완료

새 프로토콜 SEAL1941의 op7은 기존16B 헤더와4B token payload를 사용한다. section은0/1, physical length는4, expanded length는 타일 정렬된16..2048이다(OBJ는32배수). sequence/serial/generation과 section 순차 offset/최대 길이는 기존 수신기의 검사도 그대로 거친다.

수신기는 ready/kind/generation/offset/token/length를 모두 대조하고, 잘못된 영역·0/초과 길이·타일 비정렬을 거부한 뒤 DMA한다. destination은 현재 후보의 WRAM7F bank이며 이전 표시 bank는 건드리지 않는다. 한 번의 DMA는 최대2048B이고 그동안 service 호출은 없다. 직후 STOP/pad service를 호출한 후 token consume을 쓴다. STOP이면 E4로 끝내고 consume하지 않는다. 실제 전체 deadline·오디오 서비스 cadence는 아직 통합 검증 대상이다.

**consume는 카트리지 버퍼 해제일 뿐이다.** op7의 정상 ACK는 staging 수신 확인이다. 실제 화면 완료 ACK1은 모든 section과 SEAL을 검증하고 VRAM/CGRAM/OAM/HDMA 반영이 끝난 기존 경로에서만 나온다.193의 ENDsealed도 최종 표시 완료가 아니다. 기존 raw 전환·장면 전환의 비활성 VRAM 재구성·이전 화면 유지·COPY/RLE·pad/SPC 초기화 의미를 보존했다.

## 검증과 제한

SELECT build03(ROM bytes=build02), rtl03, snes05/06/07. 실제 기록은 `probes/nes-bulk194`에 보존한다.

- 실제193 생산기+194 제어부+188 aperture+확장 ROM bus RTL:2134 read checks, 정상 consume3, 부분/오류/이전 token 거부4. BG/OBJ 전환,2KiB 최대 묶음, 비영 slot, host clock 정지 중 STOP와 fresh restart를 통과했다. read/write bus 중복 구동도 검사했다. 합성 타일 입력이며 실제 CPU DMA를 함께 실행한 것은 아니다.
- 기본4KiB bus는 수정 전 배포 소스와 모든 LoROM 영역 및 packet256주소, 총33024개 읽기에서 동일했다. 실제8KiB의 code extension·vector mirror·빈 주소·기존 packet/control도 검사했다. 실제 보드 mux/IO/STA는 미검증이다.
- 실제65816/Mesen 시험: 과거186 C 생성7장면을 op7로 재포장한15chunk/4512B를 수신하고 전체428288픽셀이 기존186 기준과 같았다. 첫 장면의 사용하지 않는 BG 타일에0을 덧붙여4096B section을 두2048B chunk로 처리하도록 했다. 이 인위적 최대 길이 시험은 스크롤 성능 자료가 아니다.
- 잘못된 ready/kind/length/offset/generation/token6조건, header expanded 초과·비정렬·section·physical length4조건, DMA 직후 STOP1조건: 총11거부 사례에서 이전 화면이 그대로 유지됐고 잘못된 chunk는 consume되지 않았다. 실제 코드가 쓰는 WRAM/PPU/ACK를 검사했으며 harness에서 대신 쓰지 않았다. 총 ACK 수와 fixture 실행시간은 FPS가 아니다.
- build01은3999B 본문이 기존3776B 제한을 넘어 실패했다. build02/03은 명시적8KiB 후보다. snes01 설정 접근/snes02 다른 개발 번들의 DLL/snes03 상대 ROM 경로/snes04 Unicode Lua 경로 실행 실패, rtl01 Unicode DB 경로 실패를 보존했다. 이후 기존 Mesen 번들과 ASCII 임시 실행 경로로 완료했다. rtl02는 제어부 중간 통과이고 rtl03은 기본4KiB 비교를 추가한 최종 선택이다.

## ROM·자원 비용과 다음 작업

SNES 본문3999B는 기존3776B보다223B 크다. 이번에는 검사를 삭제하지 않고 **8KiB ROM 후보**로 기능 검증했다. `nes_sink_bus165`에 PROGRAM_BYTES parameter를 추가했지만 기본값4096은 그대로다.8KiB compact image의 끝64B는 기존과 같은 header/vector mirror이고 본문이 겹치지 않는지 검사한다. 새8KiB 이미지는 기존4KiB 보드에 배포하면 안 된다.

193의 부분 회계47M9K에 ROM 증가 예상4를 더하면51/56이다. 이것은 실제 합성 결과가 아니며192 cache·191 buffer·추가 제어 logic와24LAB 여유를 포함한 전체 배치/타이밍 승인이 아니다.8KiB를 최종 채택했다고 보지 않는다. 전체 연결 전에 초기화/공통 수신 코드 재사용으로4KiB에 복귀 가능한지와 전체 M9K/LAB 비용을 비교해야 한다. 현재 body/ROM 크기 변경만으로 전체 RAM/ARM 승인도 얻지 못했다.

다음은 실제 production plan 입력/codec/CDC·content epoch/frame-start latch와 board mux, MCU의 op7 제어 명령 발행·section 장벽 연결이다. 이번 op7은 보관된 C 출력에서 시험 도구가 작성했으며 production C sink가 발행하지 않는다.193 tile source와194 SNES 수신기 간 최종 결합에서 같은 token/generation/section 수명을 확인해야 한다. raw/palette/OAM/HDMA는 현재 경로를 유지하며 전체16.67ms source/변환/전송/표시 예산을 계산한다.

최소 통합·자원·IO 조건이 성립하면 짝패키지 실기로 넘어간다. 성능 판정은 **숫자1 타일+A → 첫 레벨 확인 → RIGHT+B 유지+A press/release 반복**에서 한다. 같은 generation의 읽기/변환/전송량과 고유 표시 간격을 묶고 cold/static/warm scroll/전환을 구분한다. 아직 같은generation 실기 스크롤 자료나 개선율은 없다. AV 약60fps→장기play/오류·reset로그→입력 유지 품질 순서를 유지한다. 일반 관측기/FIFO 확대·긴 무변경boot/FIT·186/044 재시험을 우선하지 않는다.
