# NES181 — 화면 복구와 약60fps를 함께 설계하는 전송 계약

## 판단과 작업 의미

사용자가 지적한 재작업 위험이 실제로 있다. 최근 ROM 응답 로컬 캡처와 CDC 배선 개선은 정해진 클록에서 안전하게 동작하기 위한 기반이다. 전송 바이트 수는 줄이지 않으며, 전체 setup도 아직 −1.408ns로 실패다. 이 결과를60fps 개선으로 계산하지 않는다.

부분 행 수집·다음 정상 행 복구는 첫 레벨에서 프레임이 거부되는 문제를 해결하기 위한 후보이며 재사용 가치가 있다. 하지만 현재 전송/표시 스케줄을 그대로 완성한 뒤 나중에60fps를 붙이는 순서는 변경한다. **전송량과 다음 프레임 소유권을 먼저 제한하고, 같은 계약 아래 배선과 실제 ROM 표시를 진행한다.** 모든게임60fps 또는 재작업0을 보장하는 것은 아니다.

이 문서는 기존 완료 결과를 대체하지 않고 NEXT 우선순위만 변경한다. 배포180·GBC·164복원·세이브SRAM은 그대로다. 새 FIT/펌웨어/ZIP은 만들지 않았다.

## 재사용한 데이터와 산출값

`tools/nes_cadence181.py`는 wire181/test02의 실제 RTL 전송 기록 및 client181/test05/normal의 실제 C 요청275개·실제65816 응답275개를 재검사한다. 원시 파일 SHA256와 현재 관련 소스를 결과에 고정했다. 새 실기·새 RTL 시뮬레이션이 아니다. 두 시험은 **서로 다른 합성 장면**이므로 시간을 더해 종단 실측값으로 표현하지 않는다.

paired ARM의 `nes_native165_bulk.inc`는 APB2 84MHz, BR=4(/32)인2.625MHz SPI를 사용한다. 전송 하나마다 명시적2µs 대기4회가 있고, 바이트 사이 소프트웨어 처리·guard·서비스·추가 polling 시간은 별도다. FPGA 수신과 SNES 송신은 runtime의 같은 transfer를 사용해 직렬로 진행한다.

60Hz에서 순수 bit 예산은 **5,468.75바이트/16.667ms**다. 이는 한 방향만의 예산이 아니라 같은 SPI 자원을 사용하는 전체 트래픽의 상한이다. 검증된 속도보다 임의로 SPI를 높여 해결됐다고 하지 않는다.

| 경로·fixture | 현재 전송량 | 시간과 의미 |
|---|---:|---|
| FPGA→MCU, raw0행 | 4,861B | 이전 RTL 모델15.479ms |
| FPGA→MCU, raw1행 | 6,559B | 이전 RTL 모델20.847ms |
| FPGA→MCU, raw7행 | 16,774B | 이전 RTL 모델53.164ms |
| MCU→SNES, normal 소형 장면 | 최소6,730B/29요청 | bit+최소transaction gap만21.206ms |
| MCU→SNES, raw1행 또는7행 소형 장면 | 최소11,055B/47요청 | 같은 하한34.819ms |

SNES 하한은 각 요청 길이+35바이트(E0 사전상태16, E1 command/CRC3, 최초 성공 E0 ACK16), 요청마다 최소3transaction으로 계산한다. 추가 ACK 대기/CPU변환/PPU복사/서비스는 제외했으므로 실제 속도 추정이 아니다. normal gen15→16은6개 section이 완전히 같은데도6,730B를 다시 보냈다. **이미 SNES 한 구간만으로60fps 불가능한 구조**다.

기본 map4096+CGRAM512+OAM544=5,152B를 매번 전송한다. raw는 행 수가1이어도 section5 전체3,418B를 전송하고, SNES는 raw 진입/유지/종료에서 전체 inactive bank를 재구축한다. 기존 max 시험의7복사 vblank+최종공개는 전환 복구에는 유용하지만 매 프레임 경로로 쓸 수 없다.

## 이번에 구현·검증한 압축 후보의 범위

오프라인 codec은6비트 색10개를 한96비트 record에 담는다. kind7, index4096+시작위치, payload상위4bit 개수+하위60bit 색이라는 **미할당 실험 형식**이다. 기존 record envelope4B+payload8B=12B로 계산하며, 실제 SPI block 구성·CRC·양쪽 decoder에는 아직 적용하지 않았다. 기존1811/1812와 호환되지 않으므로 그대로 장치에 전송하면 안 된다.

- 실제 저장 raw0/1/7행, 총2,048픽셀 왕복 일치.
- 별도512조합: 모든 색값·10개 단위 꼬리·최대1,792픽셀·generation65535 포함.
- 오류9종: 누락/중복/역순/세대/종류/개수/패딩 검출.
- raw1행 record1,536→312B, raw7행10,752→2,160B(약79.9% 감소).

그러나7행 전체 record는 헤더/polling도 제외한 채6,457B가 남는다. **픽셀 packing 하나만으로는 목표를 충족하지 못한다.** 기존 geometry/행별 동일값 반복도 묶어야 하며, 양방향 실제 예산으로 채택 여부를 결정한다. 이 codec의 결과는 절감 가능성 증명이며 생산 구현 완료가 아니다.

## 세 가지 소유권과 처리량 조건

1. FPGA capture lease: 현재 fetch는 `!owned && !retiring`이고 line7/dot257일 때만 시작, line232/dot1에서 종료한다. exporter COMMIT이 transport에 받아들여질 때 release한다. **SNES 최종 display ACK까지 FPGA lease가 유지된다는 설명은 틀리다.** release마다8,192클록 scrub도 있다.
2. MCU receiver/plan: COMMITTED 뒤 conversion→sink→최종 display ACK까지 한 workspace를 소유한다. 그동안 다음 frame을 poll하지 않는다. 이 시점과 FPGA release는 별개다.
3. SNES staging/display: 현재 표시 뱅크와 작성 중 뱅크의 기준 세대가 다르다. 수신 ACK와 최종 표시 ACK도 구분한다.

262×341dot/60Hz 참조 계산에서 수집 종료→다음 시작 간격은12,873dot≈2.401ms다. 실제 소스의 위치를 고정한 참고 모델이며 실측 NTSC 주파수/FPS가 아니다. 프레임 종료 뒤 수십ms 전송으로 capture lease를 잡으면 다음 시작을 놓친다. 지연 합계만16.7ms에 맞추는 접근도 불충분하다. 파이프라인 지연이 여러 프레임이어도 처리량은60Hz일 수 있지만, 공유SPI 서비스 시간의 합과 재사용 불가능한 버퍼 점유시간은 반드시 만족해야 한다.

목표 계약은 `source_frame → immutable capture/snapshot → transfer → target-bank commit → visible ACK`다. 다음 프레임 수집은 전송/표시 대기와 분리하되, 쓰는 중인 데이터를 전송하거나 이전 세대를 덮어쓰면 안 된다. 부분 행 streaming 또는 최소 snapshot 중 선택은 실제 RAM/포트/수명 표로 결정한다. 단순 전체 double buffer 추가는 금지: ARM 여유1,032B, FPGA963/963LAB·38M9K이며 남은 M9K만으로 구현 가능하다고 가정하지 않는다.

## 재사용과 변경 경계

| 유지할 부분 | 성능 경로에서 달라져야 하는 부분 |
|---|---|
| PPU색 정렬, 부분 행 보존, 렌더링 중단·재개 복구 | 수집 완료 후 긴 lease 점유·다음 시작 누락 |
| ROM qualified reply/요청 소유권·타이밍 계약 | 단일픽셀 record, 반복 geometry·행 정보의 직렬 전송 |
| CRC/버전/세대/STOP/오류 시 기존 화면 보존 | 작은 patterncallback마다 별도packet·ACK 왕복 |
| 변환 결과의 byte/pixel 정답 fixture | 매번 map/CGRAM/OAM/HDMA 전체 송신 |
| inactive bank 완성 후 공개 | raw매프레임 전체bank rebuild; scenechange keyframe으로 범위 축소 |

차분은 **대상 뱅크가 실제로 갖고 있는 기준 세대**에 적용한다. 직전 표시 화면과 같다는 이유로 다른 뱅크의 쓰기를 생략하면 안 된다. BEGIN에 base/target generation·bank를 묶고, stale base/STOP/실패/재시작은 invalidate→bounded keyframe으로 복구한다. dirty는 신뢰 가능한 쓰기 추적 또는 정확한 비교로 계산한다. CRC/hash 단독 일치로 갱신 생략을 정당화하지 않는다. 기존 BG key scratch는 변환 후 raw 공간으로 재사용하므로 영구 cache가 아니다.

## 앞으로 실행할 순서와 중단 조건

1. **전송 형식·RAM/포트 시간표를 공동 확정:** 현재 결과를 기준으로 raw 묶음+geometry 묶음/반복 제거+작은 CHR callback 집계와 sink section 차분을 같은 바이트 예산에 계산한다. mutable CHR/팔레트/스크롤도 포함한다. capture와 export의 겹침을 별도 RAM 무한 추가 없이 설명하지 못하면 그 구조를 먼저 변경한다.
2. **짝지은 작은 구현:** producer packetizer→실제 C receiver와 실제 C sink→65816 bank기준 차분/최종ACK를 최소 실제바이트 시험으로 검증한다. 정상 동일프레임은 descriptor만, 변화한 데이터만 갱신. raw/normal전환은 안전한keyframe으로 복구하되 steady raw마다 전체복사를 하지 않도록 한다. old181과 새버전은 명시적으로 구분한다.
3. **host RUN/STOP 배선 수정도 위 수명 계약에 맞춤:** raw STOP/reset/error는 즉시 버스출력을 해제하고 pendingpacket/ACK를 폐기한다. relatedPLL 타이밍을 유지한다. 무효화와 마지막 표시 완료를 혼동하지 않는다. replyjoin181/map02는 분석 기준으로 보존하며 아직 채택하지 않는다.
4. **새 공통 구조가 준비된 뒤 한 번의 정당한 통합FIT/ARM검사:** 전체 실제클록·조건부IO/reset·RAM/IRQ·부정테스트 통과 후 설치 후보. 이전 독립 시험/긴 부팅/seed/동일배선반복FIT는 생략한다. throughput 계산이 안 맞으면 먼저 SPI하드웨어 전송 개선 또는 MCU경유를 줄이는 구조의 비용을 평가하며, 무조건 압축만 덧붙이지 않는다.
5. **최소 SMB3 실기 우선:** playerselect→worldmap→숫자1+A→이동/점프/스크롤에서 영상지속·사운드·메뉴복귀 및 실제 표시 간격을 확인한다. 첫 복구판이60fps가 아니면 정확히 명시한다. 완전한 모든게임 cache 구현을 기다리며 실기 검증을 미루지는 않는다. 단, 그 복구판의 버퍼/세대 계약은 위 성능 경로와 동일해야 한다.

성능 판정은 source NES frame번호·capture누락·전송량/서비스시간·실제공개시각·반복프레임 간격(p50/p95/최대)을 사용한다. 수집 generation은 건너뛴 원본frame을 세지 않으므로 ACK횟수/60초만으로FPS를 주장하지 않는다. 정상 플레이 구간의 약60Hz 지속과 전환 복구 최대 지연을 분리한다. SPI한주기 budget에는 pad/audio/guard를 위한 실측 여유도 남겨야 한다. 사운드·입력 polling을 희생해서 숫자만 맞추지 않는다.

## 근거·재현·미완료

[분석 결과](../analysis/cadence181-verification.json), [이전 배선 결과](nes-replyjoin181-contract.ko.md), [기존 wire](nes-wire181-contract.ko.md), [기존 SNES client](nes-client181-contract.ko.md).

새 로컬 단계는 `probes/nes-cadence181/audit04`다. audit01 상대경로 처리 오류, audit02 SEAL ACK를 일반ACK와 동일하게0으로 가정한 검증기 오류는 보존했다. audit03은 첫 성공, audit04는 fetch/실제SPI소스 고정 검사를 더한 선택 결과다. RTL/C/SNES 생산 소스는 변경하지 않았다.

재현: `python -B -X utf8 tools/nes_cadence181.py --workspace <workspace절대경로> --out <새절대경로>`. 완료 디렉터리에는 덮어쓰지 않는다. 아직 미완료: 생산packing/delta/overlap, hostactivation timing, 통합FIT, 실기 첫레벨 복구, 실제60fps·장시간·입력유지.
