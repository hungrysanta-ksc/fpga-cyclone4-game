# NES1814 — MCU→SNES 반복 word 전송

## 결과와 작업 의미

실제 C sink와 SNES65816 수신기에 반복16bit word 전송을 추가했다. **이전 화면 복사본이나 추가 frame RAM 없이** map/팔레트/OAM/raw bundle의 반복 구간 전송량을 줄인다. 기존1813은 FPGA→MCU 형식이고, 이번1814는 MCU→SNES SEAL 버전이다. 서로 다른 경계이며 이번 시험에서 FPGA1813까지 종단 결합한 것은 아니다.

| 같은 client181 장면 | 기존 최소 SPI byte | 새 최소 SPI byte | 기존→새 최소 모델시간 |
|---|---:|---:|---:|
| normal gen12/15/16 |6,730|4,782|21.206→15.270ms|
| raw7 gen13/14 |11,055|8,389|34.819→26.694ms|
| raw1 gen17 |11,055|8,003|34.819→25.518ms|
| raw7 gen18 |11,055|8,073|34.819→25.731ms|

같은7frame의 request bytes는54,785→37,575B(약31.4% 감소)다. packet 수275는 그대로다. 명령·상태·ACK 최소 overhead35B/packet과3transaction×8µs, SPI2.625MHz를 포함한 계산이며 **실기 시간이나 SNES 처리시간 실측이 아니다**. 실제 FIFO polling 추가분/CPU 반복복원·service/FPGA→MCU도 제외되어 있다. 같은 fixture의50,217 logical DATA bytes는 기존과 전부 같다.

정상 frame도 이번 한 방향 최소15.270ms로 전체16.7ms와 전송80% 목표를 거의 소비한다. raw는 여전히 더 느리다. 따라서60fps 완료가 아니고, bank 차분·raw steady 갱신·capture/export 겹침이 계속 필요하다. 이 압축을 frameskip으로 부르지 않는다.

## wire와 수명 계약

기존 DATA op2와 동일한 section/offset/sequence/serial/generation을 사용한다. op4는 다음 의미다.

- 물리 payload는2B, header12..13도2. 실제 packet 길이는18B다.
- 기존 reserved14..15는 복원 길이. 짝수4..240만 허용한다. payload의 little-endian word를 그 길이까지 반복한다.
- op4 외에는 reserved0 검사 유지. header 물리길이, BUILD 소유권, sequence/serial/generation, section0..5, 정확한 다음 offset과 section 한도를 먼저 검증한다.
- 허용된 op4만 비표시 WRAM candidate에 CPU로 복원한다. 최대120반복이며 service는 기존 packet 경계에서 수행한다. STOP 반응시간을 실측한 결과는 아니며 반복 처리의 상한을 둔 것이다.
- 기존 ACK는 op4를 그대로 echo하고 status0으로 수신 완료를 알린다. SEAL24/버전1814의 유효성·최종 PPU 공개·display ACK/STOP 계약은 유지한다. 구버전 조합은 승인하지 않는다.

C는 원래 한 DATA packet의 모든16bit word가 같고 길이가 짝수4이상일 때만 압축한다. 일치하지 않으면 그대로 op2를 보낸다. 부분 run 분할이나 이전 frame delta를 구현한 것은 아니다. 기존256B packet stack을 재사용하며 receiver/video/sink 구조체, frame buffer, packet 수와 최대 논리 chunk240B를 늘리지 않았다.

현재 `nes_native_video181.c`에는 이미 BG15tile/OBJ7tile callback 묶음이 있다. **이 처리를 새 작업으로 다시 구현하지 않는다.** 다음 CHR 개선은 기존 묶음 위에서 정확한 residency/target-bank 기준 차분을 다룬다. 이전 인계의 일반적인 “CHR 묶음” 항목은 이 사실과 함께 해석한다.

## SNES 코드 공간과 검사

본문은3,768→3,774B, 허용3,776B 중2B가 남는다. 전체 program4096B와 WRAM layout은 같다. 공간 확보를 위해 DP=0인 scratch의 비indexed absolute 명령을 같은 direct-page 명령으로 인코딩했다. opcode/주소폭/flag 의미는 유지한다. DBR=7F를 사용하는 비교 routine의 indexed load/compare는 변환하지 않는다. 다른 주소·indexed/indirect 명령은 바꾸지 않는다. 새 decoder를 더 넣을 때 남은2B를 충분한 공간으로 간주하면 안 된다.

선택 `test02`는 실제 C sink→held file mailbox→실제65816→DMA/PPU/ACK 경로15경우를 통과했다. normal7frame, raw-first/복귀, 최대tile, 잘못된 버전/표/patch수, 복사 중STOP/최종STOP, packed 길이0·홀수·초과·물리크기·section·offset·token 오류를 포함한다. 총1,210개의 실제 ACK다. 거부된 후보가 이전 화면을 바꾸지 않는 것도 확인했다. 최대tile case는 기존7번의 bounded copy를 유지했다; normal의19held frame은 여러 장면의 합계이며 한 frame 지연으로 해석하지 않는다.

`test03`은 **같은 C/ROM 바이트**로 normal7frame의 모든 DATA를 ACK 시점의 실제 WRAM에서 대조했다. 일반 DATA와 반복복원 bytes 모두 일치했고 실제 PPU 출력도 기준과 같다(추가275ACK). 화면색 일치만으로 복원 영역 전체를 검증했다고 추정하지 않도록 추가한 검사다. source/game/PSRAM은 이전 합성 fixture이므로 실제 SMB3 또는 FPGA SPI 결합 시험은 아니다.

`check01`의 native C encoder는 길이1..240×4pattern 및 잘못된ACK의961exchange를 확인했다. 반복word/비반복/마지막byte차이/홀수길이와 실패 후 재전송 금지를 검사했다. 여기의 ACK는 mock이며 위 실제SNES 시험과 구분한다.

ARM object-only stack에서 packet304→312B(+8B), seal136B·pattern32B는 그대로다. 전체RUN/IRQ/link와 새4KiB 여유 목표를 통과한 것이 아니다. FPGA1813+C1813+sink1814의 실제 통합은 별도 확인해야 한다. 추가 frame RAM0도 “추가자원 전체0”을 뜻하지 않는다.

처음 `test01`은 sandbox GCC 실행 WinError623으로 컴파일 전 실패했다. 같은 기존 도구를 host에서 실행한 `test02`를 선택했으며 실패 경로도 보존했다. 새FIT/Questa/펌웨어/ZIP은 만들지 않았다.

## 다음 작업

1. 추가16KB ARM plan 없이 가능한 target-bank 기준 delta/section 변화 추적과 raw steady-state 공개를 설계한다. 기존 BG key union/receiver bitmap 수명을 지킨다. 변경 버퍼마다 자원·포트·수명·취소 경계를 기록한다.
2. capture/export 겹침 및 hostRUN/STOP 계약도 함께 유지한다. frame 생략/강제 로드 후에는 실제 표시 bank 기준을 검증하거나 완전 갱신하며, 오래된 delta·ACK를 재사용하지 않는다. [추가 사용자 기능](nes-runtime-features181.ko.md)의 비파괴 pause·mute는 향후 구현 조건이다.
3. 바뀐 최소 경계 검증→전체 ARM/FIT/IO→SMB3 숫자1+A 실기로 간다. 실기 frame 간격과 source 누락/음성을 확인한다. 현재 배포180/GBC164/세이브SRAM과 완료된 archives는 유지한다.

재현: `tools/nes_sinkpack181.py --out <새경로>`로 후보 C와ROM을 생성한다. `tools/test_nes_sinkpack181.py`는 기존 client181과 같은 `--out/--gcc/--mesen/--fixtures/--modes` 옵션을 사용한다. fixtures는 consume181/test06의 절대 경로를 사용한다. [결과](../analysis/sinkpack181-verification.json) · [확장 자원 목표](nes-mapper-headroom181.ko.md)
