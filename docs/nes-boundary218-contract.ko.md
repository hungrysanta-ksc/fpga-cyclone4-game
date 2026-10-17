# NES218 SPI 바이트 경계 사전 판별

작업 의미: NES216의 정상 출력/ROM 대기 제외 수정과 NES217의 로더·세대 수정을 실기에 배포하기 위한 전체 FPGA 타이밍 정리다. 게임 루프의 전송량·프레임 수나 SPI 클록을 변경하지 않으며, 이것만으로 60fps 개선을 주장하지 않는다.

기준은 봉인된 `nes-loader217/source04`의 90개 소스다. source01은 `nes_rom_spi.sv`만, 최종 source02는 여기에 `nes_rom_loader.sv`의 데이터 저장 조건을 추가로 정리한다. 기존 `bit_count == 7` 비교를 `byte_last` 상태로 유지한다. 동기화된 SCK 상승에서 이전 count가6이면 다음 상태가1, 나머지는0이며 SS-high와 reset에서0이다. 모든 도달 가능한 상태에서 `byte_last == (bit_count == 7)`을 유지하므로 첫 명령 바이트·offset·CRC·snapshot의 수신 에지는 이전과 같다. 원래 bit_count는 길이 검증에 계속 사용한다. 새 비트는 같은 mem_clk 도메인에 있다.

## 기능 검증

- 원본217 SPI와1056768 상태 에지/1024 후속 시퀀스를 비교했다.
- bit count8 × byte count16 × SS/SCK/이전SCK/reset16 × 모든 입력 바이트256 =524288경계를 비교했다. counter saturation9, 마지막 비트, 첫 바이트 command predicate, CRC와offset의 모든 수신 에지가 포함된다.
- 실제2.625MHz SPI/SS-high2000ns219트랜잭션14016MISO비트 비교.100READ/7ACK/19손상/72취소/2중첩을 통과했다. 기존 boot/reader를 연결한 회로시험이며 실제 카트리지 시험은 아니다.
- 잘못된 count5 조기 판별과 SS-high 시 잘못된 상태 유지 회로는 검출했다.
- loader217/epoch217/WAIT216는 내용 해시가 같은 기존 증거를 재사용하며 재실행했다고 쓰지 않는다.

## 배포 조건

전체 보드 MAP/FIT, 3corner nominal/strict setup·hold, 기존96 epoch register reset, CDC 첫 단계 fanout 및 held/Gray 경계, 조건부 PSRAM/SNES/SPI I/O를 확인한다. 클록·SDC·오류 검사를 완화하지 않는다. 통과하더라도 현재212 SNES ROM을 넣은 ASM 및 새 ARM 식별자와 짝을 맞추기 전에는 설치 파일이 아니다. 원본217 archive, GBC164, 저장SRAM, 기존 배포판은 보존한다.

결과는 `analysis/boundary218-verification.json`과 `probes/nes-boundary218/progress.json`을 기준으로 한다. 실패 시 정확한 배선 경로를 기록하고 같은 소스의 seed 반복을 하지 않는다.

## source02 로더 데이터 저장

source01의 SPI 대상은+0.724ns로 개선됐으나 전체 최악은 check_failed→byte_hold/lane/chip -0.338ns로 바뀌었다. source02는 RECEIVE에서 DATA를 받아들이는 조건을 직접 계산해 기존 command_conflict/상태별 우선순위 사슬에서 데이터 레지스터를 분리한다. IDLE/READY 상위 case와 fault/commands_blocked/BEGIN/END/START/STOP/count_complete는 모두 캡처를 막는다. 주소·데이터 저장 시점과 SETUP/WRITE/HOLD/RELEASE 파형은 같다. 새 파이프라인이나 클록·SDC 변경은 없다.

원본217 로더와294912상태/1056쓰기 시퀀스/524288count/131072이전 오류코드 조건을 비교했다. 차단을 무시하거나 STOP 시 데이터를 저장하는 의도적 오류는 검출했다. 최종 로더+SPI+boot+reader 조합으로 실제219트랜잭션/14016비트/100READ/7ACK/19손상/72취소/2중첩도 다시 통과했다.

## 전체 보드 결과와 한계

| 후보 | LE / FF / LAB / M9K | nominal setup | strict setup | hold |
|---|---|---:|---:|---:|
| source01 SPI 경계 |15105 / 8352 / 954 / 47|-0.338ns|-0.338ns|+0.132ns|
| source02 +payload 조건 |15129 / 8352 / 956 / 47|-0.207ns|-0.437ns|+0.118ns|

최종 여유279LE/7LAB/9M9K. 대상 nominal 경로는 SPI offset+1.311ns, payload capture+1.024ns, 로더 error+0.906ns, serial→Gray+1.612ns다. **두 국소 경로 개선이 전체 타이밍 통과를 뜻하지 않는다.** 최종 strict 최악은217의-0.155ns보다 나빠졌으며 아직 미채택이다. 소스·시험·배선 증거용 선택 source02이며 제품 배포 선택이 아니다. 새 ARM/ASM/ZIP 및 실기시험 없음.

남은 두 경로를 함께 검토한다.

1. `reader.check_response_address[8] → control.load_end`: nominal+0.015ns, 기존5.5ns strict 예산에서는-0.437ns. 4LUT/5.861ns, 배선3.759ns(64%). 주소 비교 중1.566ns, 공유 error_response fanout10 이후1.519ns 배선이 크다. READ의 고정 요청 tag와 같은 에지의 잘못된 응답 취소를 유지하면서 비교/명령 출력의 공유 범위를 줄이는 방향을 검토한다. 응답 검사를 한 클록 늦추거나 없애지 않는다.
2. `loader.phase[4] → count_clear → loaded_bytes[0]`: nominal/strict-0.207ns, 5LUT/6.079ns, 배선3.549ns(58%), count_clear fanout20. STOP/BEGIN/정상 완료와 WRITE/HOLD drain 시 카운터 의미를 보존한다. 단순 CE 속성/seed 반복으로 처리하지 않는다.

두 후보의 전체3corner 타이밍/CDC/reset 및 조건부I/O를 보존한다. 조건부 통과는 전기적 전체 signoff/MTBF 완료가 아니다. 수정 후 전체 기준을 다시 통과해야 현재212 SNES ROM·새 ARM과 결합한 실기 시험으로 갈 수 있다. 동일215/044 재시험이나 추가 영상은 지금 요청하지 않는다.

최종 CDC4404행/45첫단계 단일fanout/신규미분류data0, held6.809ns/Gray6.886ns.96reg/576reset 경로 최소recovery40.070ns/removal1.658ns. 조건부 I/O PSRAM+3.599ns/SNES83.995ns/SPI164.474ns와 native payload reset 통과.
