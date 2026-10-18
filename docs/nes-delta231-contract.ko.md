# NES231: 입력·출력 공동 증분 C 후보와 남은 프레임 예산

PR126 머지 `a86ba0504eae1ce5761157486b85c8e22022e969` 이후 작업이다. 설치 가능한 시험판은 아직227이다. 이번 코드는 후보 디렉터리에서 검증하며 기존 생산 C/RTL·GBC164·게임 세이브 SRAM을 수정하지 않는다.

## 작업 의미

60fps를 위해 같은 스크롤 자료의 **입력과 출력 모두에서 반복 전송을 줄이는 실제 C 후보**를 만들었다. 디버그 항목 추가가 아니라 화면 데이터 경로 변경이다. 이전230의 바이트 모델을 기존 버퍼 안에서 작동하는 수신기·planner·sink로 구체화했다. FPGA 증분 생성기와 실제65816 소비기는 아직 연결하지 않았으므로 실기60fps 구현 완료나 새 펌웨어 배포를 뜻하지 않는다.

## 구현과 데이터 수명

- 입력 geometry5741B는 기존 `nes_native165` 배열에 직접 적용한다. 첫 프레임은 순서대로 전체 literal을 받아야 하며, 이후에는 정확한 base serial/불변 ROM epoch에서만 증분을 허용한다. 리터럴, 정확한66B 맵 행의 한 칸 이동+경계 word, 연속 raster 행의 동일 XOR mask를 지원한다. 행 이동은 나머지64B의 동일성이 확인될 때만 생성하며 그 외는 literal이다. MMC3 최종 bank 값만 보고 행별 상태를 생략하지 않는다.
- geometry 검증 후 기존 `logical_record`로 요구 타일을 다시 열거한다. `required/raw_pixels` union 때문에 raw 픽셀은 이 열거가 끝난 뒤 다시 받는다. 이 메모리를 보존 캐시라고 오인하지 않는다.
- 출력은 맵4096B/CGRAM512B/raw-tail2297B를16B 단위로 추적한다. 두 목적 은행의 stale bitmap을 함께 보존하고 변경은 양쪽에 표시한다. 표시 ACK를 받은 목적 은행만 깨끗하게 만든다.
- 이전 raw 출력은 `bg_keys/patch` union을 BG/OBJ scratch로 덮어쓰기 **전에** 비교한다.16B 타일 scratch와249B 모드 테이블을 사용하며 전체 이전 화면을 복제하지 않는다. raw가 없는 프레임을 거치면 양쪽 raw 기준을 무효화한다.
- sink는 실제 E1 패킷을 생성한다. OAM 반복 압축과 HDMA 경로는 기존227을 사용하고 변경된 map/CGRAM/raw-tail만 전송한다. BEGIN/SEAL 버전2311, SEAL222B(기존168+dirty54)로 기존227 소비기와 혼용할 수 없다.
- 입력 오류나 부분 갱신은 원본을 되돌리지 않고 세션을 실패 상태로 만든다. 공통 STOP/reset으로 입력·출력·resident·FPGA·SNES 기준을 함께 폐기해야 한다. 수신 END/타일 consume/화면 표시 ACK는 서로 대체하지 않는다.

입력 API는 바깥 transport의 CRC·token·길이 검증 이후에 호출하는 후보이다. Python encoder의 fixture record 포맷을 생산 SPI 프로토콜로 확정한 것이 아니다. 실제 FPGA 송신기에서는 아직 확정되지 않은 base 저장 RAM/포트, 전송 완료와 base 교체 시점, STOP·부분 전송·다음 capture 동시성까지 구현해야 한다.

## 같은 실제 스크롤 자료의 결과

230의 관측 자료와 생산 collector/exporter 재생 결과를 재사용했다.905..975의71프레임 중 두 은행을 채우는 처음2개를 제외한907..975의69개가 아래 평균/최대의 대상이다. 새로운 실기 측정은 아니다.

| 항목 | 평균 B/프레임 | 최대 B/프레임 | 근거 |
|---|---:|---:|---|
| 기존227 출력 E1 | 5,094.70 | 6,103 | 230의 실제 C 패킷 |
| 후보231 출력 E1 | 1,483.83 | 2,147 | 이번 실제 C 패킷, 평균70.87% 감소 |
| 후보 입력 | 815.94 | 1,654 | 실제 적용된 record + 모델 framing/control |
| 입력+출력 기본 합 | 2,299.77 | 3,627 | 계획·상태 확인 등 제외 |
| 준비 확인을4패킷마다 하는 비용 시나리오 | 3,185.67 | 5,333 | 계획/상태/bulk 제어 모델 포함 |
| 매 패킷마다 준비 확인하는 비용 시나리오 | 3,670.88 | 5,933 | 같은 모델, 빈번한 확인 |

SPI2.625MHz의60Hz당5,468.75B와 비교하면 기본 합/4패킷 시나리오는69개 모두 이내, 매 패킷 시나리오는2개 초과다. **시나리오는 실제 runtime 상한이 아니다.** 상태가 준비되지 않으면 폴링이 반복되고 CPU 계산·SPI 간격·PSRAM 경합·capture 지연도 남는다. 최대5,333B도 바이트 시간만16.25ms여서 안전 여유가 있다고 승인할 수 없다. 처음2개의 cold 업로드는 이 표에서 제외했고 전체 값은 JSON에 보존했다. 새 encoder의 계산 비용도 계측하지 않았다.

### SNES 쪽에서 추가로 확인한 병목

기존212 소비기는 raw가 있으면 매번2048B 전체를 VRAM으로 올린다. 따라서 SPI만 증분화해서는 충분하지 않다. 이번 분석은 **raw VRAM 업로드도 증분화한다고 가정**한 것이다.

| SNES 업로드 모델 | 평균 charge | 최대 charge | 현재4192 예산 초과 |
|---|---:|---:|---:|
| 바뀐 구간만, 연속 구간만 합침 | 5,145.74 | 6,976 | 58/69 |
| 검증된 비활성 WRAM의 작은 간격도 함께 업로드 | 3,922.55 | 5,360 | 18/69 |

charge는 바이트 및 보수적인 작업비용 단위이며 실측 CPU cycle이나 실제 전송 바이트와 같지 않다. 기존 모델의 DMA당96, 마지막 palette/OAM/register1568을 유지했다. map/raw 구간 사이96B 이하를 함께 DMA하면 불변 구간을 재전송하는 대신 DMA 설정 횟수를 줄일 수 있다. SPI로 그 간격을 다시 보낼 필요는 없지만 **목적 WRAM의 유효 base/coverage를 증명한 경우에만** 가능하다. 패턴 chunk는2048B 한계, map/raw 합친 범위는4096B 한계를 적용했다.

이 결합은 아직65816에 구현하지 않았다. 결합 뒤에도18개가 현재 예산을 넘는다. 따라서 A 경로를60fps로 승인하지 않는다. 단순히4192/96/1568을 낮추거나 강제 blank·프레임 생략으로 합격 처리하지 않는다. 초과 프레임만으로 장기 평균60fps의 불가능성을 증명한 것도 아니다. bounded queue, 최대 화면 나이와 실제 실행 시간을 함께 확인해야 한다.

## 검증 범위와 자원

- 실제 C 입력 수신→planner→sink71프레임: geometry/raw/metadata가 기존227과 byte-exact,186 reference4,066,624 checks 통과.230 raw RGB36,352픽셀 비교 재사용 경로도 통과했다.
- 입력18오류 경계(기준/epoch/serial/순서/누락/겹침/범위·정수 wrap/raw 색·순서/행 연산) 거절, zero-span 및 generation65535→0 성공.
- 별도366개 합성 프레임에서 두 은행의 metadata 복원, raw 유무 전환, 팔레트·epoch·원형 맵 경계 통과. 기존resident11경계와 dirty5경계/은행 교대 확인. 이 소비기는 C 검사용 모델이다.
- ARM Cortex-M4 실제 object 컴파일 및 구조체 크기: 입력 관리36B+출력 관리124B=**추가 상주160B**. 기존9880B 입력/15912B video 크기는 그대로다. host 시험의 oracle용 복제 구조체를 배포 메모리로 계산하지 않는다.
- 기존1800B margin에서 상주160B만 뺀1640B는 산술값이다. planner280B, material336B+changed48B, dirty sender312B, sink312B 등의 call chain과 IRQ를 포함한 **full RUN 승인은 아직 없다**. object text 증가도 새 firmware 크기 검증을 대신하지 않는다.
- FPGA 여유159LE/2LAB/9M9K, SNES body224B는 기존227/224 값이다. geometry5741B 저장만 단순6M9K 상당이므로 포트·비교·shift/raster 제어 배치가 빠듯하다. 이번에는 FIT/STA·ROM 크기·실기 자원 적합성을 새로 증명하지 않았다.

230의 관측 어댑터 한계도 그대로다. Mesen OBJ plane timing을 native phase에 대응했고,193/194 raw는 명시적 fallback 및 동색 canonical palette index이다. 전체 NES 코어 cycle 등가성, 전체 Mesen/SNES 합성 화면, 실제65816 실행, 실기 FPS 검증이라고 부르지 않는다. ACK와 ROM read는 fixture이다.

## 다음 작업과 채택 조건

1. **231 C 패킷을 실제65816 소비기에 연결하는 최소 후보**:16B coverage/base 검사, raw sparse upload, 비활성 WRAM에서 안전한 DMA 구간 결합, STOP/잘못된 SEAL/표시 ACK를 함께 검증한다. 같은69개 스크롤 프레임의 실제 명령 실행·최대 VBlank·화면 나이를 비교한다. 단독 codec 실험이나228 실패 후보 자동 재개로 바꾸지 않는다.
2. 이와 함께 전체 RUN/IRQ 메모리와 source5741B 저장/포트·제어 상한을 확정한다. 가능한 제어 자원 근거 없이 FIT를 반복하지 않는다. 기존union 재사용 수명과 source release 이후 다음 capture를 침범하지 않는지가 조건이다.
3. A가 전체 예산을 만족할 가능성이 확인될 때만 FPGA 생산 증분 송신기·SPI CRC/token·세션 base를 연결한다. 자원 또는 총경로 예산이 성립하지 않으면 **B(준비된 metadata를 병렬 aperture로 전달/계산 위치 변경)**로 전환한다. ARM→SPI→aperture 재충전은 우회가 아니다. B도 SNES VRAM/DMA 병목을 자동으로 없애지 않으므로 이번 소비기 개선과 예산 자료를 재사용한다.
4. 최소 경계 검증, full ARM/whole-board gate, paired build 뒤 첫 레벨 숫자1+A→오른쪽+B 유지/A 반복으로 실기 시험한다. 같은227/044 재시험은 필요 없다.

목표 ROM은 Super Mario Bros 3 (J), SHA256 `dbb1cb5e18b091ca9101b1c2f5a5d6bdbeaa4a30ae1a504251310f6765cabb49`다. 변경은 화면 표현 계층이며 mapper 물리 tag/행별 bank/mask 의미를 보존한다. MMC4 latch/MMC5 ExRAM·확장음원/CHR-RAM 호환은 이번 시험으로 증명하지 않았으며 mutable source는 기존 거절 조건을 유지한다. 향후 강제 state load/reset은 양쪽 delta 기준을 무효화해야 한다. frame skip에서도 capture/transport/display 완료를 구분하고, mute는 입력·출력 base를 변경하지 않아야 한다. 해당 사용자 기능을 이번에 구현한 것은 아니다.

## 재현과 보존

선택: `probes/nes-delta231/test07`, `bounds02`, `arm03`, `analysis03`. 이전 test01 컴파일 경고 실패, arm01 sandbox DLL623, literal-only test02와 중간성공/분석도 별도로 보존한다. analysis01은 기존230 analyzer로 test02를 분석한 파일이며 최종 모델로 사용하지 않는다.

```powershell
python -B tools/test_nes_delta231.py --rom <user-ROM> --out C:/temp/231-test
python -B tools/test_nes_delta231_boundaries.py --out C:/temp/231-bounds
python -B tools/check_nes_delta231_arm.py --candidate C:/temp/231-test --out C:/temp/231-arm
python -B tools/analyze_nes_delta231.py --host C:/temp/231-test --out C:/temp/231-analysis.json
```

기존230 로컬 봉인 자료와227/225의 pinned source가 필요하다. 신규 출력 경로만 허용한다. 원본 ROM/게임 trace/바이너리는 Git에 넣지 않고 공개 source·검증 요약·hash만 기록한다. 이번 단계에는 새 firmware/FPGA/ZIP 또는 실기 설치 요청이 없다.
