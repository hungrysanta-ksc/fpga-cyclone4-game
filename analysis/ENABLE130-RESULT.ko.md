# 130 로더 상태 enable 경로 제거와 배치 비교

PR75 병합 `5ab3754a99b802d390b0c8be48918fa04a855cb5`에서 시작했다. **상태 레지스터의 enable 입력4개를 제거했고 같은 클록 최악 setup은 −0.158ns에서 −0.040ns로 개선했다. 목표인 내부 타이밍 통과는 아직 달성하지 못했다.** 최종은 **fit01 상태 전용 설정**이다.

## 작업 목표

129의 `state.WRITE → state.HOLD|ena` 병목을 단축한다. 상태 전이, WRITE/HOLD 오류 drain, 쓰기 펄스, 원시 취소 동작을 유지하며 클록 주기나 타이밍 예외를 완화하지 않는다.

## 작업 내용

`nes_rom_loader.sv`의 `state` 선언에만 `AUTO_CLOCK_ENABLE_RECOGNITION OFF` 합성 attribute를 추가했다. 이전 경로는 상태의 데이터 입력이 아닌 enable에 도달했으므로, 자동 enable 추론을 끄고 데이터 논리로 구현하도록 했다. 레지스터별 설정과 논리 mux 구현 방식은 [공식 Quartus II 11.0 handbook](https://cdrdv2-public.intel.com/653791/quartusii_handbook_archive_11_0.pdf)의 Auto Clock Enable Replacement 설명을 근거로 삼았다. 실제 적용 여부는 이번25.1 Standard MAP/FIT 결과의 포트 연결로 따로 확인했다.

129 DB를 복사한 baseline02와 실제130 배치에서 상태9개·remaining7개, 총16레지스터의 동기 입력을 수집했다. baseline의 상태 enable4개(HOLD/WRITE/RELEASE/RECEIVE)가 fit01에서0개가 됐다. 카운터 enable3개는 유지된다. 해당 범위의 보고된 setup/hold 경로9,846행도 수집했다. 각 코너·종류당10,000행 제한에 도달하면 검증을 실패시키므로 잘린 결과를 통과 처리하지 않는다.

카운터까지 같은 attribute를 추가한 fit02도 비교했다. enable은 모두 사라졌지만 전체 memory setup이−1.470ns로 악화됐으므로 **미채택**이다. 번호가 큰fit02를 다음 후보로 사용하지 않는다.

## 작업 결과

| 항목 | 채택 fit01 |
|---|---|
| 도구 | MAP/FIT/STA 모두 정상 종료 |
| 자원 | 14,261LE /959 of963LAB /5,320레지스터 /26M9K /PLL1 /물리46핀·가상264핀 |
| 같은 클록 setup | NES +7.805ns /host84 +3.388ns /memory168 **−0.040ns** |
| 원시 clock-pair 최소 | **−8.236ns**, 전체 타이밍 승인 아님 |
| 상태·카운터 대상 경로 | 9,846보고행, setup최소−0.040ns /hold최소+0.179ns |
| reader 소유권 경로 | 219보고행 최소+0.950ns, 이전 직접 setup 경로0개 |
| 진단 reset 체인 | 첫 단계 fanout1, 단계 간6경로 최소+0.383ns |
| 혼합 reset 하류 | 1,776행 최소−4.695ns, 미해결 |

남은 같은 클록 최악 경로는 `boot|check_failed → loader|remaining[3]|ena`이며6단계 논리, 데이터 지연5.926ns다. 이전−0.158ns보다 개선됐어도 음수인−0.040ns를 반올림해서 통과로 처리하지 않는다. 잔여4LAB도 최종 소비자·MMC3의 여유를 보장하지 않는다.

| 비교 | 상태 enable | 카운터 enable | memory setup | 결정 |
|---|---:|---:|---:|---|
| 129 fit01 | 4 | 3 | −0.158ns | 이전 기준 |
| 130 fit01 | 0 | 3 | **−0.040ns** | 채택 |
| 130 fit02 | 0 | 0 | −1.470ns | 미채택 |

fit02의 최악 경로는 SPI `fault → pending_body_error[2]`로 옮겨갔다. 로더 enable 제거만으로 전체 설계의 배치 결과가 개선된다고 볼 수 없다는 근거다. 다음에는 남은 카운터 입력과 공유 오류 신호의 fanout을 함께 검토한다. 카운터 전체 설정과129의 단독 phase/counter 분리·standard refit을 그대로 반복하지 않는다.

**기능 검증 재사용 범위:** 두 후보 모두 정확한 합성 attribute만 제거하면129 로더와 바이트 단위로 같다. 나머지 RTL·QSF·SDC 입력도 모두 동일 해시이며, 현재 공개 materializer가 채택fit01의 전체 입력을 재생성함을 검사했다. 129의 CHECK308/RUN128·오류 쓰기87/drain86·취소·멈춘 클록·부정 대조 증거를 재사용했다. 이번에 새 기능 시뮬레이션이나 gate-level 동등성 증명을 수행했다는 뜻은 아니다. READ16/168MHz, write22/64/22/22와 최소125/375/125/125ns, guard21/672/startup33603은 그대로다.

최초9개 상태 레지스터 분석을16개 상태·카운터로 확장했고 최초 TCL/TSV/review도 보존했다. fit01 검증기는 채택 범위에 맞춰 상태 enable0개와 관측된 카운터 enable3개를 구분한다. 두 MAP/FIT/STA 실행은 정상 종료했고 라이선스·승인 거부는 없었다. 동결 1,773파일, manifest `511eaaa612656cd6c42448a5801f812a5b57ed4f1758a6e282bff76993f91d90`. 완료 finalizer·archive044–130 수정 금지.

## 작업 의미

**실기 코어 동작을 위한 로더 제어 회로의 합성·배치 개선**이다. 새 로그 기능이나 게임 호환성 추가가 아니라 이미 구현된 동작을 목표 클록에서 실행하도록 만드는 단계다. 이번에는 기존 병목의 구현을 바꿨지만 내부 타이밍 완성까지는 남았다.

다음은 채택fit01의 `check_failed → remaining[3]` enable 경로 개선, 이후 새 hierarchy CDC/IO·실제 SNES 소비자·관측 가능한 최소 RUN+독립044 복원이다. 이전126 CDC 승인,119 실기 통과를 새 배치 승인으로 상속하지 않는다. E1/E2·전체MTBF·8µs·양클록 정지 CE9µs 반례는 미해결이다. 첫 게임 SMB3(J)/mapper4/384KiB와 제한 진단 준비도6완료/5부분/1미완료를 유지한다. 새 ARM/ASM/설치 패키지·실기 결과는 없다.

[검증 메타](enable130-verification.json) · [현재 인계](../cores/nes/HANDOFF.ko.md)
