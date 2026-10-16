# NES192 실제 CHR-ROM 읽기 경로와 작은 원본 캐시

PR117 OPEN 같은 branch. 배포186/GBC164/세이브 SRAM은 변경하지 않는다. 새 펌웨어·실기 ZIP·FIT 또는60fps 승인 단계가 아니다.

## 작업 의미와 구현

191의 metadata 계획→타일 생성기를 변경 없는 배포 `nes_native_arbiter165`와 `nes_rom_physical READ16`에 연결한 후보다. 목표는 CHR 픽셀의 MCU 왕복을 제거하면서 코어 CPU/PPU의 메모리 우선권을 유지하는 것이다. 이번 후보는 실제 읽기 회로까지 연결했으며, 계획 통신·CDC·188 읽기창·실제 SNES 소비기는 아직 미연결이다.

`nes_source_tile192`는 NES clock에서 동작한다.191의 `{tag,plane,row}`를 물리 주소 `0x200000..0x21ffff`로 바꾸고 기존 중재기의 fill 포트를 사용한다. source ready, CHR-ROM 여부, 쓰기 중 여부, 캡처 시점 content epoch와 live epoch, frame ownership/geometry/generation을 확인한다. 잘못된 입력은 단순 무한 대기가 아니라 오류로 처리한다.

현재 수집기가 저장하는 tag는 logical bank 번호가 아니라 실제 fetch의 physical CHR tile이다. 불변 CHR-ROM에서는 mapper bank가 이후 바뀌어도 같은 physical byte를 읽을 수 있다. CHR-RAM에는 이 가정을 적용하지 않는다. CHR-RAM은 명시적으로 거부하며 내용 버전과 snapshot이 필요하다. MMC4/5 호환성을 이 후보가 확보한 것은 아니다. 현재 읽기 범위와 qualified slot은 기존 NTSC/MMC3 범위다.

`captured_epoch`는 upload 시점이 아니라 geometry 수집 시작 시점에 controller가 고정해야 한다. ROM reload/쓰기/state 변경 시 `live_epoch`를 갱신하고 쓰기 동안 `source_writing`을 표시해야 한다. 아직 이 epoch 생성기와 frame-start latch를 실제 board에 구현하지 않았다.32bit epoch가 retained cache/frame 동안 한 바퀴 돌아 같은 값이 되어서는 안 되며, 그 전에 common reset/flush가 필요하다.

`nes_chr_cache192`는 physical tag18bit/유효 lane16bit/content epoch32bit와 원본16B 한 타일만 저장한다. 검증된 응답만 cache에 넣는다. hit도 등록된 한 번의 응답으로 전달하고 요청 generation을 유지한다. frame geometry가 바뀌더라도 같은 불변 ROM content라면 cache를 재사용할 수 있다. STOP/reset/쓰기/내용 epoch 변경/소유권 오류는 유효 비트를 폐기한다. captured/live epoch가 동시에 새 값으로 바뀌어도 cache 자체의 이전 epoch와 비교하여 오래된 데이터가 남지 않는다.16B 배열에는 reset을 넣지 않는다.

STOP은 공유 물리 reader를 강제로 reset하지 않고 기존 중재기로 drain한다. wrapper의 drained는 cache가 아니라 실제 reader의 flush 완료다. reset은 reader와 공통으로 적용해야 한다. cache hit는 PSRAM을 사용하지 않으며 miss는 원래 qualified slot·core_safe 조건을 따른다. core 요청의 우선권과 seven-edge 응답 계약은 변경하지 않았다.

191의4096클록은 임의 fixture 지연에 대한 한도였다.192는 귀선 구간까지 한 프레임 가까이 기다릴 수 있으므로 타일당1,048,576 NES클록(약48.8ms)의 유한 한도를 사용한다. 이는 합법적 슬롯 대기를 포함한 보호 한도이며 목표 지연을 늘려 해결했다는 뜻이 아니다. 실제 단계별 timeout/STOP controller와 전체 프레임 예산은 별도로 연결해야 한다.

## 선택된 검증

SELECT `test03/evidence01`. `test01`은 캐시 없는 baseline, `test02`는 cache 도입 후 중간 통과 결과로 보존한다. test03에서 captured/live epoch 동시 변경에 대한 cache 자체 epoch 무효화를 보강했다. 과거 실행 파일은 수정하지 않았다.

- 191에서 변경 없는186 실제 C 변환기로 만든8개 합성 장면97계획/1840B를 그대로 사용했다. 모든 BG/OBJ 출력 byte·slot·generation·길이가 일치한다.
- 실제 배포 중재기와 READ16 회로,21.477MHz/168MHz clock,0/3.5ns 두 위상,70ns PSRAM pin fixture를 사용했다. 실제 메모리 칩이나 board timing 검증이 아니다.
- NTSC242..259줄,12 master클록당 한 슬롯을 모델링했다. core_safe는1, 매10번째 슬롯에 코어 요청을 넣었다. 코어 응답 주소·data와 우선권을 검사했다. DMA/APU/CPU cache miss 등 실제 grant 제한은 모델링하지 않아 낙관적 일정이다.
- 9개 경계 조건: mutable source 거부, capture/live epoch 불일치, 쓰기 중 거부, 실제 읽기 중 epoch 취소, 실제 읽기 중 STOP·drain, drain 이후 재시작, warm tile 무재읽기, write window+새 epoch 후 새 바이트, captured/live 동시 갱신 후 새 바이트.
- 원본·현재 소스·선택된 fixture를 해시로 고정했다. 이전1862799/실기11/1878/188142/189328/190209/191181파일은 불변이다. 라이선스 서버/서명 원본은 증거·Git에 넣지 않는다.

## 처리량 결과와 결정

| 시험 | cache 없는 원본 읽기 |16B cache 사용 | 해석 |
|---|---:|---:|---|
| 기존8장면 합계 |1304|1262|42회 감소(약3.22%); 큰 개선으로 주장하지 않음 |
| 같은 BG 계획512회 재생 |8192|16|warm 반복 상한 시험; 실제 converter가512개 중복 슬롯을 만든다는 뜻 아님 |

반복 시험은 동일8192B 출력에 대해6읽기 구간/83.837ms→1구간/1.895ms였다. 이는 같은 계획을 반복한 인위적 cache 효과 시험이며 게임·스크롤 FPS가 아니다. 작은8장면은 각각 한 읽기 구간, 약0.724..0.762ms다. 시작 시점을232줄로 잡은 fixture의 대기 포함 시간이며 전체 영상 파이프라인 지연도 아니다.

순수 slot 상한은 `(260-242)*341*4/12=2046` byte reads/frame이다. source 원본이 cold일 때8192B를 매번 읽는다면 이 제한만으로도 한 프레임에 완료할 수 없다. 여기에 실제 core 경쟁과 타일 계획 전환 비용이 추가된다. 따라서 **기존 core 우선권을 풀거나 timeout만 늘리지 않는다.** 불변 physical content 재사용과 변경분 중심 공급을 직접 전송 경로와 함께 진행해야 한다.

한 entry는 대부분의8장면에서 약3%만 줄였다. 안정된 pattern/plan key 재사용의 필요성을 확인했지만, 캐시만 늘리면60fps가 된다는 결론은 아니다. 같은 타일 재생의 큰 개선율을 실제 scrolling에 적용하지 않는다. 대표 first-level source/converted-output 동일 generation 데이터는 아직 없으며, 사용자 tile1+A→RIGHT+B 유지+A press/release 절차도 이번에 실행하지 않았다.

## 자원과 다음 연결

191의32B tile buffer에192의16B source cache를 추가했다.512타일 전체 캐시나 save SRAM은 사용하지 않는다. payload48B 외 tag/mask/epoch/request/response 레지스터와 mux 비용이 있다.188의4M9K 추정과 함께 현재24LAB/14M9K 여유에 들어가는지는 미합성이다. 구조체·코어 전체 ARM stack 또는 SNES3776B body도 이번에 재빌드하지 않았다.

다음은192에서 생성한 tile을188 불변 읽기창에 SNES-ready section으로 직접 공급하는 최소 경계다. 실제 계획 codec/CDC/epoch producer/descriptor/STOP/최종 displayACK를 연결하고, output slot의 안정된 내용 key·delta를 함께 유지한다. 원본 cache의 불변 content epoch와 frame generation/전송 token/표시 ACK를 하나로 혼용하지 않는다. geometry/raw/palette/OBJ/OAM/HDMA는 현재 검증된 의미를 보존한다.

자원·포트·source reads·계획 byte·카트리지 전송·VBlank/표시 완료를 포함한16.67ms 예산을 만족하는 최소 경로 후 FIT/IO와 SMB3 실기로 진행한다. 일반 관측기 확대/무변경 boot·FIT·186/044 반복은 하지 않는다. 장기 플레이와 오류·reset 로그·입력 유지 검증은 AV 약60fps 확보 다음이다.
