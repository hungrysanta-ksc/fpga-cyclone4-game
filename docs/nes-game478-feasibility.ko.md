# NES478: SMB3 대표 입력과 MMC3 전체 보드 예산

PR135의476/477 실기 이후 첫 게임 진입 관문이다. **새 SMB3 실기/게임 부팅이나 FPS를 확인한 결과가 아니다.** 현재 실기 기준은 NROM476 평균23.84fps다. [수치·입력 해시](../analysis/game478-feasibility.json).

## 실제 ARM에서 게임 기록을 확인했다

기존에 동결한 SMB3905–975의71 geometry/raw를 원래 `nes-delta231/test07/result.json`의142개 해시와 대조했다. ROM이나 새 게임 실행을 생성하지 않고 캡처된 활성 배열만 현재2232 ABI의 host encoder로 포장했다. 실제474/476 ELF의 PT_LOAD와 firmware를 대조해 M4 poll·CRC·packet·prepare·planner를 실행했다.

SPI peer와 tile plan/DMA 완료는 모델이다. generation905–975·epoch1·serial1–71을 부여해 bank0/1/0 수명을 이어갔다. 원래 게임의 시간·SPI 거래를 재생한 것이 아니며, model packet 분할/압축이 실제 FPGA 출력과 byte 동일하다고 주장하지 않는다. 활성 geometry·raw를 별도로 비교했고, 두 실제 ARM의 전체 receiver/video/resident bytes와 모든40B plan이71개 모두 같다.

| 입력·CPU 비용 | 최소 | 중앙값 | 최대 |
|---|---:|---:|---:|
| OBJ 항목 | 8 | 8 | 28 |
| 필요 tag | 89 | 100 | 111 |
| raw 예외 bytes | 512 | 512 | 512 |
| host2232 payload bytes | 3740 | 3770 | 3996 |
| 수신474 명령 | 648899 | 651642 | 674961 |
| 수신476 명령 | 336368 | 337421 | 347277 |
| 계획 명령,474/476 동일 | 704576 | 799681 | 874617 |

수신 절감률 중앙값은48.22%다. 개선은 이 게임 기록에서도 유지된다. 그러나 계획 중앙값은 문양 warm172546명령의 **4.63배**다. 단순 문양의 CPU/표시 성능을 게임으로 확장할 수 없다는 점도 확인했다. 입력 bytes는 host 모델의 예시이며 실제 SPI 대역/ROM 경쟁/IRQ·65816·전체 시간이나 FPS로 환산하지 않는다.

이71개는 기존 게임의 한 구간이다. 시작 화면·월드맵·모든 sprite/IRQ/음악·전 게임 호환성·독립 새 pixel golden proof를 대신하지 않는다. isolated unit RAM128KiB를 사용했으므로 전체 RUN 물리 stack proof도 아니다. public에는 source/도구·hash·집계만 남기고 원본 ROM/geometry/raw/plan payload는 Git에 추가하지 않았다.

## MMC3를 현재 보드에 복원해 전체 배치를 확인했다

471의66개 QSF 지정 입력을 고정하고, 원래227의 MMC3 `cart_top`을 hash 대조해 복원했다. 포트 선언은 동일하다. `nes_local_memory.sv`에는 기존8KiB PRG RAM 구현이 남아 있으며 mapper 복원으로 다시 사용된다. 소스를 새로 임의 재구성하거나 모듈 면적을 더해 FIT를 예측하지 않았다.

| 전체 비용 | NROM471 기준 | MMC3 진단478 | 차이 |
|---|---:|---:|---:|
| MAP LE | 18253 | 18923 | +670 |
| MAP comb/FF | 13620/8063 | 14016/8383 | +396/+320 |
| FIT LE | 14740 | **15266** | +526 |
| FIT comb/FF | 13672/8063 | 14069/8387 | +397/+324 |
| RAM bits | 185824 | 256608 | +70784 |

동일 Quartus Lite25.1·device EP4CE15F17C8, seed1이다. 수정 seed/구조 탐색은 하지 않았다. 올바른 입력을 갖춘 map03/fit03은 성공했고 실제 잔여는 **142LE**다. MAP의18923LE와 실제 FIT15266LE를 같은 지표로 판단하지 않는다. 배치 성공은 신규 기능을 추가할 넉넉한 예산이나 실제 게임 성공을 뜻하지 않는다.

동일 fitted DB에서 기존 implementation/nominal204 제약을 각각 읽었다. 관련 clock 경로의 최악 setup **+0.187ns**,hold **+0.146ns**다. 전체 raw STA는 setup−6.499ns/recovery−9.140ns가 남으며 reset/CDC/외부IO 승인은 미완료다. 관련 경로의 양수를 전체 signoff로 승격하지 않는다. 제약·클록·예외를 새로 완화하지 않았다.

## 누락된 소스 의존성도 정리했다

기존471 보고서의 Source Files Read에서 `nes_native_ciram165.sv`·`sink-program.hex`가 자동 발견된 것을 확인했다. QSF66개만 복사하면 CIRAM이 누락된다. 또 board.sdc가 읽는 `cdc181.sdc`는 QSF 지정 목록/기존 board-source snapshot 밖에 있었다. 원래 실행한471 폴더의 동일66입력을 다시 대조한 뒤 정확한 CDC bytes를 복구했다.

새 진단은 CIRAM을 QSF에 명시하고,66지정+2자동발견+1transitive SDC인 **69개 파일**을 hash로 보존한다. 이것은 기존 bitstream이 잘못 동작했다는 뜻이 아니라 기존 목록이 전체 재현 입력을 다 담지 못했다는 뜻이다. 현재476 설치본·과거 원문/실패/실기는 변경하지 않았다.

첫 m4game01의 익명 union DWARF 처리와02의 bool ABI 인수 오류를 고쳐03으로 전체71개를 확인했다. map01의 CIRAM 누락,fit02의 cdc181.sdc 누락도 보존했다. 특히 fit02는 배치 이전 제약 읽기 실패이지 장치 용량 초과의 증거가 아니다. map03/fit03에서 원본 의존성을 복구했으며 새 라이선스·Questa 시험은 실행하지 않았다.

## 다음 구현과 승인 경계

1. NROM과 혼동되지 않는 **새 MMC3 profile identity**와 정확한 SMB3 header/크기/CRC/PRG·CHR 배치를 ARM loader/readback/START/STOP/base 경로에 묶는다. 현재 진단은 여전히ID78·NROM loader라 **실기 사용 금지**다. 새 firmware/bitstream/설치본은 아직 없다.
2. 실제 MMC3 core에서 source/query·CHR bank 전환/IRQ·입력 중 ROM 경쟁과 display lease를 연결한다.71개 host-encoded replay로 이 관문을 대체하지 않는다. ROM은 기존 사용자 고정본을 쓰고 배포/Git에 넣지 않는다.
3. 원래 paired65816에서 게임 프레임 소비·DMA·독립 검사·최종ACK·observer·STOP/base/menu와 새 source/제약을 검증한다. payload가 커지고 계획도 무거우므로 기존24fps를 게임 FPS로 예측하지 않는다.
4. 이 관문을 통과한 같은 source/FIT/timing/원복 구성만 실제 게임 비교에 전달한다. 제한 NROM476은 회귀용으로 보존하고 문양60fps를 선행 조건으로 두지 않는다.

도구는 `check_nes_game478.py`, `prepare_nes_mmc478.py`, `analyze_nes_game478.py`다. raw/실행 source는 `probes/nes-game478/m4game03`·`mmc03`, 관련 LUT/원본 캡처는 기존 private 자료에 남긴다. 정확한 실행 옵션은 분석 도구의 CLI와 JSON pins를 사용한다.
