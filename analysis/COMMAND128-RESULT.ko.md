# 128 SPI 명령 처리·로더 타이밍 개선

PR73 병합 `dfd1454db4e0fc7dd18325ad87ca36e74c98ccfa`에서 시작했다. **구조 변경과 기능 검증은 완료했고, 168MHz 내부 위반은 −2.647ns에서 −0.446ns로 줄었다. 타이밍 목표는 아직 미달이다.**

## 작업 목표

127에서 통합한 실제 코어의 SPI 명령 판정·reset 경로를 단축해 실기 RUN에 필요한 최소 안정성에 접근한다. 기존 오류 차단과 PSRAM 쓰기 시간을 유지한다.

## 작업 내용

- SPI 프레임 종료 때 형식·명령 조건을 검증하고, 다음 메모리 클록에 효과를 반영한다. 큐에 있는 START보다 새 오류가 우선하며, 반영 전 새 프레임이 겹치면 거부한다. CHECK/ACK/FINISH 후 verified가 설정된 경우만 START를 허용한다.
- 실제 top에 진단용 비동기 assert·동기 release reset 체인을 추가했다. reset이 들어오면 대기 명령을 취소하고, 클록이 멈춰 있으면 해제하지 않는다.
- CHECK 응답은 reader의 등록된 응답을 사용한다. 조합 응답 gate와 중복 명령 CHECK gate를 제거하되 sticky `check_failed` gate는 유지한다. 불법 BEGIN의 내부 상태는 달라질 수 있으나 같은 오류에서 외부 RUN과 이후 DATA 쓰기는 차단한다. 내부 오류 코드 전체의 이전 버전 동등성을 주장하지 않는다.
- 로더 명령 판정을 상태별로 나누어 READY의 조건이 WRITE/HOLD 전이를 지연시키지 않도록 했다. 쓰기 준비/쓰기/유지/해제는 22/64/22/22클록, 모델 시간130.944/380.928/130.944/130.944ns, 최소125/375/125/125ns를 유지한다.
- CHECK 주소 증가의 하위8비트 carry를 미리 계산한다. 완전한 SPI 프레임 사이에 값이 안정되는 계약을 시험하고 255→256,511→512 및 큰 주소 경계를 확인했다. READ16/168MHz, guard21분주/age672/startup33603은 유지한다.

## 작업 결과

| 검증 | 결과와 범위 |
|---|---|
| test06 실제 SPI decoder + 응답 모델 | half-SCK60/18ns 각각166검사/18오류 사례. 기존16 ACK 외512연속 ACK,65535/81919/98303에서 시작한3개 주소 경계 통과 |
| 명령 경계 | queued START보다 hard fault 우선, sub-cycle raw reset 취소, 정지 클록의 reset 유지, 겹친 프레임 거부 |
| boot05 실제 loader/boot/reader +70ns RAM 모델 | 80/96KiB 쓰기180,224+오류87바이트, CHECK308/RUN128, WRITE/HOLD 오류86위치 통과 |
| CHECK 소유권 | 이미지마다24취소 위치(총48), 내부 READY 상태를 설정한 불법 명령6사례 통과 |
| diff02 실제127/128 로더 대조 | 26,112개 한 클록 전이·오류 우선순위 일치. byte count0/total−1/total과 remaining1/2/22/64를 조합 |
| 부정 대조4개 | 미검증 START 허용, pending 중 hard fault 무시, sticky DATA gate 제거, 로더 오류코드 변경을 각각 거부 |
| fit07 실제 코어 배치 | 14,147LE /955 of963LAB /5,318레지스터 /26M9K /PLL1 /물리핀46·가상핀264 |
| 같은 클록 setup 최소 | NES +9.027ns /host84 +1.028ns /memory168 **−0.446ns** |
| 전체 원시 clock-pair 최소 | **−6.953ns**, 전체 타이밍 통과 아님 |
| 새 진단 reset 체인 | 첫 단계 fanout1, 단계 간 setup/hold6경로 최소+0.384ns. 하류 혼합 클록1,776경로 최소−4.482ns는 별도 미해결 |

현재 최악 같은 클록 경로는 `loader|release_reset[1] → reader|check_response_address[8]`다. 이 경로와 새 hierarchy의 CDC/IO가 다음 작업이다. 과거126의 데이터372쌍/제어10체인 검증을 이번 배치 승인으로 상속하지 않는다. 새로운 false path·multicycle·클록 주기 완화는 추가하지 않았다.

중간 memory setup은 fit01 −1.578, fit02 −1.469, fit03 −0.858, 동일 RTL standard fitter의 fit04 −0.676, 상태별 로더를 적용한 fit06 −0.413ns였다. fit07의 carry 분리는 최악값을 더 개선하지 않았고 병목이 reset 해제로 이동했다. 따라서 fit06보다 fit07이 모든 지표에서 우수하다고 하지 않는다. 최종 검증 대상은 fit07이다. fit05는 잘못된 이전 로더가 복사된 것을 발견해 의도적으로 중단했다.

시험의 경계도 보존한다. diff01은 도달 불가능한 `FAILED && !fault`를 주입하여 차이를 검출했다. 최종 diff02는 이1,536조합만 제외하며 임의 상태 레지스터 손상에 대한 동등성을 주장하지 않는다. 주소 count가 total보다 커지는 손상 상태도 범위 밖이다. 큰 ACK 주소3사례와 READY 불법 명령6사례는 내부 상태를 설정한 시험이다. 전체80/96KiB SPI→CPU 폐루프, MCU·SNES 소비자·실제 핀 전기적 시간은 검증하지 않았다.

test02 선언 순서 컴파일 실패, test04의512ACK 추가 후 기존10ms 시험 watchdog 초과, fit02 완료 전 audit 실행 실패도 기록했다. watchdog은 생성된 시험에서만100ms로 늘렸으며 펌웨어 제한은 바꾸지 않았다. fit05/boot04는 materializer의 새 로더 복사 누락을 확인하고 해당 작업의 자식 프로세스만 중단했다. 최종 boot05/fit07/공개 로더 해시는 일치한다. FLOAT wrapper가 임시 서버를 정리했으며 새 라이선스나 승인은 필요하지 않았다.

동결 3,773파일, manifest `3078ead176dd6b070b71b032b9c75a1e584b03f94784f9cdeb41bf5c8c0905eb`. 완료 finalizer와 과거 archive는 수정하지 않는다. 새 ARM/ASM/실기 패키지·실기 결과는 없다.

## 작업 의미

이번 작업은 **실기 코어 동작을 위한 로더·명령 제어 구현과 타이밍 개선**이다. 디버그 기록만 추가한 작업은 아니며, 실제 배선의 긴 조합 경로를 줄였다. 다만 타이밍 목표를 완전히 달성하지 못했고 NES 게임 구동·MMC3 호환성이 완성된 것은 아니다.

다음은 fit07의 reader reset/enable 경로를 개선하고 영향받는 경계 시험과 실제 배치를 확인하는 것이다. 그 뒤 새 CDC/IO·SNES 소비자·진행 관측과 독립044 복원을 갖춘 최소 RUN 실기로 넘어간다. E1/E2·전체MTBF·8µs·양클록 정지 CE9µs 반례는 남는다. 첫 게임 SMB3(J)/mapper4/384KiB와 제한 진단 준비도6완료/5부분/1미완료를 유지한다.

[검증 메타](command128-verification.json) · [현재 인계](../cores/nes/HANDOFF.ko.md)
