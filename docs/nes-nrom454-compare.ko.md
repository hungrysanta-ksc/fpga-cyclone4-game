# NROM454: 같은 edge 길이 검사의 분리 후보

453의 동기 setup 위반은 `loaded_bytes[8]`에서 SPI `raw_causes[4]`까지의 길이 비교·명령 결합 경로였다. 원래 C0 edge에서 24비트 offset과 loaded length의 상·하 절반 불일치 및 command 자격을 따로 기록하고 C1의 기존 sampled causes에서 합치는 격리 후보를 만들었다. 오류 우선순위와 C0에서 소비되는 값은 유지하며, 453의 guard 후보와 452의 SDC 후보를 포함한다. 제품 RTL은 변경하지 않았다.

원본과 후보를 같은 C0/C1 값으로 비교해 13,200 사례를 통과했다. 11개 명령, 16개 검증 상태 조합, 길이 세 값과 offset 24개 단일 bit 불일치·일치를 포함하며 C0 직후 입력을 바꿔 이전 값을 소비하는지도 확인했다. 동일 RTL의 SPI·boot·reader 회귀는 14,016 bit, read 100, ACK 7, corruption 19, cancel 72, overlap 2를 통과했다. 상위 불일치를 의도적으로 지운 음성 대조는 C0 mismatch를 검출했다. 이 결과는 전체 가능한 상태나 실제 ARM/보드를 증명하지 않는다. 첫 `test01`은 구형 벤치의 보드 ID 0x74 기대 때문에 실패했으며, 실제 0x78로 수정한 `test02`/음성 대조를 포함한 `test03`이 통과했다.

QSF 입력 누락을 검사한 Quartus Lite 전체 배치에서 453 대비 14,779→14,791 LE, comb 13,628→13,627, FF 8,029→8,033, RAM 185,824bit 동일이다. 원래 loaded_bytes→raw_causes 경로는 없어졌고 분리된 실제 비교 레지스터 경로 최악은 +0.831ns다. 453의 동일 경로 최악 −0.494ns와 대상은 다르므로 데이터 경로 변화와 전체 경로를 함께 본다. 420 방식 관련 클록 분류의 전체 최악은 다른 `loader|fault→phase[5]` 동일 클록 setup **−0.254ns**다. loader 강화 5.3ns 경로는 +0.253ns이며 raw setup −6.959ns, recovery −7.654ns, 미제약 IO가 남는다. guard 직접 경로 제거는 유지된다.

**판정: 보류.** 명령 검사 경로는 개선했으나 실제 동기 setup이 실패하므로 실기 후보로 채택하지 않는다. 조건부 IO와 단일 경로의 개선은 완전한 timing/CDC signoff가 아니다. 실패한 전체 timing을 해결하기 전 느린 전체 표시 회귀를 반복하지 않는다. 실제 ARM·base/menu 복구·물리 60fps도 미검증이다. 원본 및 시험 자료는 `probes/nes-nrom454`, 동일 분류 결과는 `analysis/nrom454-timing.json`이다.
