# 129 reader 소유권 등록과 reset→주소 경로 개선

PR74 병합 `533a01875cba62239a4b9ce696e23bf953567ef0`에서 시작했다. **기존 reader 병목은 분리했고 같은 클록 최악 setup은 −0.446ns에서 −0.158ns로 개선했다. 전체 내부 타이밍은 아직 미통과다.** 최종 선택은 **test01/fit01**이며, 번호가 더 큰 후속 실험을 최종으로 사용하지 않는다.

## 작업 목표

128의 `loader|release_reset[1] → reader|check_response_address[8]` 경로를 단축하고, 원시 reset·오류의 즉시 취소와 CHECK/RUN 소유권을 유지한다. 실기 최소 RUN을 위한 내부 타이밍 통과까지는 달성하지 못했다.

## 작업 내용

- reader가 로컬 reset에서 해제된 다음 메모리 클록에 CHECK/RUN 소유권을 `owner_check`에 저장하고 `owner_valid`를 설정한다. 이후 주소 선택·pending·완료 응답은 이 고정된 소유권으로 판단한다. CHECK ready는 소유권 확정 이후에만 올라간다.
- 소유권 변경은 공통 reader reset을 사이에 두어야 한다. 정상 CHECK→RUN은 CHECK 종료·reset 후 START로, RUN→CHECK는 STOP·reset 후 진행한다. 불법 변경은 기존 sticky 오류가 차단한다.
- boot 내부 CHECK 요청은 등록 소유권을 포함한 `raw_check_ready`를 사용한다. 외부 `check_ready`는 즉각적인 합법성 조건을 유지하며 주소 범위·`check_failed` 검사도 남겼다. 공통 reset/취소는 소유권 레지스터와 reader FSM을 비동기로 지운다.
- 로더 WRITE/HOLD의 조건 분리와 카운터 분리도 비교했으나, 타이밍 결과가 최종 후보보다 나빠 채택하지 않았다. **최종 로더와 SPI decoder는128과 같은 바이트다.** 해당 실험의 RTL·시험·배치·미채택 이유는 동결 자료에 남겼다.

## 작업 결과

| 검증 | 결과와 범위 |
|---|---|
| 최종 test01 | 80/96KiB RAM·로더 완료 상태를 설정한 뒤 실제 CHECK308회/RUN128회. 전체 이미지 쓰기는 반복하지 않음 |
| 오류 쓰기 | 실제87바이트 핀 쓰기, WRITE/HOLD86오류 위치와 CHECK 중 오류1개. 기존 쓰기 시간·drain 보존 |
| 취소 | 기존 CHECK48위치 + 새 CHECK/RUN 공통 reset·소유권 종료96사례 |
| 클록 정지 | memory/source/both 정지3사례에서 클록 없는 reset 취소·로컬 해제 대기·재시작 후 stale 응답 없음 |
| 잘못된 명령 | READY 상태를 설정한 불법6사례, 이후 쓰기와 외부 RUN 차단 |
| 부정 대조2개 | 잘못 저장한 owner와 동기식으로만 지워지는 owner를 각각 거부 |
| 실제 fit01 | 14,183LE /960 of963LAB /5,320레지스터 /26M9K /PLL1 /물리46핀·가상264핀 |
| 같은 클록 setup | NES +9.280ns /host84 +3.172ns /memory168 **−0.158ns** |
| reader 단계 경로 | 3코너의 보고된 setup219경로 최소 **+0.808ns**, 이전 reset→주소 직접 setup 경로0개 |
| 전체 원시 clock-pair | **−8.298ns**, 전체 타이밍 통과 아님.128의−6.953ns보다 악화 |
| 진단 reset 체인 | 첫 단계 fanout1, 단계 간6경로 최소+0.456ns. 혼합 하류1,776경로 최소−4.280ns는 미해결 |

219는 `release→owner`, `owner→address`, `owner 입력`의 보고 행 수이며 일부 그룹이 겹친다. `owner_valid`는 정상 동작 시 상수1을 저장하므로 register-to-register setup 경로가0개로 보고된다. 이것을 reset/CDC 승인으로 해석하지 않는다. 이전126의 CDC 검증도 새 배치 승인으로 상속하지 않는다.

선택한 후보의 남은 최악 경로는 `loader|state.WRITE → loader|state.HOLD` enable 논리다. READ16/168MHz, 로더22/64/22/22클록과 최소125/375/125/125ns, guard21/672/startup33603은 변경하지 않았다. 클록 주기나 타이밍 예외를 완화하지 않았다.

| 후보 | 변경 | memory setup | 선택 |
|---|---|---:|---|
| fit01 | reader 소유권 등록 | −0.158ns | **최종** |
| fit02 | 같은 RTL, standard fitter | −0.615ns | 미채택 |
| fit03 | WRITE/HOLD 진행과 오류 판정 분리 | −0.695ns | 미채택 |
| fit04 | 추가로 시간 카운터 갱신 분리 | −0.350ns | 미채택 |
| fit05 | fit04와 같은 RTL, standard fitter | −0.521ns | 미채택 |

두 로더 구조 실험은 각각26,112개 한 클록 전이 대조와 오류코드 변경 부정 대조를 통과했다. 하지만 배치 결과가 더 나빠 최종 코드에서 제외했다. 이 대조는 count0/total−1/total과 remaining1/2/22/64의 조합이며, 도달 불가능한 FAILED+fault0 및 임의 레지스터 손상을 포함하지 않는다.

시험은70ns RAM 모델·seeded 이미지·일부 seeded READY 상태를 사용한다. 실제 전체 SPI→CPU/MCU/SNES 소비자·실물 핀 타이밍 시험은 아니다. 128의 정상 전체80/96KiB 쓰기 증거는 로더 동일 해시로 유지하고, 이번에는 변경된 reader와 오류 경계에 시험을 집중했다.

초기 경로 분석기는 `owner_valid`에도 setup 경로가 존재해야 한다고 잘못 가정해 중단됐다. 실제 레지스터와 RTL 상수 입력을 확인한 뒤0개 결과를 명시하도록 수정했고 최초 TSV를 보존했다. refit 시작 직후 이전 후보의 완료 metadata가 보이던 문제도 새 실행기에서 빈 phase 목록을 먼저 쓰도록 고쳤다. 실행된 원본은 동결했고, 완료 전 결과를 최종으로 채택하지 않았다. 새 RTL·시뮬레이션·라이선스 실패나 승인 거부는 없었다.

동결 2,502파일, manifest `10ff116cdb29ca1d2e35d9bd4aff7c7866cb404a57a2128be999d50480ca4c9b`. 완료 finalizer·과거 archive 수정 금지. 새 ARM/ASM/설치 패키지·실기 결과는 없다.

## 작업 의미

**실기 코어 동작을 위한 reader 제어 구현과 내부 타이밍 개선**이다. reset 상태의 조합 논리를 주소 저장 조건에서 분리해 실제 제어 배선이 진전했다. 실기 게임 구동이나 MMC3 호환성 완성을 의미하지 않는다.

다음은 선택한 fit01의 로더 WRITE→HOLD enable 경로를 새 구조로 줄이는 것이다. 이번에 미채택한 단독 phase 분리·counter 분리·standard refit을 반복하지 말고 실제 지연 원인에 근거한 변경을 선택한다. 내부 타이밍 이후 새 CDC/IO·SNES 소비자·관측 가능한 최소 RUN+044 복원으로 넘어간다. E1/E2·전체MTBF·8µs·양클록 정지 CE9µs 반례와 SMB3(J)/mapper4/384KiB 첫 목표를 유지한다.

[검증 메타](reader129-verification.json) · [현재 인계](../cores/nes/HANDOFF.ko.md)
