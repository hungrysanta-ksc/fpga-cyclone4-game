# NROM452: 무시된 loader 예산을 실제 phase에 연결

**정정 및 재검증:** 첫 재배치 `fit01`은 QSF 지정 `sys/iir_filter.v`가 빠진 무효 실행이다. 모든 QSF 입력을 포함해 재배치한 `fit02`에서 아래 수치를 다시 얻었다. QSF 지정 입력 66개 중 원본과 다른 것은 수정한 SDC 하나뿐임을 확인했다. 첫 실행은 실패 증거로 보존한다.


419 보드 SDC의 `loader|state*`는 현재 wire를 가리켜 5.3ns max-delay 예산이 무시됐다. 원본 배치 DB 사본에서 대상만 `loader|phase*`로 바꾸자 phase 8개와 loaded_bytes 19개가 선택됐다. 동일 배치·동일 경로의 최악은 일반 클록 기준 +0.351ns, 기존에 의도한 강화 5.3ns 예산 기준 −0.301ns였다. 강화 예산 미달을 일반 setup 실패로 혼동하지 않는다.

같은 419 소스·핀·seed·Quartus Lite에서 이 제약 하나만 바로잡아 새로 배치했다. loader phase→loaded_bytes 최악은 강화 기준 +0.102ns, 일반 기준 +0.754ns다. 전체 FIT는 14,751→14,741 LE, comb 13,607·FF 8,029·RAM 185,824bit 동일이다. 420과 같은 제한된 분류에서 관련 경로 최악 setup +0.102ns/hold +0.135ns, epoch reset 최소 +1.605ns, 조건부 PSRAM +3.034ns, SNES 79.887ns, SPI 165.097ns다. 45개 첫 단계 fanout 확인과 제한 표본의 native payload reset 검사도 통과했다. 이 IO 계산은 기존 전기적 가정을 따른다.

전체 raw setup 최악은 −6.970→−6.568ns, recovery 최악은 −8.824→−11.467ns다. 후자의 해당 보고 경로는 NES 클록 `clock_guard|ref_qualified`에서 memory 클록 `reader|memory_reset[0/1]`까지의 비동기 reset release 경로다. 419와 다른 경로가 최악이므로 숫자 차이를 동일 경로의 회로 회귀라고 단정하지 않는다. 미제약 IO, reset/CDC 전체 검증과 MTBF는 여전히 열려 있다.

판정: 잘못된 제약 이름의 구체적인 수정 후보이며, **새 배치를 실기용 산출물로 승인하지 않는다**. 관련 경로·IO는 제한 분류일 뿐이며 raw reset 경계 및 복구 검증이 먼저다. RTL 및 생산 firmware를 수정하지 않았다. raw 자료는 `probes/nes-nrom452/sta01`·`fit02` (무효 `fit01` 별도 보존), 재계산 가능한 범위는 `analysis/nrom452-timing.json`이다.
