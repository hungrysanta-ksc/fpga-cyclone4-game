# NES232: 공동 증분 패킷의 실제 65816 소비기

PR127의231 C 후보에 실제 SNES 소비기를 연결했다. **같은 SMB3 스크롤69프레임에서 전송에 두 VBlank가 필요했던 경우가18→5개로 감소했다.** 기존4192 charge 한계와 DMA당96을 유지한 결과다. 생산 FPGA 송신기와 전체 ARM RUN은 아직 연결되지 않았으므로 설치판/실기60fps 승인이 아니다.

## 작업 의미

60fps 화면 전송 경로를 구현하는 단계다. 입력·출력 SPI 바이트를 줄여도 SNES에서 raw2048B를 매번 올리면 남는 병목을 해결한다. 변경된 raw/map 구간을 실제 VRAM DMA로 연결하고, 안전한 간격 결합과 불필요한 팔레트 재전송 생략을 실행 코드로 검증했다. 디버그 로그 확장이 아니다. 향후 metadata 병렬 전달 경로로 전환하더라도 이 소비기와 VRAM 비용 검증을 재사용할 수 있다.

## 구현 계약

- BEGIN/SEAL 버전2311, SEAL222B. 기존227 소비기와 혼용 금지. C231 입력·planner·sink 자체는 변경하지 않았다.
- 패턴1152비트와 metadata432비트를 합친198B received bitmap 및 목적 은행별198B valid bitmap을 사용한다. metadata는 map256/CGRAM32/raw-tail144개의16B 단위다. raw-tail 마지막9B는 정확한 끝2297B에서만 허용한다.
- map/CGRAM/raw-tail은 sparse 입력, OAM은 기존 순차/반복 전송, bundle의 처음1121B는 순차 검증이다. raw 없는 프레임도 기존 descriptor 길이만큼 prefix를 검증한다.
- 패킷 중복·정렬·범위·SEAL dirty mask·base serial·은행·epoch와 사용 패턴 coverage를 검사한다. raw 없는 프레임은 양쪽 raw valid를 무효화하여 다음 raw 진입 때 다시 채우게 한다.
- 명령은 준비만 하고, SEAL에서 필요한 목적 metadata 전체가 유효함을 확인한 **뒤에만** VRAM DMA를 실행한다. 따라서 같은 map/raw section의96B 이하 간격을 기존 비활성 WRAM 값과 함께 전송할 수 있다. 패턴의 비연속 간격이나 다른 section 사이를 합치지 않는다. 합친 DMA 길이4096B 이내, 기존 charge4192/설정96 유지.
- raw-tail의 처음2048B만 raw CHR VRAM 영역으로 업로드한다. 뒤의 mode/HDMA table은 WRAM 데이터다. raw 전량2048B 업로드를 제거했다.
- CGRAM32비트 received mask가0이면 마지막 global palette DMA512B 및 설정96을 생략한다. **송신 C231이 팔레트 변경을 양쪽 은행에 stale로 표시한다는 결합 계약이 필요하다.** 목적 은행의 이전 팔레트와 같다는 이유만으로 생략하는 방식이 아니다. cold palette 누락은 coverage에서 거절한다. 소비기가 별도로512B를 비교하는 구현도 아니다.
- 마지막 업로드는 내부에서 만든 고정 CGRAM/OAM descriptor만 사용한다. VRAM은 별도 검증 목록으로 처리하므로 해당 final routine의 도달 불가능한 VRAM 분기를 제거했다. 외부 패킷이 이 내부 descriptor 종류를 지정하지 않는다. 팔레트 포함 final charge1568, 생략 시 실제 제거된512+96만큼 줄어960이다.
- transport ACK, bulk consume, 화면 표시 ACK를 계속 구분한다. 표시 ACK 전에는 C resident/dirty를 commit하지 않는다. 잘못된 표시 ACK나 STOP 이후에는 공통 reset으로 양쪽 기준을 폐기한다.

## 실행 결과

관측230의 동일71프레임905..975를 사용했다. 처음2개는 cold, 이후69개가 warm 스크롤이다. C231 → file mailbox → **실제65816 명령 실행/Mesen SNES PPU** → 실제 표시 ACK → C commit으로 연결했다. ROM read와 bulk source 공급은 fixture이며 생산 FPGA가 아니다.

| 항목 | CGRAM 생략 전 scroll01 | 최종 scroll02 |
|---|---:|---:|
| warm 한 VBlank |51/69|64/69|
| warm 두 VBlank |18/69|5/69|
| cold 두 프레임 |각3 VBlank|각3 VBlank|
| 전체 VRAM 전송 |133,600B /478명령|동일|
| 최종 warm charge 평균/최대 |3,922.55 /5,360|3,314.55 /4,752|

5개 잔여 프레임은952,954,955,963,968이다. 이들의 실제 VBlank 다회 사용과 기존231 모델에서 palette 비용608을 제외한 예산 초과가 일치한다. **표의 VBlank는 화면 완성을 위해 업로드가 점유한 횟수이며 전체 처리시간이나 게임 FPS가 아니다.** cold 결과를 warm 평균에 섞지 않았다.

전 프레임의8570B 출력 metadata, 사용 중인 VRAM 패턴/전체map/rawCHR가 기대값과 일치했다. geometry/raw/metadata는 봉인된231과 byte-exact, 기존186 reference4,066,624 checks도 유지된다. E1 데이터 내용은 동일하고, 실제 bulk op7가 추가되어 달라지는 packet sequence2B만 별도로 순차 검증한 뒤 비교했다.

새 harness는 타일마다 bulk op7를 사용한다.598개 타일/12,944B를 전달했고, 출력 wire131,902B 중13,754B는598×23B bulk 제어, 나머지118,148B가 기존231 metadata wire다. 이 수치를 생산의 그룹 bulk 스케줄이나 실제 SPI 시간으로 해석하지 않는다.

별도 합성30프레임은 기존227/186 기준의 실제 합성 화면과 OAM에 일치했다. 다음12개 오류·중단을 거절/처리했다: dirty mask 변조, cold map 누락, raw 정렬 오류, raw 누락, cold palette 누락, CGRAM 중복, 은행/base/epoch 불일치, 구SEAL, 잘못된 표시ACK, final STOP. post-display ACK 변조는 이미 표시된 결과를 취소할 수 없으므로 host commit 거절 및 공통 reset이 필요하다.

fileRPC가 에뮬레이터 프레임 경계에서 패킷을 공급하므로 실행 wall time/기록된 seal_master_cycles는 생산 runtime 계측이 아니다. 전체 NES 코어 및 Mesen 원본 화면과의 완전한 RGB 등가성도 주장하지 않는다.230 OBJ timing/명시적 raw fallback의 기존 한계를 유지한다.

## 자원과 보존

- 실제 소비기 body3910B, 용량3936B 중26B 여유. boot96B/header64B 포함 기존4KiB ROM이다. 최종 재빌드는 시험한 ROM·body·compact hex와 byte-exact이며 boot/body/header 중첩을 검사했다. 초기 초과판8KiB는 진단용이고 선택하지 않았다.
- received `1280..1345`, bank-valid `1380..150b`, metadata end `150c`: 기존1450 대비 private SNES WRAM188B 추가. 명령 목록 `7E4000..6fff`,1536×8B=12,288B: 기존9736B 대비2552B 추가. 합계2740B이며 기존7F frame banks/HDMA 영역과 분리된다. 게임 세이브 SRAM은 사용하지 않는다.
- 최대 목록은 패턴1024+128, map256, rawCHR128=1536개로 제한한다. CGRAM/OAM은 final 처리, mode/HDMA는 목록에 넣지 않는다. 실제71프레임 최대 목록14개.
- C231 추가 상주160B 그대로다. 기존1800에서 차감한1640B는 산술 여유일 뿐 full RUN/call chain/IRQ 승인이 아니다.
- 생산227/FPGA224 자원 여유159LE/2LAB/9M9K는 재사용 값이다. 새 입력 delta 송신기는 미구현이고 새 FIT/STA/ARM firmware/ASM/ZIP을 만들지 않았다. GBC164·세이브 SRAM·기존 배포물 보존.

## 다음 단계

1. 실제 전체 RUN에231 C와232 consumer 계약을 연결할 때의 stack/IRQ 및 RAM 수명을 확정한다. FPGA source5741B base 저장/포트/비교·shift/raster 제어를159LE/2LAB/9M9K 내에서 구현 가능한지 구체적으로 산정한다. source release/다음 capture/부분 실패 시 base 교체 조건도 포함한다.
2. 잔여5개 warm 업로드의 버스트 비용과 실제 ARM/SNES 계산 시간을 전체16.67ms 경로에 넣는다. pending queue가 있다면 최대 화면 나이까지 제한해야 하며 단지 평균 바이트가 낮다고60fps 승인하지 않는다. CGRAM에 이어 무조건 OAM codec/FIT 반복으로 가지 않는다.
3. 조건이 성립하면 생산 FPGA delta 송신기/CRC·token·세션 base와 전체 경로를 연결한다. 성립하지 않으면 병렬 metadata 대안B로 전환한다. ARM SPI로 aperture를 재충전하는 방식은 우회가 아니다.
4. 최소 경계/whole-board gate와 paired build 후 첫레벨 스크롤 실기 시험으로 간다. 같은227/044 반복 시험은 필요 없다.

이번 변경은 표시 계층이며 mapper 물리 tag/행별bank/mask 의미를 바꾸지 않는다. MMC4/MMC5/CHR-RAM 호환이나 state/frameskip/mute 구현을 새로 입증하지 않았다. state load/reset은 delta·resident·SNES 기준을 함께 무효화해야 한다.

## 재현·증거

선택 `probes/nes-sparse232/build08`, `snes05`, `scroll02`, `analysis02`. build08은 무결성 assert만 추가했고 시험한 build07 body/ROM과 byte-exact다. scroll01은 비교용 이전8KiB 진단판이다. 이전 실패들도 보존하고 선택하지 않는다: 잘못된 reference 경로(snes01), Lua 삽입 순서(snes03), raw 없는 장면에 raw 오류를 주입한 시험(snes04), BEGIN 전체raw-valid 조건의 불필요한 DMA 결합 억제(snes04), 초기 ROM 크기 초과/build04 class 선택 오류. analysis01은 bulk 추가에 따른 sequence 차이를 고려하지 않은 비교 assertion 실패다.

```powershell
python -B tools/nes_sparse232.py --out C:/temp/232-build
python -B tools/test_nes_sparse232.py --out C:/temp/232-snes --reference-run <probes/nes-repeat227/snes02/reference-normal> --modes normal bad_dirty missing_map raw_align missing_raw missing_palette duplicate_cgram bad_bank bad_base bad_epoch old_seal wrong_display_ack stop_final
python -B tools/test_nes_sparse232_scroll.py --out C:/temp/232-scroll --rom <user-ROM>
python -B tools/analyze_nes_sparse232.py --before <scroll01> --after <scroll02> --synthetic <snes05> --build <build08> --out C:/temp/232-analysis.json
```

기존231/230/227 로컬 봉인 자료 및 지정 host GCC/Mesen이 필요하다. 신규 ASCII 출력 경로만 사용한다. ROM/게임 trace/바이너리는 Git에 넣지 않으며 공개 source와 검증 요약만 커밋한다. 현 단계에서 사용자 실기 재시험을 요청하지 않는다.
