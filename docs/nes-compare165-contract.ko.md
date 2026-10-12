# NES165 타이밍 후보 비교 — 기존 구현 유지

**이번 후보는 모두 미채택이다.** 실제 게임 영상 전달 목표는 아직 완료하지 못했다. 선택 구현은 [predecode165/map03](nes-predecode165-contract.ko.md), setup−0.153ns/hold+0.155ns이며 그대로 유지한다. [이번 검증](../analysis/compare165-verification.json) · [현재 인계](../cores/nes/HANDOFF.ko.md).

## 무엇을 시도했는가

1. map01: 응답이 없으면 주소 비교를 통과시키는 조건을19개 비트에 분배하고 keep 조합 노드로 유지했다. 카운터 경로는−0.153→+0.453ns가 되었지만 로더 상태 경로가−0.222ns로 나빠졌다.
2. map02: WRITE/HOLD 상태 전환 허용 조건과 오류 코드 처리를 분리했다. 해당 경로는 통과했지만 reset release→명령 오류 캡처가−0.300ns였다.
3. map03: CHECK_BEGIN/READ 오류를 기존 캡처 edge의 두 레지스터에 나누고 기존 명령 실행 edge에서 합쳤다. 전체 최악은 load_end→로더 fault −0.367ns, 다른 캡처 경로도−0.240ns였다.
4. map04: sticky fault 발생 조건을 병렬 상태 적법성 식으로 분리했다. 최악은 load_begin→loaded_bytes −0.560ns, 명령 캡처도−0.485ns였다.
5. map06: 회로는 기준과 완전히 같게 두고 SPI·로더 인스턴스에만 SPEED 합성 설정을 적용했다. 설정 readback은 두 곳 모두SPEED, 무시 경고0이지만 자원과 타이밍은 기준과 같았다. 추가 이득이 없어 도입하지 않는다.

[Intel Quartus II Handbook 13.0](https://cdrdv2-public.intel.com/653795/quartusii_handbook_archive_130.pdf)의 모듈별 Optimization Technique 사용 설명을 참고했다. 지원되는 설정이라는 사실과 이 회로에서 효과가 있다는 주장은 다르다. map05는 중괄호가 포함된 인스턴스 이름으로 설정2개가 무시됐으므로 유효한 성능 비교에서 제외했다. 원시 기록을 보존했고 큰따옴표로 수정한 map06에서 다시 확인했다.

## 결과와 채택 판단

|후보|LE / LAB|추가 배치 목표 setup|실제 클록 setup|
|---|---:|---:|---:|
|유지: predecode165/map03|15040 / 963|-0.605ns|-0.153ns|
|map01: 주소 비트별 응답 조건|15027 / 961|-0.222ns|-0.222ns|
|map02: + WRITE/HOLD 전환 분리|15017 / 960|-0.300ns|-0.300ns|
|map03: + 오류 원인 캡처 분리|15030 / 961|-0.367ns|-0.367ns|
|map04: + 로더 fault 병렬 판별|15059 / 961|-0.676ns|-0.560ns|
|map06: 기준 RTL + 두 인스턴스 SPEED|15040 / 963|-0.605ns|-0.153ns|


모두 전체 FIT/ROUTE는 완료했으며35M9K를 사용한다. 실제 클록 setup은 모두 미달이다. SDC·클록·false path·multicycle을 완화하지 않았다. 각 후보는 카운터·캡처·로더뿐 아니라 네 클록의 setup/hold를 함께 판정했다. 한 경로의 개선이나 LAB 절감만으로 후보를 채택하지 않는다. 혼합 클록/외부IO 미제약은 별도 미완료다.

map01~04는 실험용 generator이며 설치 후보가 아니다. map06은60개 RTL/SDC/ROM 입력이 기준과 같아 기존 기능 검증을 재사용했다. 새로운 RTL 후보는 각각 변경 경계와 실제 SPI를 검증했다. 완료된 이전 archive와 공개 검증 해시는 그대로 보존한다.

## 검증 범위

- 최종 실험 SPI:1409024상태(19개 응답 주소 비트 불일치622592사례 포함),438272명령 캡처와 바로 다음 실행 edge 비교. 분리된 오류 저장은 이전 표현으로 투영한 뒤 동작까지 비교했다.
- 비트별 주소식은 모든19비트 차이 마스크×응답 유무1048576조합에서 동등했다. 주소 검사 비트와 READ 오류 원인을 빠뜨린 대조 회로는 거부됐다.
- 로더:3342336사례, 타이머0~127·상태·64명령 조합·차단·오류·6가지 적재 수. 상태/오류코드/주소/데이터/카운트/외부 핀이 같았다. 잘못된 STOP 전환과 STOP 오류 누락도 각각 검출했다.
- 각 변경 조합의 실제SPI98검사·8쓰기·6읽기·6실패 조건과 ACK/finish/START가 통과했다. 동일 바이트의 SPI 또는 로더는 재시험하지 않았다. 전체 ROM 적재·게임 부팅·60fps 실기 확인은 하지 않았다.
- 최초 FLOAT 실행은 샌드박스의 호스트 식별에서 멈췄고 같은 승인 래퍼를 실제 호스트에서 실행해 통과했다. 라이선스 내용/전역 설정은 변경하지 않았으며 비공개 라이선스 로그는 공개하지 않는다.

## 다음 계획

다음에는 조합식만 바꿔 배치를 반복하지 않는다. CHECK 요청 수락부터 응답·ACK까지 주소 태그와 카운터가 유지되는 정확한 클록 구간을 먼저 확인한다. 그 계약을 근거로 **응답 주소 비교가 카운터 갱신으로 되돌아오는 의존성 자체를 끊는 구조**를 검토한다. 잘못된 주소 응답·STOP/reset·동시 오류와 명령 완료 시점은 유지해야 한다. 도달할 수 없는 강제 주입 상태를 제외하려면 먼저 실제 순차 동작에서 불가능함을 입증하며, 실패하는 검사를 임의로 완화하지 않는다.

Retain predecode165 map03/reproduce03final (-0.153ns); no new RTL/SD selected. Do not repeat compare165 map01-04 or per-instance SPEED map06 (same result), and reject map05 invalid braced-node assignments. Before another full fit, derive a sequential ownership contract for CHECK request tag/counter/response: exactly which registers are stable from request acceptance through response and ACK. Use that contract to remove the response-address comparison from the counter feedback path, or precompute ownership validity where the tag is already stable. Preserve wrong-address, STOP/reset, fault and command retirement edges; do not simply waive arbitrary-state failures without proving reachability. Test only the changed boundary, then one full fit with counter/capture/loader and all-clock minima. Once safe, connect necessary native-video IO/CDC/reset and MCU receive-convert-ACK/audio/input/STOP/time/full-link/stack to minimum SMB3(J) hardware. Keep installed164/GBC/save SRAM; no repeated full writes/OAM/A-B/044.

실기 우선 원칙은 유지한다. 최소 안정성이 확보되면 IO·영상CDC/reset과 MCU 수신→변환→ACK·오디오·입력·STOP·경과시간·링크/스택을 연결하고 SMB3 첫 레벨로 간다. 기존164/GBC·세이브 SRAM을 보존하며 같은 OAM·전체 쓰기·A/B·044를 반복하지 않는다.
