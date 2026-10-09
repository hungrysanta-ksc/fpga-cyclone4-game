# 131 로더 카운터 사전 설정과 실제 배치 비교

PR76 병합 `77454989e171a767695831b9900ca830e671a852`에서 시작했다. **카운터를 바이트 수 검사와 분리했고 전체 이미지 쓰기 회귀를 통과했다.** 최종 **test02/fit05**, 같은 클록 memory setup **+0.041ns**로 setup은 **통과**다. 전체 타이밍 및 실기 설치 승인과 구분한다.

## 작업 목표

130의 `check_failed → remaining[3]|ena` 병목을 줄이되 WRITE/HOLD 펄스·오류 drain·명령 우선순위를 유지한다. 기존 카운터 전체 enable OFF 실험이나 phase/counter 단순 분리를 반복하지 않고, 실제 데이터 의존성을 제거한다.

## 작업 내용

기존에는 RECEIVE에서 유효한 데이터를 받아야 카운터에 SETUP 시간을 넣었다. 새 구현은 SETUP/WRITE/HOLD/RELEASE 밖에서 미리 SETUP 시간을 넣는다. 따라서 수신 허용·바이트 수·주소 계산이 카운터 갱신을 결정하지 않는다. 실제 데이터를 수락해 SETUP에 진입하는 순간의 값은 기존과 같다. 동작 중에는 기존 명령 pause와 sticky fault 발생 후 WRITE/HOLD drain 규칙을 유지한다.

대기 상태의 내부 `remaining`은 의도적으로 달라진다. 상태·주소·데이터·오류·핀 출력과 다음 상태가 timed phase일 때의 카운트를 대조했다. 내부 레지스터 전체가 항상 같다고 주장하지 않는다. 모든 경계는 고정 진단 파라미터22/64/22/22를 대상으로 한다.

실제 배치에서 나타난 enable/synchronous-load 병목에만 합성 설정을 적용했다. SPI `check_next`, 로더 `state`·`load_address`에서는 해당 제어 입력이 제거됐다. SPI `checked_data`에도 같은 설정을 추가했으나 **실제 enable8개는 남아 있다**. 따라서 설정만으로 제거를 보장하거나 이번 통과가 그 enable 제거 때문이라고 주장하지 않는다. 명령·응답 처리에 새 클록 지연은 없다. [공식 Quartus 도움말](https://www.intel.com.tw/content/www/tw/zh/programmable/quartushelp/22.1/logicops/logicops/def_allow_synch_ctrl_usage.htm)은 동기 clear/load가 LAB에서 공유되어 배치에 영향을 줄 수 있으며 레지스터별 적용이 가능함을 설명한다. 실제 연결은25.1 Standard 배치 결과로 확인했다.

## 작업 결과

| 검증 | 결과와 범위 |
|---|---|
| 상태 전이 대조 | 26,112개 상태·명령·길이·오류·카운트 조합, 외부 출력과 활성 카운터 일치 |
| 부정 대조 | SETUP 사전 설정을1클록 줄인 후보를 거부 |
| 전체 이미지 쓰기 | 80/96KiB 합계180,224바이트 +오류 시험87회 = **180,311회 실제 모델 핀 쓰기** |
| CHECK/RUN | CHECK308 /RUN128 /WRITE-HOLD drain86 |
| 취소·오용 | 기존CHECK48+추가CHECK/RUN96, 클록정지3, seeded READY 오용6 |
| 합성·배치 | MAP/FIT/STA 정상 종료. 14,078LE/954LAB/5,320regs/26M9K/PLL1/46물리핀+264가상핀 |
| 같은 클록 setup | NES +6.936 /host +2.318 /memory **+0.041ns** |
| 같은 클록 hold | 최소+0.158ns |
| 카운터 의존성 | 바이트 수→카운터 setup 경로0개, check_failed→카운터 최소+1.496ns |
| 상태·카운터 범위 | 8,592보고행, setup최소+0.304 /hold최소+0.187ns |
| 전체 원시 clock-pair | **-10.408ns**, 전체 승인 아님 |

| 배치 | memory setup | 선택 |
|---|---:|---|
| 이전130 fit01 | −0.040ns | 비교 기준 |
| fit01 | -0.474ns | 중간 비교 |
| fit02 | -0.251ns | 중간 비교 |
| fit03 | -0.095ns | 중간 비교 |
| fit04 | -0.283ns | 중간 비교 |
| fit05 | +0.041ns | 최종 |

fit01은 카운터 사전 설정만 바꿔 로더 병목을 줄였으나 SPI check_next enable이 최악 경로가 됐다. fit02는 이 enable을 제거했지만 state.RECEIVE sload에−0.251ns가 남았다. fit03은 상태 동기 제어 입력을 제거하고 load_address enable에−0.095ns가 남았다. fit04는 주소 제어 입력을 제거하고 checked_data enable에−0.283ns가 남았다. 후속 비교는 실제 보고된 경로에 근거했으며 단순 seed 변경이나 시간 예외 완화를 사용하지 않았다.

최종 reader 소유권219보고경로 최소+1.089ns, 이전 직접 setup0개다. 진단 reset 첫 단계 fanout1/단계 간6경로 최소+0.456ns, 혼합 하류1,776경로 최소-4.439ns는 별도 미해결이다. 원시 clock-pair 최악값은130의−8.236ns보다 악화됐으며 같은 클록 통과와 별도로 다룬다. 잔여LAB은 SNES 소비자·MMC3의 최종 여유가 아니다.

test01은 전체 쓰기를 끝낸 후 이전 seeded 시험의 `ram.writes==87` 기대값 때문에 실패했다. 전체 이미지180,224회가 추가됐으므로 기대값을180,311로 바로잡은 test02를 처음부터 다시 수행해 통과했다. fit05의 최초 검증기도 checked_data enable이0개여야 한다고 잘못 가정해 중단됐다. 실제8개 포트·타이밍을 확인한 뒤 관측값을 기록하도록 수정했으며 최초 검증기와 TSV를 보존했다. 이 수정 때문에 FPGA를 다시 배치하지 않았다. 라이선스 오류나 승인 거부는 없었다. 테스트 로그의 일부 PASS128/129 이름은 재사용한 검사 이름이며 새 시험 결과를 과거 실기 증거로 혼동하지 않는다.

fit03 이후의 차이는 합성 attribute뿐이다. 해당 attribute를 제거하면 diff01/test02와 최종 로더 동작 코드가 바이트 단위로 같고, SPI도130 동작 코드와 같다. 나머지 RTL·QSF·SDC는 그대로다. 최종 공개 materializer가 배치 입력을 재생성함을 검사했다. 이는 gate-level 동등성 증명이나 전체 SPI→CPU/MCU/SNES 소비자 시험은 아니다. RAM은70ns 모델이며 실물 핀 타이밍 승인이 아니다.

READ16/168MHz, write22/64/22/22 최소125/375/125/125ns, guard21/672/startup33603 유지. 새ARM/ASM/실기 패키지 없음. 동결 2,409파일, manifest `363d7305f110b92805c468a37138acc12341ef9fe208c659ae12a0dbf6d607ef`. 완료 finalizer와 archive044–131 수정 금지.

## 작업 의미

**실기 코어 동작을 위한 로더 제어 회로 구현과 합성·배치 검증**이다. 쓰기 타이머의 불필요한 수신 조건 의존성을 없애고, 바뀐 회로가 전체 전송과 오류 종료에서도 같은 핀 동작을 유지하는지 확인했다. 게임·MMC3 호환성 추가나 로그 기능 확장이 아니다.

다음 작업: 선택131fit05의 같은 클록 setup·hold 통과를 기준으로 새 hierarchy의 CDC/제어·reset 경로와 외부IO를 검증한다. 이후 실제 SNES 소비자와 관측 가능한 최소 RUN·044 복원으로 진행한다. 근거 없이 다섯 배치나 전체 쓰기를 반복하지 않는다.

이전126 CDC 승인·119 실기 통과를 새 배치에 상속하지 않는다. E1/E2·전체MTBF·8µs·양클록정지 CE9µs 반례, 첫 게임 SMB3(J)/mapper4/384KiB와 제한 진단 준비도6완료/5부분/1미완료를 유지한다.

[검증 메타](counter131-verification.json) · [현재 인계](../cores/nes/HANDOFF.ko.md)
