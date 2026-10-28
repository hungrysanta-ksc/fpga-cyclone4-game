# NES422: loader 지연 가이드의 출처와 판정

419 후보와 실기 기준 224의 `nes_rom_loader.sv` SHA-256은 모두 `4ae5eceb7a80929b6ad5eefdcfeadcbb3ab1c78ee2cfa62a7032df0706e9c35f`, `board.sdc`는 모두 `425a210e3639abc282ad5e1ed0ed10990c7b1b161ccda4de5a3c8f76b21a80b5`다. 동일 소스·제약이라도 NROM cart에 따른 재배선 delay는 별도로 측정해야 한다.

문제의 5.3ns는 `board.sdc` 주석상 160의 배치 유도용 max-delay로, 기존 binary `loader|state*`를 대상으로 한다. 현재 `phase` one-hot과는 매칭되지 않으며 이 경고는 새 NROM만의 문제가 아니다. 181과 206 기록도 이름 불일치를 보존했고 전체 loader에 가이드가 적용됐다고 해석하지 않았다. 219는 카운터 경로의 count-clear 공유를 제거해 one-hot RELEASE 데이터 선택으로 바꿨으며, 뒤의 224 검증도 동일 warning을 지닌다.

421에서 현 NROM 배치의 `phase → loaded_bytes` 513경로를 3코너에서 직접 측정했다. slow 85C에서 최대 5.524ns, 일반 setup 최소 +0.351ns다. 이것은 실제 clock setup의 조건부 양수이고 이전 가이드를 phase 전체에 적용한 5.3ns 이내는 아니다. 원래 가이드의 의도를 새 phase 경로 전체의 자동 기능 명세로 확대하지 않으며, 반대로 양의 setup만으로 외부 I/O와 reset을 승인하지 않는다. 별도의 5.3ns를 달성하려고 검증된 219 선택을 되돌리거나 seed 탐색을 반복하지 않는다. 우선 224와 같은 조건부 경계, 제품 pair·실기 복구를 진행하고 관측된 시간 회귀 또는 재현 오류에 대응한다.

기존 224의 routed DB를 Lite에서 직접 같은 방식으로 재측정하려는 `base224paths01`은 Standard 프로젝트 DB 호환 오류로 실패했다. 별도 임시 사본에서 project force를 시도한 `base224paths02`도 유효한 Lite FIT DB가 없어 실패했다. 두 실패를 보존하며 baseline 경로 지연 비교값을 만들지 않는다. 사용자 정책대로 Standard를 재실행하거나 구매하지 않았다. 대조 가능한 것은 source/SDC 동일성 및 기존 224에 보존된 timing·CDC/조건부 IO 결과다.

다음은 새 ARM·FPGA·65816 paired build와 실제 의미 있는 화면/입력 fixture, 복구 경로를 연결하는 것이다. 419의 FIT·420/421 관련 clock·reset·조건부 IO 결과는 raw STA의 비동기 경로 39개와 54/56 미제약 포트 또는 전기적 signoff를 지우지 않는다. 60fps와 MMC4/5도 미입증이다.
