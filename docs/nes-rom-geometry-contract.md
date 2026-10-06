# NES 057 승인된 ROM 크기 연결 계약

SPDX-License-Identifier: MIT.

054/055에서는 SPI BEGIN 인자가 적재 길이를 결정하지만 코어의 `chr_32k`는 별도 입력이었다.057은 **로더가 승인한 기존 `chr32` 레지스터 하나**를 적재 길이와 코어 CHR 주소 mask에 함께 사용한다. PRG64KiB 및 CHR16/32KiB 진단 범위는 같다.

`tools/nes_rom_geometry.py`는 해시가 고정된053/054 원본을 수정하지 않고 새 출력 폴더에 아래3모듈을 생성한다.

- `nes_rom_loader`: 기존 `chr32`를 `rom_chr32` 출력으로 노출한다. 새 형상 레지스터·명령·상태 머신은 없다.
- `nes_rom_boot`와 `nes_spi_boot`: 그 출력을 상위로 연결한다.
- 실제 코어/공동 자원 wrapper: `rom_chr32`를 코어와 PPU tap이 사용하는 `chr_32k`에 연결한다. 별도 `ext_chr_32k` 입력과 가상 핀은 제거한다.

SPI decoder의 `load_chr32`는 **수신한 명령 인자**다. CRC와 프레임이 정상이어도 BEGIN이 현재 상태에서 거부될 수 있어 이 값을 코어 설정으로 바로 사용하면 안 된다. 예를 들어32KiB 적재 중16KiB BEGIN을 보내면 decoder의 인자는0으로 바뀌지만 loader는 오류를 내며 기존 승인된1을 유지한다.057은 후자의 레지스터만 사용한다.

공통 reset에서 형상은0으로 초기화된다. 유효한 BEGIN을 IDLE/READY에서 승인할 때만 갱신하며, STOP 뒤에도 남은 비트 자체를 loaded/실행 허가로 해석하지 않는다. 코어·패킷 reset은 기존 `!run_enable`과049 scrub에 계속 묶인다. 설정은 BEGIN부터 RUN까지 안정되고 RUN 중 바뀌지 않는다. 메모리→NES 도메인의 이 안정된 설정/reset 계약을 사용하며, 독립 reset이나 RUN 중 형상 변경을 지원하지 않는다. 실제 배선/CDC/STA signoff는 별도다.

## 재현

```powershell
& tools/run_nes_rom_geometry.ps1 -Mode unit -Python $PY -FloatWrapper $FLOAT -QuestaBin $QUESTA -Out $UNIT_OUT -Baseline unused
& tools/run_nes_rom_geometry.ps1 -Mode mutation -Python $PY -FloatWrapper $FLOAT -QuestaBin $QUESTA -Out $MUTATION_OUT -Baseline unused
& tools/run_nes_rom_geometry.ps1 -Mode live -Python $PY -FloatWrapper $FLOAT -QuestaBin $QUESTA -Out $LIVE_OUT -Baseline $PRIVATE_055
& $PY -B -X utf8 tools/nes_rom_geometry_checks.py --mode fit --out $FIT_OUT --baseline $PRIVATE_054_FIT --quartus-bin $QUARTUS
```

unit는 공개 원본만 사용한다(`Baseline` 인자는 wrapper 호환용이며 unit에서는 읽지 않는다). SPI14형상 검사와 직접 loader360470검사/180224바이트로 두 길이, RUN/STOP, 잘못된 BEGIN과 손상 프레임을 확인한다. 실제 코어 live는 고정055 private export, fit는054 private 공동 자원 export가 필요하다. 입력 해시를 먼저 확인하며 과거 폴더는 수정하지 않는다.

live에서는 BEGIN 뒤 기존 fixture 인자를 반대로 바꿔 둔다. 코어는 loader의 실제 승인값으로 실행되어야 한다. 전체96/80KiB를 핀 쓰기로만 적재한 뒤 두 ROM의8프레임·491520픽셀·패킷·전체 S/E/F/D 이벤트를055와 비교한다. 이번 연결은 추가 레지스터/지연이 없어 release tick과 이벤트 시각도 차이0을 요구한다. 과거의 일정한 시각 차이 허용을 더 느슨하게 만들지 않는다.

`-Mode mutation`은 `nes_rom_geometry_mutation.py`를 같은 FLOAT wrapper의 RunOnly 경로로 실행한다. 동일 unit에서 승인값 대신 잘못된 SPI 인자 latch를 연결하는 대조 실험이다. 정확히 `Geometry check3 expected1 got0` 실패를 요구하며, 설계 통과로 세지 않는다. 한 좌석을 공유하므로 다른 Questa 작업이 끝난 뒤 실행한다.

`verify_nes_rom_geometry.py --evidence <private057> --baseline <private055>`는 원시 자료·해시·결과와 동일 생성 소스 사용을 감사하는 명령이며 새 시험을 실행하지 않는다. 이 경로를 공개 clone만으로 재현 가능하다고 표현하지 않는다.

## 미완료

형상 연결은 물리 readback이 아니다.056 MCU는 여전히 적재 전용이며 실제 START/메뉴 호출은 없다. 새로운 공동 자원 수치와 과거054를 구분하고, 남은 자원에서 [물리 읽기 검증 설계](nes-rom-readback-plan.md)를 먼저 평가한다. 보드 클록·소비자·실기 이미지·전체 핀/PLL/STA는 아직 남았다. GBC 및 실기044는 유지한다.
