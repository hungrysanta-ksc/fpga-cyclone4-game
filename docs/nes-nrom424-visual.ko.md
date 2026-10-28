# NES424: 자체 NROM 화면 및 입력 반응 fixture

외부 ROM 없이 iNES1 NROM16/CHR8/수평을 직접 생성했다. NES CPU는 PPU 초기화 뒤 체크무늬 배경을 출력하고 4016의 A bit가 들어오면 palette를 바꾼다. 음성 테스트는 아니다. `fixture02`가 선택이며 SHA-256은 `edd81f0da6990d91e2967200aa46186098940761638015a2fd239a8084f216af`다.

Mesen NES `mesen11`은 frame60 배경 palette 0x21과 frame100 palette 0x16, 두 프레임의 서로 다른 표시 픽셀 및 nametable 값을 확인했다. **4016 read bit는 Lua callback에서 명시적으로 주입했다.** 실제 controller 장치는 시험하지 않았으며 NES 에뮬레이션 결과이지 FPGA·65816·SNES·실기 화면이 아니다. 앞선 `fixture01/mesen01..03`은 palette 변경 뒤 PPU 주소를 복구하지 않아 화면과 입력 결과가 실패했고, `fixture02/mesen04..10`은 화면은 관측됐지만 테스트 실행기의 controller 장치가 비어 실제 입력 확인이 실패했다. 모든 실패를 보존한다. emucap launch는 sandbox에서 .NET host를 찾지 못했고 별도 Mesen 시험은 기존 C:/works/dotnet과 격리 경로를 사용했다.

Mesen `TestRunner.Run`의 `InitializeEmu(..., true, true, true, true)` 마지막 인자는 `noInput`으로 확인됐다. 따라서 위 단일 실행기로는 컨트롤러 장치 부재를 게임 코드의 오류라고 판정하지 않는다. 실기 입력 승인에는 실제 pad 장치가 활성화된 에뮬레이터 또는 보드 시험이 필요하다.

동일 ROM SHA를 414 actual loader/FatFS/programmer/run136 host fixture의 `loader01`에 넣어 정상 및 오류 9개 사례를 통과했다. SPI/PSRAM·native·observer·GPIO/DONE·IRQ는 모델이며 411의 실제 FPGA 전송 전체 시험을 이 ROM으로 다시 실행한 것은 아니다.

423 실제 진단용 BI3는 227 programmer/FatFS와 합성 FAT16의 `programmer01`에서 읽어 510,856B의 핀 모델 전송 내용이 RBF와 완전히 일치했다. GPIO/DONE은 모델이며 실제 FPGA 구성·base 복구는 미검증이다. 보드/firmware/65816 파일 이름과 해시 결합은 진단용이고 419 raw STA, 미제약 IO와 reset의 한계가 남는다. 실기 package 승인이나 60fps 결과가 아니다.
