# NES174 — 오류 코드 타이밍 회복과 실기 시험판

**실제 클록 setup +0.246ns / hold +0.156ns를 확보해 NES174 실기 시험판을 만들었다.** 타일 간 비트평면 수집 수정, 패턴 묶음 전송과 새 FPGA를 함께 적용한다. 아직 실기 결과가 없으므로 화면 정지 해결이나60fps 달성을 선언하지 않는다.

## 오류 코드 갱신 변경

기준은 legality174 map01이다. SPI `error_code`는 reset 직후0이고, 모든 오류에서 `fault`와 같은 에지에 함께 기록된다. 이후 둘 다 유지된다. 따라서 도달 가능한 상태에서는 `!fault → error_code==0`이다.

이 성질을 이용해 fault 전에는 오류가 없는 에지에도0을 명시적으로 쓴다. 코드 갱신 여부를 결정하던 복잡한 enable 조건을 없애고, 첫 fault 뒤의 유지 조건만 남긴다. 우선순위는 hard fault9 → 잘못된 응답7 → SS 겹침1 → pending의 decoded error다. 코드0인 정상 명령은 fault를 만들지 않는다. 입력을 한 에지 미리 샘플링하거나 명령 단계를 추가하지 않았다.

이는 이전 errorhold174의 합성 속성 변경과 다르다. 이번에는 SPI 기능 RTL의 도달 상태 불변식을 사용한다. reset으로부터 불가능한 `fault=0,error_code!=0` 상태까지 동치라고 주장하지 않는다. 기존 loader의 reject_state 변경은 바이트 그대로 유지한다.

## 검증 범위

- 구·신 실제 SPI RTL: 557,056조건에서 fault·코드·CHECK 상태·명령 펄스·카운터 비교 통과. 오류 없음, 동시 오류, code0~15, fault 이후 모든4비트 코드 유지, 비동기 reset을 포함한다. 잘못된 우선순위·hold 제거 변이2개 모두 검출했다.
- 실제 SPI→boot→READ16 연결: 1,126,009에지 / 100읽기 / 7ACK / 19잘못된 응답 / 72취소 / 2겹침 통과.219 wire frame, SCK2.625MHz·SS 간격2µs 유지. READY/count를 설정한 연결 시험이며 전체 ROM 적재·새 게임 부팅은 아니다.
- FPGA: 15,061LE / 963LAB / 36M9K. 변경 대상 `check_busy → error_code` setup +0.828ns. 전체 실제 클록 setup +0.246ns, hold +0.156ns. 기존 더 엄격한 구현 예산은 -0.052ns로 별도 보존한다. 클록·SDC·false path·multicycle은 변경하지 않았다.
- 외부 조건: PSRAM70ns·PCB 왕복4ns 가정의 여유 +3.899ns, SNES 읽기78.805ns < 모델270ns, SPI 응답162.819ns < 반주기190.476ns. records/prepared/pad 묶음 여유도 양수이며 동기화 첫 단계 fanout11개가 각각 다음 단계1개로만 연결된다.
- 기존 reset recovery/removal 음수 경로24개는 별도 기록한다. native 영상 payload의 음수 reset 경로는0이다. 이 조건부 디지털 검사로 전체 IO·CDC·MTBF나 미측정 전기 특성까지 승인했다고 해석하지 않는다.
- 이전 cross174의 픽셀/수집기 검증, batch174의 실제 C 변환·SNES229,376픽셀 및 ARM 전체 링크를 재사용한다. 해당 소스는 바뀌지 않았다. MCU 여유1,040바이트이며 새 최대 길이 로그3934/4096바이트 검사도 통과했다.

## 패키지와 실기 판단

선택 FPGA는 `nes-errorzero174-map01`, MCU는 `probes/nes-batch174/arm01`이다. Quartus ASM/CPF와 압축 왕복 검증을 거쳤으며 매핑된 SNES ROM4096바이트가 기존172 코드와 일치한다. 기존173 패키지의 게임·기본 메뉴·164 복원 파일을 바이트 그대로 보존했다. 배포 ZIP 전체 파일의 길이·SHA256을 다시 읽어 확인했다.

| 파일 | SHA256 |
| --- | --- |
| NES174-SMB3-VIDEO-BATCH.zip | `6624455010e05fe425ec1b81fd105e2eaddf21ef795470aa047da03c77940468` |
| firmware.stm | `89c98add72ed3a6d983f9961c96b7ac2d7da6a889ba0fc5d5595da25dacfaa87` |
| fpga_n174.bi3 | `23e71b323e617d4bb23e3703d7107e0b65f7e9f2d2974b3805d8dd8d6e8ef9aa` |

FPGA→MCU ABI1741·예외32비트와 묶음 전송을 함께 적용하므로174 MCU와173 FPGA를 혼용하지 않는다. 실행 후 약60초 한도·정지 후 로그·사운드·입력·메뉴 복귀 계약은 유지한다. 로딩 적재·비교 절차는 줄이지 않았다. 세이브 SRAM·두 번째 MCU 프레임 버퍼·RUN 중 SD 쓰기는 추가하지 않는다.

**다음 작업은 동일 모델 검증 반복이 아니라 SMB3 실기1회다.** 화면이60초 동안 계속 움직이는지와 실제 끊김, 사운드·입력·메뉴 복귀를 함께 확인한다. 남는 비용인 전체 map/CGRAM/OAM/HDMA 전송과 패킷별 ACK는 실기 측정에 따라 우선순위를 정한다. 연속 AV → 장기 플레이/오류·리셋 로그 → 입력 유지 순서다.

[설치·촬영·로그 안내](nes-game174-ready.ko.md) · [검증과 해시](../analysis/errorzero174-verification.json) · [인계](../cores/nes/HANDOFF.ko.md)
