# NES 058 — 공유 읽기 포트 계약

SPDX-License-Identifier: MIT.

058은 실행 전 읽기의 **메모리 클록 포트**를 구현한 단계다. 새 SPI 명령·MCU 비교/CRC·무결성 성공 판정·검증 성공을 요구하는 START gate는 아직 없다. 초기 자원 실험을 먼저 수행하라는 [057 설계](nes-rom-readback-plan.md)의 첫 부분이다.

## 구현과 소유권

`tools/nes_rom_readback.py`가 해시 고정052 reader와057 생성 loader/boot를 새 폴더에 변환한다. 원본은 수정하지 않는다. 기존 PSRAM 읽기 FSM·주소/chip/lane 레지스터·응답 데이터 레지스터를 CHECK와 RUN이 공유한다. 별도 reader·FPGA CRC 엔진·클록 mux·추가 CDC 요청 통로를 만들지 않는다. 추가 상태는 CHECK 응답 pulse와 sticky fault다.

- 모든 CHECK 입력/출력은 `mem_clk`에 속한다. `check_enable`은 END 승인 뒤 loaded이고 RUN이 꺼진 상태에서만 올린다. 코어/로컬 RAM/패킷은 기존 `!run_enable` reset에 계속 둔다. reader의 양쪽 도메인 공통 reset은 CHECK 동안 해제한다.
- `check_ready`일 때 `check_request` 한 클록과17비트 논리 주소를 준다. PRG0..FFFF, CHR10000..13FFF/17FFF다. CHR은 물리200000부터 읽으며 길이는057 승인 레지스터로 판정한다. 이후 입력 주소를 바꿔도 이미 수락한 핀 주소는 유지한다.
- `check_response`는 완료 시 한 메모리 클록이다. 그 클록의 데이터와 반환 주소를 **같은 클록에서 소비**해야 한다. 주소 tag는 controller가 보관한 물리 주소/chip/lane에서 얻는다. 다음 요청이 보관 주소를 바꾸므로 응답을 무기한 보존하는 mailbox가 아니다. SPI 연결에는 별도의 완료 보존/ack 계약이 필요하다.
- busy 중 요청, 범위 밖 주소, loaded 이전 CHECK, CHECK 중 BEGIN/DATA/END/START 또는 RUN 중 CHECK는 sticky `check_fault`다. RUN 허용을 내리고 읽기를 취소한다. common reset으로만 해제한다. 이미 수락된 쓰기의 펄스/hold는 끝까지 진행한다.
- 취소는 `check_enable=0`으로 한다. RUN 전에 최소 한 메모리 클록 동안 CHECK를 내리고 공통 reader reset을 거친다. 이 실험은5클록을 사용한다. STOP과 CHECK 해제는 함께 수행하며 READY 이미지가 폐기된다. RUN STOP은 기존대로 loaded를 유지한다. common reset은 이미지와 reader 양쪽 상태를 무효화한다.
- CHECK 모드는 MCU/decoder가 직접 상태를 유지해야 한다. 현재054 SPI는 그대로이며 CHECK 제어를 제공하지 않는다. generated SPI wrapper의 포트 전달은 공동 fit에 포함했지만 새 MCU 파형 시험을 한 것은 아니다.

## 공개 재현

Python3, Questa SystemVerilog가 필요하다. 다음 명령은 이 개발 호스트의 기존 FLOAT wrapper 안에서만 실행한다. 출력은 존재하지 않는 ASCII 디렉터리여야 한다. 각 모드는 순차 실행하며1seat를 공유한다.

```powershell
./tools/run_nes_rom_readback.ps1 -Python $PYTHON -FloatWrapper $FLOAT_WRAPPER -QuestaBin $QUESTA -Out $FRESH_OUTPUT -Baseline unused -Mode unit
./tools/run_nes_rom_readback.ps1 -Python $PYTHON -FloatWrapper $FLOAT_WRAPPER -QuestaBin $QUESTA -Out $FRESH_DIFF -Baseline unused -Mode diff
./tools/run_nes_rom_readback.ps1 -Python $PYTHON -FloatWrapper $FLOAT_WRAPPER -QuestaBin $QUESTA -Out $FRESH_MUTATION -Baseline unused -Mode mutation
```

unit은 공개 합성 패턴을 실제 쓰기 핀으로 초기값 없는 RAM 모델에 적재한다. 80/96KiB 전 영역 CHECK, 입력 주소 변경, PRG/CHR 바이트 손상, 잘못된 요청/명령, 취소/STOP/common reset, RUN 재전환, CHECK 오용 중 쓰기 펄스 유지가 포함된다. SRAM25ns 응답은 기존 가정이며 측정한 보드 규격이 아니다. PLL loss는 별도 입력이 없으며 common reset 시험을 물리 PLL 검증으로 부르지 않는다.

diff는 CHECK를 끈 새 reader와 원본052 reader를 같이 실행하여 양쪽 클록의 모든 edge 뒤 노출 출력들을 비교한다. mutation은 chip/lane/CHR 상위 주소를 각각 잘못 연결하여 주소 tag 검사에서 반드시 실패하는 것을 확인한다. 잘못된 구현의 기능 통과가 아니다. 현재 unit에 마지막 쓰기 유지 시험이 추가되기 전 mutation을 실행했으며, 실패 위치까지의 시험과 생산 RTL은 동일하다.

공동 fit는 해시 고정 **private057 fit export**가 추가로 필요하다. 공개 clone만으로 전체 코어 fit를 재현한다고 주장하지 않는다.

```powershell
python -B tools/nes_rom_readback_checks.py --mode fit --baseline $PRIVATE_057_FIT --quartus-bin $QUARTUS_BIN --out $FRESH_FIT
python -B tools/verify_nes_rom_readback.py --evidence $PRIVATE_058_EVIDENCE --out $AUDIT_JSON
```

마지막 명령은 저장된 unit/diff/mutation/fit 원본의 감사이며 새 시뮬레이션이 아니다. 드라이버·생성기·실행 소스·원시 로그를 보존한다. 기존 FLOAT 라이선스/전역 설정을 바꾸지 않는다.

## 이후 통합의 필수 조건

1. SPI 응답 snapshot에 완료와 실제 데이터/tag를 안전하게 보존하고 요청을 단일 outstanding으로 제한한다. 수신 중 덮어쓰는 offset을 응답 보관소로 사용하지 않는다.
2. MCU가 전체 길이의 반환 데이터를 SD 승인 입력과 비교하고 누락/중복/tag 불일치/timeout/CRC 오류를 거부한다. MCU 검증 성공과 RUN 허가를 분리해 연결한다.
3. 실제 MCU GPIO 파형→RTL 및 실제 코어8프레임 회귀를 새 경로로 수행한다.058의 RUN reader 차등 시험은 전체 CPU/PPU 재실행이 아니다.
4. SPI/MCU 연결 후 공동 fit를 다시 한다.058의 외부 가상 CHECK 포트335핀, PLL0, 물리 핀22개 미배치 조건을 전체 보드 fit/STA로 확대하지 않는다.
