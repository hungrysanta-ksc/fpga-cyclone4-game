# NES181 — SNES 수신·부분 행 표시·완료 ACK 연결

PR113의 후속 구현이다. 실제 MCU sink가 보낸 새 규격을 배포용 SNES 클라이언트 후보가 수신하고, 비표시 VRAM 준비·최종 전환·완료 ACK까지 수행한다. 기존180 배포본은 변경하지 않았다. 아직 보드 전체 연결·전체 ARM 링크·FPGA 배치·실기 전이며 새 설치 패키지는 없다.

## 구현

`tools/nes_client181.py`는 기존172 부트 복사 검증,169 비표시 뱅크 갱신,178 clipping을 보존하며 새 후보를 생성한다. 이전 생성기 파일을 수정하지 않는다. 짝이 되는 C 코드는 `nes_native_sink181.c`, `nes_native_video181.[ch]`, `nes_native181.[ch]`다. 기존165 API 이름으로 격리 빌드하되181 후보끼리 배치해야 한다.

- SEAL24의 version1812·0~7행·일치하는 수신 길이를 검사한다. FPGA→MCU version1811과 서로 다른 규격이다.
- section5는 일반 화면에서 최대1,121바이트 scroll HDMA, 부분 행에서는 정확히3,418바이트 bundle이다. scroll1121 + raw CHR2048 + modeA81 + modeB81 + enable81 + 길이6의 배치를 유지한다.
- scroll 표의 유한 길이·224행·반복 플래그 금지, modeA/B/enable의 같은 구간 길이·종료·224행·raw 행 수·고정 mode/map/window 값과 길이 꼬리를 검사한다. raw 픽셀·슬롯의 원본 유효성은 앞 단계 수신기와 변환기가 담당한다. 모든 가능한 악성 패킷 조합을 검증했다는 뜻은 아니다.
- 부트의 강제 블랭크 동안 raw map A7000/Bb000을 준비한다. 첫32개 타일 번호는320+x/832+x, 나머지 영역은0이다. 일반 map6000/a000과 분리된다.
- 일반→일반은 기존 차분 갱신을 유지한다. raw가 있거나 직전 화면에 raw가 있으면 비표시 뱅크에 BG·OBJ·map 및 필요 시 raw CHR A5000/B9000을 준비한다. 한 번의 DMA는 최대4,096바이트다.
- 최종 vblank에 palette/OAM·BG/OBJ 뱅크·scroll·mode/map·enable/window의 세 HDMA 채널을 함께 전환한다. raw→normal은 mode0·일반 window·단일 scroll HDMA로 복구한다. 활성 HDMA는 이전 candidate WRAM을 계속 읽고 새 데이터는 반대 candidate에만 기록한다.
- 실제 DMA·전환 완료 뒤에만 성공 ACK를 낸다. 복사와 최종 대기 모두 기존 유한 wait169와 STOP/pad 서비스를 사용한다. 거부·STOP은 성공 ACK를 내지 않고 fail-stop 상태로 들어간다. 세이브 SRAM을 사용하지 않는다.

검사 중 초기 화면 전송이 vblank를 넘긴 뒤 바로 HDMA를 켜는 오류를 발견했다. 화면은 다음 프레임부터 맞았지만 첫 공개 시점은 scanline2였고, 초기화되지 않은 HDMA 현재 주소를 읽었다. 처음 표시할 때도 전송 후 다음 vblank를 기다리도록 고쳤다. 최종 시험에서 공개·완료 ACK의 vblank 조건 및 초기화되지 않은 읽기 경고 부재를 확인했다.

## 검증과 재현

선택 근거는 `probes/nes-client181/evidence/test05`의12경우와 `test06`의 raw-first1경우다. 본문 바이트는 두 실행이 동일하다. test06은 시험 하네스에 첫 raw 화면 경로만 추가했으며 앞선 결과를 재실행한 것으로 계산하지 않는다. 각 실행의 원본 소스 사본·해시·로그·패킷·ACK·픽셀은 보존했다.

| 항목 | 결과 |
| --- | --- |
| 실제 C sink→실제65816 mailbox→DMA/HDMA/PPU | 정상7 + 최대 페이로드2 + raw-first2 =11장면,630,784픽셀 전체 일치 |
| 일반/raw·두 VRAM 뱅크 | 0/1/7행, clipped/unclipped, raw→normal, 정상 noop,127행 초과 구간 분할 통과 |
| 최대 페이로드 | BG16KiB·OBJ4KiB·map4KiB·raw2KiB;7번의 유한 복사 중 이전7프레임 보존 |
| 잘못된 입력 | version·행 수 상한·행 수 불일치·SEAL 길이·mode·반복 플래그·표 길이·scroll 오류8경우 E0 |
| 중단 | 복사 도중 및 최종 전환 대기 중2경우 E4, 이후 전체 화면이 이전 화면과 일치 |
| ACK/서비스 | 전체13경우에서 실제 CPU가 만든1,359개 ACK의 op/seq/serial/gen/signature 확인; pad 샘플·SPC 초기화 유지 |
| ROM | 본문3,768/3,776바이트, compact ROM4,096바이트; 부트 복사 readback 유지 |

수신 버스는 파일로 모델링했다. ACK·WRAM·PPU 명령을 시험 코드가 주입하지 않는다. 입력은 이전 실제 C 변환 결과를 재사용한 결정적 장면이며 SMB3 전체 실행 또는 물리 SPI/실기 결과가 아니다. 오류 시험의 초기 정상 장면10개는630,784픽셀 수에 중복 합산하지 않았다.

재현 도구는 `tools/test_nes_client181.py --out <새 ASCII 임시 경로> --gcc <gcc.exe> --mesen <Mesen.exe> --fixtures <보존된 nes-consume181-test06>`이다. 기본13경우 또는 `--modes raw_first` 등 필요한 경계를 선택한다. Windows GCC DLL relocation623 문제는 기존처럼 승인된 host 실행으로 처리하며 FLOAT/Questa는 이번 단계에서 쓰지 않았다.

초기 build01/02는 ROM 크기 초과였고, 초기화 반복을 루프로 묶어 줄였다. test01은 광범위한 Lua 후킹으로50초 제한에 걸렸다. test02/03은 기능 탐색 근거이며, 초기 공개 시점 오류를 찾기 전이므로 최종 채택 근거가 아니다. test03 실행 중 하네스 보완이 있었던 점도 기록한다. 최종 채택은 고정된 코드의 test05/06이다. 별도 read01/02는 초기 HDMA 경고의 CPU·DMA 상태를 좁힌 조사 기록이다.

## 제한과 다음 단계

**화면 경로 연결 완료와60fps는 다르다.** 현재 raw 후보는 비표시 VRAM을 통째로 준비하므로 최대7번의 fresh vblank와 최종 전환을 기다린다. 이 방식만으로 매 프레임60fps를 보장할 수 없다. 기존 raw wire 약53ms 모델과 table 재전송 비용도 남아 있다. 실제 생산·전송·표시 완료 간격을 측정하고 raw 묶음 전송, bank별 기준 세대에 대한 차분 갱신을 다뤄야 한다. 표시 횟수/60초를 FPS로 사용하지 않는다.

다음은 실제 board의 PPU color/emphasis→frame181→export181 배선을 완성하고 MCU/SNES 후보를 같은 격리 통합본에 배치하는 것이다. 전체 ARM RUN/IRQ/stack·4096B ROM·FPGA 자원/타이밍·조건부 IO를 확인한 뒤 최소 SMB3 숫자1→A 실기로 간다. 기존 함수별 video stack696/seal136, receiver18,064/video15,888 크기는 전체 링크 승인값이 아니며 기존180 여유1,040바이트와962/963LAB를 새 후보 승인으로 옮겨 쓰지 않는다.

완료된 독립 PPU/수집기·긴 부팅·동일180·044 시험을 반복하지 않는다. 실제 게임의 영상 정지 해소와 갱신 간격을 우선 확인하고, AV→장시간 실행/오류·리셋 로그→입력 유지 순서를 따른다. GBC·164 복구판·180 배포본·세이브 SRAM·완료된 이전 근거는 그대로 보존한다.

[현재 인계](../cores/nes/HANDOFF.ko.md) · [검증 데이터](../analysis/client181-verification.json) · [MCU 변환 계약](nes-consume181-contract.ko.md)
