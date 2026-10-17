# NES210 — 스크롤 전송 예산과 지속 재사용의 첫 실기 판정

PR118 머지 `c263d6385622e1215fb84f5aa4a7f0b244bda5f0` 이후 수정 계획의 첫 단계다. 실제209 로그에는 구간별 바이트/패턴 수가 없어 스크롤 중 입력과 출력 중 어느 경로가16.67ms 예산을 넘는지 판정할 수 없었다. 새 대형 RTL/캐시를 FIT하기 전에, 동작하는209 경로에 제한된 측정을 넣는다.

## 작업 의미

**실제 지속 재사용 구현의 채택 판단에 필요한 실기 자료 수집 단계**다. 동시에2031 receiver가 보장하는 정렬된 물리 태그 목록을 활용하여191 planner의 반복 선형 검색을 이진 검색으로 바꾼다. 최대512항목을 반복 검사하던 부분을 로그 규모의 비교로 줄이지만, 이것만으로60fps에 도달한다고 주장하지 않는다. 정렬·범위·kind는 첫 계획을 내보내기 전에 확인한다. 기존 raw/alt/mask/palette 처리·계획 순서·SPI 프로토콜·표시ACK는 유지한다.

## 기록과 해석

- 기존 `nes-progress-210.txt`, `nes-game-last-210.txt`를 유지하고 `nes-budget-210.txt`를 추가한다. 기존4096B 게임 로그에 억지로 넣지 않고 동일한 임시text 버퍼를 다시 사용한다. 안전한 STOP/base복원 후에만 기록하며 플레이 중 SD 접근은 없다.
- 5초 단위12개 집계, **프레임 시작 시점**으로 묶는다. 수신/계획/SEAL 시간, 완료 수/최대 표시 간격, D0–D3/E8/E9/E0/E1/기타 clocked bytes, 계획/출력량/복잡한 변환량, BG/OBJ수, 현재map dirty64B그룹 수를 남긴다. SPI 전송 전 opcode를 잡아 TX==RX 버퍼가 덮어써져도 분류가 바뀌지 않는다. TX와RX 길이를 두 번 더하지 않는다.
- cache 모델은256entry 직접 사상,64bit **정확한 키** 비교다. CHR-ROM의 physical tag+변환행, OBJ physical tag+mask, zero를 구분한다. 충돌은 교체/미스로 처리하며 같은 프레임 반복은 프레임 간 재사용으로 세지 않는다. alt 변환은 재사용을 주장하지 않는다. 별도 순번은 generation wrap과 분리하고 자체wrap에는 무효화한다.
- 모델은 실제 계획/읽기/DMA를 생략하지 않는다. 같은 실행 자료에서 미래 재사용의 효과를 가늠하는 자료이며 active slot·display base/bank·퇴거 안전성을 입증하지 않는다. 태그가 같아도 내용이 바뀌는 CHR-RAM에는 적용할 수 없다. 현재 immutable ROM-session에만 의미가 있다. 실제cachemiss나 물리PSRAM읽기 수라는 이름을 붙이지 않는다.
- 모델 키/순번2,560B는 RUN stack에만 둔다. 반환 전에 포인터를 끊는다. 집계만 상시 남기며, 부팅/로드 실패에도 이전 실행의 기록이 남지 않도록 diagnostic entry와 runtime begin에서 초기화한다.
- `analyze_nes_budget210.py`는 실제 clocked bytes의 SPI하한과 재사용 가능한 **계획payload만** 뺐을 때의 조건부 하한을 구분한다. 직접타일 payload를 SPI바이트로 세지 않는다. 아직 구현하지 않은poll/ACK·메타데이터·맵 절감을 빼지 않는다.

## 일부러 단정하지 않는 항목

10ms 기존 시간축은 현재 수백ms 지연을 구분하는 데 사용한다.16.67ms 간격의 jitter/60Hz 합격에는 해상도가 부족하다.5초에 시작한 프레임은 다음 구간에서 끝날 수 있고, 실패한 마지막 프레임의 전송도 포함될 수 있다. 따라서 bin의frames/5를 순간FPS로 제시하지 않는다. 전체 평균·최대간격만으로 median/p95를 만들어내지 않는다. 바이트는 기존runtime transfer wrapper를 통과한 값이다. service 콜백의 별도 관찰/오디오 등의 트래픽은 제외되므로 전체버스점유의 하한이며 모든SPI트래픽을 계측했다고 주장하지 않는다.

아직 미측정: 실제 physical read/cache miss, SNES 전수비교시간/fallback원인/VBlank횟수, 원래 NES좌표에 맞춘 맵 이동량, 캡처와 표시의 실제 scene 대응. FPGA148LE/1LAB와SNES본문1B 조건에서 이러한 계측을 전부 추가하기 위해 큰 RTL/ROM을 변경하지 않았다. 먼저 이번 SPI/패턴 자료로 병목을 좁히며, **이번판 통과만으로 영속slot 구현을 승인하지 않는다.** 기존 intro/정지 fixture는 스크롤 자료의 대체가 아니다.

## 다음 판단

실기에서 숫자1+A→첫레벨→RIGHT+B 유지/A 반복 구간을 기록하고 시작 시점 또는 영상을 함께 받는다. 실제스크롤에 속한 bin을 먼저 식별한다. 재사용 가능량이 커도 잔여geometry/E1/map/control 비용이 예산을 넘으면 그 경로도 바꾼다.256entry모델의 충돌 미스가 많으면 더 큰cache의 가능성을 곧바로 부정하지 않고 키배치/용량을 검토한다. 이후 stable physical-slot+스크롤맵+dirty소비를 같이 설계하고 최소 경계 검사 후 다시 실기로 간다. 아직 same-input 후보픽셀 replay나 지속캐시 구현 완료는 아니다.

FPGA/SNES ROM/PSRAM qualification/SPI속도/최종ACK/세이브SRAM/기존GBC164와209 복구자료는 변경하지 않는다. 새FPGA FIT/ASM은 수행하지 않는다.210패키지는 기존209 FPGA 바이트를 새 이름으로 포함한다. 재사용 모델은 지원매퍼 확장이나60fps를 보장하지 않는다.
